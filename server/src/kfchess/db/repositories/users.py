"""User repository for database operations."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kfchess.db.models import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user database operations.

    Note: Most user CRUD is handled by FastAPI-Users. This repository
    provides additional queries needed by the application.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: The database session to use
        """
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        """Get a user by ID.

        Args:
            user_id: The user's ID

        Returns:
            User or None if not found
        """
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Get a user by username.

        Args:
            username: The username to look up

        Returns:
            User or None if not found
        """
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_google_id(self, google_id: str) -> User | None:
        """Get a user by Google OAuth ID.

        Used for legacy user lookup during OAuth flow.

        Args:
            google_id: The Google account ID

        Returns:
            User or None if not found
        """
        result = await self.session.execute(select(User).where(User.google_id == google_id))
        return result.scalar_one_or_none()

    async def is_username_available(self, username: str) -> bool:
        """Check if a username is available.

        Args:
            username: The username to check

        Returns:
            True if the username is not taken
        """
        result = await self.session.execute(
            select(User.id).where(User.username == username).limit(1)
        )
        return result.scalar_one_or_none() is None
