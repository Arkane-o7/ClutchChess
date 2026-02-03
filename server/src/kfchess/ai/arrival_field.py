"""Arrival time fields for AI decision-making.

Computes the minimum ticks for each side to reach each square,
enabling safety analysis and positional evaluation.

Key concept: "post-arrival safety" — after moving to a square, we're on
cooldown. A square is safe if no enemy piece can reach it before our
cooldown expires. The safety calculation is per-move (depends on travel
distance), not per-square.
"""

from dataclasses import dataclass, field

from kfchess.ai.state_extractor import AIPiece, AIState, PieceStatus
from kfchess.game.pieces import PieceType
from kfchess.game.state import TICK_RATE_HZ, SpeedConfig

# Infinity sentinel for unreachable squares
INF_TICKS = 999_999

# Reaction time: how long it takes to see an incoming threat and issue
# a dodge move after cooldown expires. 100ms converted to ticks.
REACTION_TIME_SECONDS = 1.0


@dataclass
class ArrivalData:
    """Arrival time data for both sides.

    Attributes:
        our_time: Min ticks for AI's pieces to reach each square
        enemy_time: Min ticks for enemy pieces to reach each square
        enemy_time_by_piece: Per-piece enemy arrival times (for excluding
            captured pieces when evaluating recapture risk)
        tps: Ticks per square (from speed config)
        cd_ticks: Cooldown duration in ticks (from speed config)
    """

    our_time: dict[tuple[int, int], int] = field(default_factory=dict)
    enemy_time: dict[tuple[int, int], int] = field(default_factory=dict)
    enemy_time_by_piece: dict[str, dict[tuple[int, int], int]] = field(
        default_factory=dict
    )
    tps: int = 30
    cd_ticks: int = 300
    reaction_ticks: int = 30  # 1s at 30Hz
    # Stored for recomputation when a piece vacates its square
    _occupied: set[tuple[int, int]] = field(default_factory=set)
    _enemy_pieces: list[AIPiece] = field(default_factory=list)
    _board_w: int = 8
    _board_h: int = 8
    _is_4p: bool = False

    def get_our_time(self, row: int, col: int) -> int:
        """Get our minimum arrival time at a square."""
        return self.our_time.get((row, col), INF_TICKS)

    def get_enemy_time(self, row: int, col: int) -> int:
        """Get enemy minimum arrival time at a square."""
        return self.enemy_time.get((row, col), INF_TICKS)

    def get_enemy_time_excluding(
        self, row: int, col: int, exclude_piece_id: str,
    ) -> int:
        """Get enemy arrival time at a square, excluding one piece.

        Used for recapture analysis: after capturing a piece, compute
        how quickly a different enemy piece can reach the same square.
        """
        best = INF_TICKS
        for pid, times in self.enemy_time_by_piece.items():
            if pid == exclude_piece_id:
                continue
            t = times.get((row, col), INF_TICKS)
            if t < best:
                best = t
        return best

    def _recompute_enemy_time(
        self, row: int, col: int,
        unblocked_pos: tuple[int, int],
        exclude_piece_id: str | None = None,
    ) -> int:
        """Recompute enemy arrival at (row, col) with unblocked_pos removed from occupancy.

        This handles the case where our piece vacating its square unblocks
        an enemy slider ray. Only recomputes for idle enemy sliders that
        could benefit from the unblocked position.
        """
        modified_occupied = self._occupied - {unblocked_pos}
        best = INF_TICKS

        for ep in self._enemy_pieces:
            if exclude_piece_id and ep.piece.id == exclude_piece_id:
                continue
            t = _piece_arrival_time(
                ep, (row, col), self.tps, self.cd_ticks,
                modified_occupied, self._board_w, self._board_h, self._is_4p,
            )
            if t < best:
                best = t

        # Also check traveling enemy pieces (not affected by occupancy changes,
        # but need to include them for completeness)
        for pid, times in self.enemy_time_by_piece.items():
            if exclude_piece_id and pid == exclude_piece_id:
                continue
            # Skip idle pieces — already recomputed above
            if any(ep.piece.id == pid for ep in self._enemy_pieces):
                continue
            t = times.get((row, col), INF_TICKS)
            if t < best:
                best = t

        return best

    def post_arrival_safety(
        self, row: int, col: int, travel_ticks: int,
        exclude_piece_id: str | None = None,
        moving_from: tuple[int, int] | None = None,
    ) -> int:
        """Compute post-arrival safety margin for a move.

        After arriving at (row, col) in travel_ticks, we're on cooldown
        for cd_ticks + reaction_ticks before we can dodge.
        Safety = enemy_arrival - (travel + cooldown + reaction).
        Positive means enemy can't reach us before we can react.

        Args:
            row, col: Destination square
            travel_ticks: How long our move takes
            exclude_piece_id: Enemy piece to exclude (e.g., one we're capturing)
            moving_from: Our piece's origin square. When set, recomputes enemy
                arrival times as if this square is vacated, fixing the
                self-blocking bug where our piece blocks an enemy slider ray.

        Returns:
            Safety margin in ticks. Positive = safe, negative = vulnerable.
        """
        if moving_from is not None and self._enemy_pieces:
            enemy_t = self._recompute_enemy_time(
                row, col, moving_from, exclude_piece_id,
            )
        elif exclude_piece_id:
            enemy_t = self.get_enemy_time_excluding(row, col, exclude_piece_id)
        else:
            enemy_t = self.get_enemy_time(row, col)

        vulnerable_until = travel_ticks + self.cd_ticks + self.reaction_ticks
        return enemy_t - vulnerable_until

    def is_piece_at_risk(
        self, row: int, col: int, cooldown_remaining: int = 0,
    ) -> bool:
        """Check if a piece sitting at (row, col) is at risk.

        A piece can dodge an incoming threat, but only after its cooldown
        expires and it has time to react. It's at risk if an enemy can
        reach the square before cooldown + reaction time.

        An idle piece (cooldown_remaining=0) only needs reaction time to
        dodge, so it's much harder to threaten.

        Args:
            row, col: Piece position
            cooldown_remaining: Ticks left on this piece's cooldown (0 if idle)
        """
        enemy_t = self.get_enemy_time(row, col)
        return enemy_t < cooldown_remaining + self.reaction_ticks


class ArrivalField:
    """Computes per-side arrival time fields."""

    @staticmethod
    def compute(
        ai_state: AIState,
        config: SpeedConfig,
        critical_only: bool = False,
    ) -> ArrivalData:
        """Compute arrival fields for both sides.

        Args:
            ai_state: AI state snapshot
            config: Speed configuration (for ticks_per_square)
            critical_only: If True, only compute for critical squares
                (king zones + center). Used for 4-player to save budget.

        Returns:
            ArrivalData with timing info
        """
        tps = config.ticks_per_square
        cd_ticks = config.cooldown_ticks
        w, h = ai_state.board_width, ai_state.board_height

        # Determine which squares to compute
        if critical_only:
            squares = _get_critical_squares(ai_state)
        else:
            squares = [
                (r, c) for r in range(h) for c in range(w)
            ]

        # Build static occupancy for slider blocking
        occupied: set[tuple[int, int]] = set()
        for ap in ai_state.pieces:
            if ap.status != PieceStatus.TRAVELING and not ap.piece.captured:
                occupied.add(ap.piece.grid_position)

        own_pieces = [
            p for p in ai_state.get_own_pieces()
            if p.status != PieceStatus.TRAVELING and not p.piece.captured
        ]
        enemy_pieces = [
            p for p in ai_state.get_enemy_pieces()
            if p.status != PieceStatus.TRAVELING and not p.piece.captured
        ]

        is_4p = w > 8

        our_time = _compute_side_times(own_pieces, squares, tps, cd_ticks, occupied, w, h, is_4p)

        # Compute per-piece enemy times (for exclusion during capture analysis)
        enemy_time_by_piece: dict[str, dict[tuple[int, int], int]] = {}
        enemy_time: dict[tuple[int, int], int] = {sq: INF_TICKS for sq in squares}

        for ep in enemy_pieces:
            piece_times: dict[tuple[int, int], int] = {}
            for sq in squares:
                t = _piece_arrival_time(ep, sq, tps, cd_ticks, occupied, w, h, is_4p)
                piece_times[sq] = t
                if t < enemy_time[sq]:
                    enemy_time[sq] = t
            enemy_time_by_piece[ep.piece.id] = piece_times

        # Account for traveling enemy pieces: they will arrive at squares
        # along their remaining path. These are already committed moves
        # that WILL happen — ignoring them is a critical safety blind spot.
        for ep in ai_state.get_enemy_pieces():
            if ep.status != PieceStatus.TRAVELING or ep.piece.captured:
                continue
            if ep.travel_direction is None:
                continue

            pr, pc = ep.current_position
            dr, dc = ep.travel_direction
            piece_times: dict[tuple[int, int], int] = {}

            # Project along the travel ray: the piece will pass through
            # each square at dist * tps ticks from now (approximate)
            for dist in range(0, max(w, h)):
                sr = int(round(pr + dr * dist))
                sc = int(round(pc + dc * dist))
                if sr < 0 or sr >= h or sc < 0 or sc >= w:
                    break
                sq = (sr, sc)
                # Arrival time: distance from current position in ticks
                t = dist * tps
                if sq in enemy_time:
                    piece_times[sq] = t
                    if t < enemy_time[sq]:
                        enemy_time[sq] = t

            enemy_time_by_piece[ep.piece.id] = piece_times

        reaction_ticks = int(REACTION_TIME_SECONDS * TICK_RATE_HZ)

        return ArrivalData(
            our_time=our_time,
            enemy_time=enemy_time,
            enemy_time_by_piece=enemy_time_by_piece,
            tps=tps,
            cd_ticks=cd_ticks,
            reaction_ticks=reaction_ticks,
            _occupied=occupied,
            _enemy_pieces=enemy_pieces,
            _board_w=w,
            _board_h=h,
            _is_4p=is_4p,
        )


def _compute_side_times(
    pieces: list[AIPiece],
    squares: list[tuple[int, int]],
    tps: int,
    cd_ticks: int,
    occupied: set[tuple[int, int]],
    board_w: int,
    board_h: int,
    is_4p: bool = False,
) -> dict[tuple[int, int], int]:
    """Compute minimum arrival time for a set of pieces to each square."""
    times: dict[tuple[int, int], int] = {}

    for sq in squares:
        best = INF_TICKS
        for piece in pieces:
            t = _piece_arrival_time(piece, sq, tps, cd_ticks, occupied, board_w, board_h, is_4p)
            if t < best:
                best = t
        times[sq] = best

    return times


def _piece_arrival_time(
    ap: AIPiece,
    target: tuple[int, int],
    tps: int,
    cd_ticks: int,
    occupied: set[tuple[int, int]],
    board_w: int,
    board_h: int,
    is_4p: bool = False,
) -> int:
    """Compute ticks for a single piece to reach a target square.

    Returns INF_TICKS if unreachable.
    """
    pos = ap.piece.grid_position
    if pos == target:
        return ap.cooldown_remaining

    base_delay = ap.cooldown_remaining
    tr, tc = target
    pr, pc = pos
    ptype = ap.piece.type

    if ptype == PieceType.ROOK:
        return _slider_time_rook(pr, pc, tr, tc, tps, base_delay, occupied)
    elif ptype == PieceType.BISHOP:
        return _slider_time_bishop(pr, pc, tr, tc, tps, base_delay, occupied)
    elif ptype == PieceType.QUEEN:
        # Queen = min(rook path, bishop path)
        rt = _slider_time_rook(pr, pc, tr, tc, tps, base_delay, occupied)
        bt = _slider_time_bishop(pr, pc, tr, tc, tps, base_delay, occupied)
        return min(rt, bt)
    elif ptype == PieceType.KNIGHT:
        return _knight_time(pr, pc, tr, tc, tps, base_delay, cd_ticks, board_w, board_h)
    elif ptype == PieceType.KING:
        return _king_time(pr, pc, tr, tc, tps, base_delay)
    elif ptype == PieceType.PAWN:
        return _pawn_time(ap, tr, tc, tps, base_delay, is_4p)
    return INF_TICKS


def _slider_time_rook(
    pr: int, pc: int, tr: int, tc: int,
    tps: int, base_delay: int,
    occupied: set[tuple[int, int]],
) -> int:
    """Arrival time for a rook (straight lines only)."""
    if pr == tr:
        dist = abs(tc - pc)
        if _is_path_clear_horizontal(pr, pc, tc, occupied):
            return base_delay + dist * tps
    elif pc == tc:
        dist = abs(tr - pr)
        if _is_path_clear_vertical(pc, pr, tr, occupied):
            return base_delay + dist * tps
    return INF_TICKS


def _slider_time_bishop(
    pr: int, pc: int, tr: int, tc: int,
    tps: int, base_delay: int,
    occupied: set[tuple[int, int]],
) -> int:
    """Arrival time for a bishop (diagonals only)."""
    dr = abs(tr - pr)
    dc = abs(tc - pc)
    if dr == dc and dr > 0:
        if _is_path_clear_diagonal(pr, pc, tr, tc, occupied):
            return base_delay + dr * tps
    return INF_TICKS


def _is_path_clear_horizontal(
    row: int, from_col: int, to_col: int,
    occupied: set[tuple[int, int]],
) -> bool:
    """Check if horizontal path is clear (exclusive of endpoints)."""
    step = 1 if to_col > from_col else -1
    for c in range(from_col + step, to_col, step):
        if (row, c) in occupied:
            return False
    return True


def _is_path_clear_vertical(
    col: int, from_row: int, to_row: int,
    occupied: set[tuple[int, int]],
) -> bool:
    """Check if vertical path is clear (exclusive of endpoints)."""
    step = 1 if to_row > from_row else -1
    for r in range(from_row + step, to_row, step):
        if (r, col) in occupied:
            return False
    return True


def _is_path_clear_diagonal(
    pr: int, pc: int, tr: int, tc: int,
    occupied: set[tuple[int, int]],
) -> bool:
    """Check if diagonal path is clear (exclusive of endpoints)."""
    dr = 1 if tr > pr else -1
    dc = 1 if tc > pc else -1
    r, c = pr + dr, pc + dc
    while r != tr or c != tc:
        if (r, c) in occupied:
            return False
        r += dr
        c += dc
    return True


def _knight_time(
    pr: int, pc: int, tr: int, tc: int,
    tps: int, base_delay: int, cd_ticks: int,
    board_w: int, board_h: int,
) -> int:
    """Arrival time for a knight using BFS (up to 2 hops for budget)."""
    # Knight moves 2 squares per move (L-shape), each taking 2*tps ticks
    move_ticks = 2 * tps

    # Check 1-hop
    dr, dc = abs(tr - pr), abs(tc - pc)
    if (dr, dc) in ((1, 2), (2, 1)):
        return base_delay + move_ticks

    # Check 2-hop: enumerate all intermediate squares reachable in 1 hop
    KNIGHT_OFFSETS = [
        (-2, -1), (-2, 1), (-1, -2), (-1, 2),
        (1, -2), (1, 2), (2, -1), (2, 1),
    ]
    for dr1, dc1 in KNIGHT_OFFSETS:
        mr, mc = pr + dr1, pc + dc1
        if 0 <= mr < board_h and 0 <= mc < board_w:
            dr2, dc2 = abs(tr - mr), abs(tc - mc)
            if (dr2, dc2) in ((1, 2), (2, 1)):
                return base_delay + move_ticks + cd_ticks + move_ticks

    return INF_TICKS


def _king_time(
    pr: int, pc: int, tr: int, tc: int,
    tps: int, base_delay: int,
) -> int:
    """Arrival time for a king (1 square in any direction, single move only)."""
    dr = abs(tr - pr)
    dc = abs(tc - pc)
    if dr <= 1 and dc <= 1:
        dist = max(dr, dc)
        return base_delay + dist * tps
    return INF_TICKS


def _pawn_time(
    ap: AIPiece, tr: int, tc: int,
    tps: int, base_delay: int,
    is_4p: bool = False,
) -> int:
    """Arrival time for a pawn (forward moves and captures, single move only).

    Uses per-player forward direction to handle 4-player mode correctly.
    2-player: P1 up (-1,0), P2 down (1,0).
    4-player: P1 left (0,-1), P2 up (-1,0), P3 right (0,1), P4 down (1,0).

    Includes diagonal capture squares — pawns can threaten diagonals even
    if no enemy is currently there (used for arrival-time threat assessment).
    """
    pr, pc = ap.piece.grid_position
    player = ap.piece.player
    fr, fc = _pawn_forward(player, is_4p)
    dr, dc = tr - pr, tc - pc

    # Forward 1
    if dr == fr and dc == fc:
        return base_delay + tps
    # Forward 2 (from starting position)
    if dr == 2 * fr and dc == 2 * fc and not ap.piece.moved:
        return base_delay + 2 * tps
    # Diagonal capture: one step forward + one step sideways
    if fr != 0:
        # Row-moving pawn: forward is (fr, 0), sideways is column ±1
        if dr == fr and abs(dc) == 1:
            return base_delay + tps
    else:
        # Column-moving pawn: forward is (0, fc), sideways is row ±1
        if dc == fc and abs(dr) == 1:
            return base_delay + tps

    return INF_TICKS


# Forward direction per player.
# 2-player: P1 bottom (up), P2 top (down).
# 4-player: matches FOUR_PLAYER_ORIENTATIONS in moves.py.
_PAWN_FORWARD_2P: dict[int, tuple[int, int]] = {
    1: (-1, 0),  # Up
    2: (1, 0),   # Down
}
_PAWN_FORWARD_4P: dict[int, tuple[int, int]] = {
    1: (0, -1),  # Left (East player)
    2: (-1, 0),  # Up (South player)
    3: (0, 1),   # Right (West player)
    4: (1, 0),   # Down (North player)
}


def _pawn_forward(player: int, is_4p: bool = False) -> tuple[int, int]:
    """Get pawn forward direction for a player."""
    if is_4p:
        return _PAWN_FORWARD_4P.get(player, (-1, 0))
    return _PAWN_FORWARD_2P.get(player, (-1, 0))


def _get_critical_squares(ai_state: AIState) -> list[tuple[int, int]]:
    """Get critical squares for 4-player mode: king zones + center."""
    squares: set[tuple[int, int]] = set()
    w, h = ai_state.board_width, ai_state.board_height

    # Center region (4x4)
    center_r, center_c = h // 2, w // 2
    for r in range(center_r - 2, center_r + 2):
        for c in range(center_c - 2, center_c + 2):
            if 0 <= r < h and 0 <= c < w:
                squares.add((r, c))

    # King zones (3x3 around each king)
    for ap in ai_state.pieces:
        if ap.piece.type == PieceType.KING and not ap.piece.captured:
            kr, kc = ap.piece.grid_position
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    r, c = kr + dr, kc + dc
                    if 0 <= r < h and 0 <= c < w:
                        squares.add((r, c))

    return list(squares)
