"""Extract AI-friendly state from GameState."""

from dataclasses import dataclass, field
from enum import Enum

from kfchess.game.moves import Cooldown, Move
from kfchess.game.pieces import Piece, PieceType
from kfchess.game.state import GameState


class PieceStatus(Enum):
    """Status of a piece from the AI's perspective."""

    IDLE = "idle"  # Can move right now
    TRAVELING = "traveling"  # Currently moving
    COOLDOWN = "cooldown"  # Waiting for cooldown


@dataclass
class AIPiece:
    """AI-friendly view of a piece."""

    piece: Piece
    status: PieceStatus
    cooldown_remaining: int  # Ticks remaining on cooldown (0 if not on cooldown)
    # For traveling pieces owned by AI: destination
    destination: tuple[int, int] | None
    # For traveling enemy pieces: direction of travel (row_delta, col_delta)
    travel_direction: tuple[float, float] | None


@dataclass
class AIState:
    """AI-friendly snapshot of the game state."""

    pieces: list[AIPiece]
    ai_player: int
    current_tick: int
    board_width: int
    board_height: int
    # Pre-computed lookups (populated at construction)
    pieces_by_id: dict[str, AIPiece] = field(default_factory=dict)
    _movable: list[AIPiece] = field(default_factory=list)
    _enemy_pieces: list[AIPiece] = field(default_factory=list)
    _enemy_king: AIPiece | None = None
    _own_king: AIPiece | None = None

    def get_movable_pieces(self) -> list[AIPiece]:
        """Get pieces that can move right now (idle, not captured)."""
        return self._movable

    def get_enemy_pieces(self) -> list[AIPiece]:
        """Get all non-captured enemy pieces."""
        return self._enemy_pieces

    def get_enemy_king(self) -> AIPiece | None:
        """Get the nearest enemy king."""
        return self._enemy_king

    def get_own_king(self) -> AIPiece | None:
        """Get the AI's own king."""
        return self._own_king


class StateExtractor:
    """Converts GameState into AI-friendly structures."""

    @staticmethod
    def extract(state: GameState, ai_player: int) -> AIState:
        """Extract AI state from game state.

        Args:
            state: Current game state
            ai_player: Player number the AI controls

        Returns:
            AI-friendly state snapshot
        """
        # Build lookup dicts once
        move_by_piece: dict[str, Move] = {
            m.piece_id: m for m in state.active_moves
        }
        cooldown_by_piece: dict[str, Cooldown] = {
            c.piece_id: c
            for c in state.cooldowns
            if c.is_active(state.current_tick)
        }

        pieces: list[AIPiece] = []
        pieces_by_id: dict[str, AIPiece] = {}
        movable: list[AIPiece] = []
        enemy_pieces: list[AIPiece] = []
        enemy_king: AIPiece | None = None
        own_king: AIPiece | None = None

        for piece in state.board.pieces:
            if piece.captured:
                continue

            # Determine status using dicts (O(1) lookups)
            move = move_by_piece.get(piece.id)
            cd = cooldown_by_piece.get(piece.id)

            if move is not None:
                status = PieceStatus.TRAVELING
            elif cd is not None:
                status = PieceStatus.COOLDOWN
            else:
                status = PieceStatus.IDLE

            # Cooldown remaining
            cooldown_remaining = 0
            if cd is not None:
                end_tick = cd.start_tick + cd.duration
                cooldown_remaining = max(0, end_tick - state.current_tick)

            # Travel info
            destination = None
            travel_direction = None
            if move is not None:
                end_row, end_col = move.end_position
                if piece.player == ai_player:
                    destination = (int(end_row), int(end_col))
                else:
                    start_row, start_col = move.start_position
                    dr = end_row - start_row
                    dc = end_col - start_col
                    length = max(abs(dr), abs(dc))
                    if length > 0:
                        travel_direction = (dr / length, dc / length)

            ai_piece = AIPiece(
                piece=piece,
                status=status,
                cooldown_remaining=cooldown_remaining,
                destination=destination,
                travel_direction=travel_direction,
            )
            pieces.append(ai_piece)
            pieces_by_id[piece.id] = ai_piece

            # Populate cached lists
            if piece.player == ai_player:
                if status == PieceStatus.IDLE:
                    movable.append(ai_piece)
                if piece.type == PieceType.KING:
                    own_king = ai_piece
            else:
                enemy_pieces.append(ai_piece)
                if piece.type == PieceType.KING:
                    enemy_king = ai_piece

        return AIState(
            pieces=pieces,
            ai_player=ai_player,
            current_tick=state.current_tick,
            board_width=state.board.width,
            board_height=state.board.height,
            pieces_by_id=pieces_by_id,
            _movable=movable,
            _enemy_pieces=enemy_pieces,
            _enemy_king=enemy_king,
            _own_king=own_king,
        )
