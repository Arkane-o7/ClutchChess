"""Game engine module for Clutch Chess."""

from clutchchess.game.board import Board, BoardType
from clutchchess.game.collision import (
    CAPTURE_DISTANCE,
    Capture,
    detect_collisions,
    get_interpolated_position,
    is_piece_moving,
    is_piece_on_cooldown,
)
from clutchchess.game.engine import GameEngine, GameEvent, GameEventType
from clutchchess.game.moves import Cooldown, Move, check_castling, compute_move_path
from clutchchess.game.pieces import Piece, PieceType
from clutchchess.game.state import (
    SPEED_CONFIGS,
    GameState,
    GameStatus,
    ReplayMove,
    Speed,
    SpeedConfig,
)

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
