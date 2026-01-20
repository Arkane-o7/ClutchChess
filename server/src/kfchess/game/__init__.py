"""Game engine module for Kung Fu Chess."""

from kfchess.game.pieces import Piece, PieceType
from kfchess.game.board import Board, BoardType
from kfchess.game.moves import Move, Cooldown, compute_move_path, check_castling
from kfchess.game.collision import (
    detect_collisions,
    get_interpolated_position,
    is_piece_moving,
    is_piece_on_cooldown,
    Capture,
    CAPTURE_DISTANCE,
)
from kfchess.game.state import (
    GameState,
    GameStatus,
    Speed,
    SpeedConfig,
    SPEED_CONFIGS,
    ReplayMove,
)
from kfchess.game.engine import GameEngine, GameEvent, GameEventType

__all__ = [
    # Pieces
    "Piece",
    "PieceType",
    # Board
    "Board",
    "BoardType",
    # Moves
    "Move",
    "Cooldown",
    "compute_move_path",
    "check_castling",
    # Collision
    "detect_collisions",
    "get_interpolated_position",
    "is_piece_moving",
    "is_piece_on_cooldown",
    "Capture",
    "CAPTURE_DISTANCE",
    # State
    "GameState",
    "GameStatus",
    "Speed",
    "SpeedConfig",
    "SPEED_CONFIGS",
    "ReplayMove",
    # Engine
    "GameEngine",
    "GameEvent",
    "GameEventType",
]
