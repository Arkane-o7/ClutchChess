"""Database repositories."""

from kfchess.db.repositories.active_games import ActiveGameRepository
from kfchess.db.repositories.lobbies import LobbyRepository
from kfchess.db.repositories.replay_likes import ReplayLikesRepository
from kfchess.db.repositories.replays import ReplayRepository
from kfchess.db.repositories.users import UserRepository

__all__ = [
    "ActiveGameRepository",
    "LobbyRepository",
    "ReplayLikesRepository",
    "ReplayRepository",
    "UserRepository",
]
