"""User game history repository for fast match history lookups."""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from clutchchess.db.models import UserGameHistory

logger = logging.getLogger(__name__)


class UserGameHistoryRepository:
    """Repository for user match history.

    This provides O(1) access to a user's match history via the
    indexed user_game_history table, rather than scanning all replays.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: The database session to use
        """
        self.session = session

    async def add(
        self,
        user_id: int,
        game_time: datetime,
        game_info: dict[str, Any],
    ) -> UserGameHistory:
        """Add a game to a user's match history.

        Args:
            user_id: The user's ID
            game_time: When the game was played
            game_info: Game summary data including:
                - speed: Game speed
                - player: This player's position (1-4)
                - winner: Winner position (0=draw)
                - gameId: ID of game_replays entry
                - ticks: Game duration
                - opponents: List of opponent identifiers
                - boardType: Board type (standard/four_player)

        Returns:
            The created UserGameHistory record
        """
        # Convert timezone-aware datetime to naive UTC for database
        if game_time.tzinfo is not None:
            game_time = game_time.replace(tzinfo=None)

        record = UserGameHistory(
            user_id=user_id,
            game_time=game_time,
            game_info=game_info,
        )
        self.session.add(record)
        await self.session.flush()

        logger.info(f"Added game history for user {user_id}: {game_info.get('gameId')}")
        return record

    async def list_by_user(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[UserGameHistory]:
        """List a user's match history.

        This is an O(1) operation using the (user_id, game_time) index.

        Args:
            user_id: The user's ID
            limit: Maximum number of entries to return
            offset: Number of entries to skip

        Returns:
            List of UserGameHistory records ordered by game_time DESC
        """
        result = await self.session.execute(
            select(UserGameHistory)
            .where(UserGameHistory.user_id == user_id)
            .order_by(UserGameHistory.game_time.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_user(self, user_id: int) -> int:
        """Count a user's total games.

        Args:
            user_id: The user's ID

        Returns:
            Total count of games for this user
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(UserGameHistory)
            .where(UserGameHistory.user_id == user_id)
        )
        return result.scalar_one()
