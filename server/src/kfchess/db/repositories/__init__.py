"""Database repositories."""

from kfchess.db.repositories.replays import ReplayRepository
from kfchess.db.repositories.users import UserRepository

__all__ = ["ReplayRepository", "UserRepository"]
