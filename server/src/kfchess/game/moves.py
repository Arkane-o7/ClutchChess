"""Move definitions and validation for Kung Fu Chess."""

from dataclasses import dataclass

from kfchess.game.pieces import Piece, PieceType
from kfchess.game.board import Board


# Path type: can be int or float (floats used for knight midpoint)
PathPoint = tuple[float, float]


@dataclass
class Move:
    """Represents an active piece movement.

    Attributes:
        piece_id: ID of the moving piece
        path: List of (row, col) positions the piece travels through.
              Usually integers, but knights use float midpoints.
        start_tick: Game tick when the move started
        extra_move: Optional secondary move (e.g., rook in castling)
    """

    piece_id: str
    path: list[PathPoint]
    start_tick: int
    extra_move: "Move | None" = None

    @property
    def start_position(self) -> PathPoint:
        """Get the starting position of the move."""
        return self.path[0]

    @property
    def end_position(self) -> PathPoint:
        """Get the ending position of the move."""
        return self.path[-1]

    @property
    def num_squares(self) -> int:
        """Get the number of squares the piece moves through (path length - 1)."""
        return len(self.path) - 1


@dataclass
class Cooldown:
    """Represents a piece cooldown period.

    Attributes:
        piece_id: ID of the piece on cooldown
        start_tick: Game tick when cooldown started
        duration: Number of ticks the cooldown lasts
    """

    piece_id: str
    start_tick: int
    duration: int

    def is_active(self, current_tick: int) -> bool:
        """Check if cooldown is still active at the given tick."""
        return current_tick < self.start_tick + self.duration


def compute_move_path(
    piece: Piece,
    board: Board,
    to_row: int,
    to_col: int,
    active_moves: list[Move],
) -> list[PathPoint] | None:
    """Compute the path for a piece to move to a destination.

    Returns the path as a list of (row, col) tuples, or None if the move is invalid.
    The path includes the starting position as the first element.
    Most pieces use integer coordinates, but knights use float midpoints.

    Args:
        piece: The piece to move
        board: Current board state
        to_row: Destination row
        to_col: Destination column
        active_moves: Currently active moves (to check for path conflicts)

    Returns:
        List of (row, col) positions forming the path, or None if invalid
    """
    from_row, from_col = piece.grid_position

    # Can't move to same position
    if from_row == to_row and from_col == to_col:
        return None

    # Check if destination is valid
    if not board.is_valid_square(to_row, to_col):
        return None

    # Get the appropriate path computation based on piece type
    path = _compute_piece_path(piece, board, from_row, from_col, to_row, to_col, active_moves)
    if path is None:
        return None

    # Check for blocking pieces along the path (except knights which jump)
    if piece.type != PieceType.KNIGHT:
        if not _is_path_clear(path, board, piece.player, active_moves):
            return None
    else:
        # Knights jump over pieces but still can't land on own pieces
        if not _is_knight_destination_valid(path, board, piece.player, active_moves):
            return None

    return path


def _compute_piece_path(
    piece: Piece,
    board: Board,
    from_row: int,
    from_col: int,
    to_row: int,
    to_col: int,
    active_moves: list[Move],
) -> list[PathPoint] | None:
    """Compute path based on piece type."""
    match piece.type:
        case PieceType.PAWN:
            return _compute_pawn_path(piece, board, from_row, from_col, to_row, to_col, active_moves)
        case PieceType.KNIGHT:
            return _compute_knight_path(from_row, from_col, to_row, to_col)
        case PieceType.BISHOP:
            return _compute_bishop_path(from_row, from_col, to_row, to_col)
        case PieceType.ROOK:
            return _compute_rook_path(from_row, from_col, to_row, to_col)
        case PieceType.QUEEN:
            return _compute_queen_path(from_row, from_col, to_row, to_col)
        case PieceType.KING:
            return _compute_king_path(from_row, from_col, to_row, to_col)
        case _:
            return None


def _compute_pawn_path(
    piece: Piece,
    board: Board,
    from_row: int,
    from_col: int,
    to_row: int,
    to_col: int,
    active_moves: list[Move],
) -> list[PathPoint] | None:
    """Compute pawn movement path.

    Pawns can:
    - Move forward 1 square (or 2 from starting position)
    - Capture diagonally (only if stationary opponent piece at destination)
    """
    direction = -1 if piece.player == 1 else 1  # Player 1 moves up (decreasing row)
    start_row = 6 if piece.player == 1 else 1  # Starting row for each player

    row_diff = to_row - from_row
    col_diff = to_col - from_col

    # Forward movement
    if col_diff == 0:
        # Single square forward
        if row_diff == direction:
            # Can't capture when moving straight - destination must be empty
            target = board.get_piece_at(to_row, to_col)
            if target is not None:
                return None
            return [(float(from_row), float(from_col)), (float(to_row), float(to_col))]

        # Double square forward from starting position
        if row_diff == 2 * direction and from_row == start_row:
            # Check both squares are empty
            mid_row = from_row + direction
            if board.get_piece_at(mid_row, from_col) is not None:
                return None
            if board.get_piece_at(to_row, to_col) is not None:
                return None
            return [
                (float(from_row), float(from_col)),
                (float(mid_row), float(from_col)),
                (float(to_row), float(to_col)),
            ]

    # Diagonal capture - requires stationary opponent piece at destination
    if abs(col_diff) == 1 and row_diff == direction:
        target = board.get_piece_at(to_row, to_col)
        # Must have an opponent piece that is NOT currently moving
        if target is None or target.player == piece.player:
            return None
        # Check if target is already moving
        if _is_piece_moving(target.id, active_moves):
            return None
        return [(float(from_row), float(from_col)), (float(to_row), float(to_col))]

    return None


def _is_piece_moving(piece_id: str, active_moves: list[Move]) -> bool:
    """Check if a piece is currently moving."""
    return any(m.piece_id == piece_id for m in active_moves)


def _compute_knight_path(
    from_row: int,
    from_col: int,
    to_row: int,
    to_col: int,
) -> list[PathPoint] | None:
    """Compute knight movement path.

    Knights move in an L-shape: 2 squares in one direction, 1 in perpendicular.
    Knights jump over pieces and travel through a midpoint between start and end.
    The path has 3 points: start, midpoint (float), end.
    This takes 2 * move_ticks to complete (2 segments).
    """
    row_diff = abs(to_row - from_row)
    col_diff = abs(to_col - from_col)

    # Valid knight moves: 2+1 or 1+2
    if (row_diff == 2 and col_diff == 1) or (row_diff == 1 and col_diff == 2):
        # Midpoint is average of start and end (can be float like 3.5)
        mid_row = (from_row + to_row) / 2.0
        mid_col = (from_col + to_col) / 2.0
        return [
            (float(from_row), float(from_col)),
            (mid_row, mid_col),
            (float(to_row), float(to_col)),
        ]

    return None


def _compute_bishop_path(
    from_row: int,
    from_col: int,
    to_row: int,
    to_col: int,
) -> list[PathPoint] | None:
    """Compute bishop movement path (diagonal only)."""
    row_diff = to_row - from_row
    col_diff = to_col - from_col

    # Must be diagonal (equal absolute differences)
    if abs(row_diff) != abs(col_diff) or row_diff == 0:
        return None

    return _build_linear_path(from_row, from_col, to_row, to_col)


def _compute_rook_path(
    from_row: int,
    from_col: int,
    to_row: int,
    to_col: int,
) -> list[PathPoint] | None:
    """Compute rook movement path (horizontal or vertical only)."""
    row_diff = to_row - from_row
    col_diff = to_col - from_col

    # Must be horizontal or vertical (one diff must be 0)
    if row_diff != 0 and col_diff != 0:
        return None

    if row_diff == 0 and col_diff == 0:
        return None

    return _build_linear_path(from_row, from_col, to_row, to_col)


def _compute_queen_path(
    from_row: int,
    from_col: int,
    to_row: int,
    to_col: int,
) -> list[PathPoint] | None:
    """Compute queen movement path (diagonal, horizontal, or vertical)."""
    row_diff = to_row - from_row
    col_diff = to_col - from_col

    # Diagonal
    if abs(row_diff) == abs(col_diff) and row_diff != 0:
        return _build_linear_path(from_row, from_col, to_row, to_col)

    # Horizontal or vertical
    if (row_diff == 0) != (col_diff == 0):  # XOR - exactly one must be 0
        return _build_linear_path(from_row, from_col, to_row, to_col)

    return None


def _compute_king_path(
    from_row: int,
    from_col: int,
    to_row: int,
    to_col: int,
) -> list[PathPoint] | None:
    """Compute king movement path (one square in any direction)."""
    row_diff = abs(to_row - from_row)
    col_diff = abs(to_col - from_col)

    # King can move one square in any direction
    if row_diff <= 1 and col_diff <= 1 and (row_diff > 0 or col_diff > 0):
        return [(float(from_row), float(from_col)), (float(to_row), float(to_col))]

    return None


def _build_linear_path(
    from_row: int,
    from_col: int,
    to_row: int,
    to_col: int,
) -> list[PathPoint]:
    """Build a linear path from start to end, including all intermediate squares."""
    path: list[PathPoint] = [(float(from_row), float(from_col))]

    row_dir = 0 if to_row == from_row else (1 if to_row > from_row else -1)
    col_dir = 0 if to_col == from_col else (1 if to_col > from_col else -1)

    current_row, current_col = from_row, from_col

    while (current_row, current_col) != (to_row, to_col):
        current_row += row_dir
        current_col += col_dir
        path.append((float(current_row), float(current_col)))

    return path


def _is_path_clear(
    path: list[PathPoint],
    board: Board,
    player: int,
    active_moves: list[Move],
) -> bool:
    """Check if a path is clear of blocking pieces.

    - Own stationary pieces block at any point in the path
    - Own moving pieces' destinations block our path
    - Opponent pieces don't block (collision/capture happens during movement)
    """
    # Build set of destinations for own moving pieces
    own_moving_destinations: set[tuple[int, int]] = set()
    for move in active_moves:
        # Get the piece for this move to check player
        end_row, end_col = move.end_position
        # We need to check if this is our own piece - look up in board
        moving_piece = board.get_piece_by_id(move.piece_id)
        if moving_piece is not None and moving_piece.player == player:
            own_moving_destinations.add((int(end_row), int(end_col)))

    # Check all squares in path (excluding start)
    for row, col in path[1:]:
        int_row, int_col = int(row), int(col)

        # Check for stationary own piece
        piece_at = board.get_piece_at(int_row, int_col)
        if piece_at is not None and piece_at.player == player:
            # Check if this piece is currently moving (if so, it's not blocking)
            is_moving = any(m.piece_id == piece_at.id for m in active_moves)
            if not is_moving:
                return False  # Blocked by own stationary piece

        # Check for own moving piece destination
        if (int_row, int_col) in own_moving_destinations:
            return False  # Can't move to where own piece will end up

    return True


def _is_knight_destination_valid(
    path: list[PathPoint],
    board: Board,
    player: int,
    active_moves: list[Move],
) -> bool:
    """Check if a knight's destination is valid.

    Knights can jump over pieces but cannot land on their own pieces.
    """
    # Get destination (last point in path)
    end_row, end_col = path[-1]
    int_row, int_col = int(end_row), int(end_col)

    # Check for stationary own piece at destination
    piece_at = board.get_piece_at(int_row, int_col)
    if piece_at is not None and piece_at.player == player:
        # Check if this piece is currently moving (if so, it won't be there)
        is_moving = any(m.piece_id == piece_at.id for m in active_moves)
        if not is_moving:
            return False  # Can't land on own stationary piece

    # Check for own moving piece destination
    for move in active_moves:
        move_end_row, move_end_col = move.end_position
        moving_piece = board.get_piece_by_id(move.piece_id)
        if moving_piece is not None and moving_piece.player == player:
            if int(move_end_row) == int_row and int(move_end_col) == int_col:
                return False  # Can't land where own piece will end up

    return True


def check_castling(
    piece: Piece,
    board: Board,
    to_row: int,
    to_col: int,
    active_moves: list[Move],
    cooldowns: list[Cooldown] | None = None,
    current_tick: int = 0,
) -> tuple[Move, Move] | None:
    """Check if this is a valid castling move.

    Returns (king_move, rook_move) if valid castling, None otherwise.

    Castling requirements:
    - King has not moved
    - Rook has not moved
    - Rook is not currently moving
    - Rook is not on cooldown
    - No pieces between king and rook
    - King moves 2 squares toward rook
    """
    if piece.type != PieceType.KING:
        return None

    if piece.moved:
        return None

    from_row, from_col = piece.grid_position

    # King must stay on same row
    if to_row != from_row:
        return None

    # King must move exactly 2 squares
    col_diff = to_col - from_col
    if abs(col_diff) != 2:
        return None

    # Determine rook position based on direction
    if col_diff == 2:  # Kingside castling
        rook_col = 7
        new_rook_col = 5
    else:  # Queenside castling (col_diff == -2)
        rook_col = 0
        new_rook_col = 3

    # Find the rook
    rook = board.get_piece_at(from_row, rook_col)
    if rook is None or rook.type != PieceType.ROOK or rook.player != piece.player:
        return None

    if rook.moved:
        return None

    # Check rook is not currently moving
    if _is_piece_moving(rook.id, active_moves):
        return None

    # Check rook is not on cooldown
    if cooldowns is not None:
        for cd in cooldowns:
            if cd.piece_id == rook.id and cd.is_active(current_tick):
                return None

    # Check path is clear between king and rook
    start_col = min(from_col, rook_col) + 1
    end_col = max(from_col, rook_col)
    for col in range(start_col, end_col):
        if board.get_piece_at(from_row, col) is not None:
            return None

    # Check no pieces currently moving through the castling path
    for move in active_moves:
        move_end_row, move_end_col = move.end_position
        # Cast to int for proper comparison
        if int(move_end_row) == from_row and start_col <= int(move_end_col) < end_col:
            return None

    # Create the moves
    king_path: list[PathPoint] = [(float(from_row), float(from_col))]
    king_step = 1 if col_diff > 0 else -1
    for _ in range(2):
        king_path.append((float(from_row), king_path[-1][1] + king_step))

    rook_path: list[PathPoint] = [
        (float(from_row), float(rook_col)),
        (float(from_row), float(new_rook_col)),
    ]

    # Both moves start at tick 0 - the actual start tick will be set by the engine
    king_move = Move(piece_id=piece.id, path=king_path, start_tick=0)
    rook_move = Move(piece_id=rook.id, path=rook_path, start_tick=0)
    king_move.extra_move = rook_move

    return (king_move, rook_move)
