"""Repository for replay likes."""

import logging

from sqlalchemy import case, delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kfchess.db.models import GameReplay, ReplayLike

logger = logging.getLogger(__name__)


class ReplayLikesRepository:
    """Repository for managing replay likes."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: The database session to use
        """
        self.session = session

    async def like(self, replay_id: str, user_id: int) -> bool:
        """Add a like to a replay.

        Uses INSERT ... ON CONFLICT DO NOTHING for idempotency.

        Args:
            replay_id: The replay ID to like
            user_id: The user ID liking the replay

        Returns:
            True if like was added, False if already existed
        """
        stmt = (
            insert(ReplayLike)
            .values(
                replay_id=replay_id,
                user_id=user_id,
            )
            .on_conflict_do_nothing(constraint="uq_replay_likes_replay_user")
        )

        result = await self.session.execute(stmt)

        if result.rowcount > 0:
            # Like was added, increment counter
            await self._increment_like_count(replay_id, 1)
            await self.session.flush()
            logger.debug(f"User {user_id} liked replay {replay_id}")
            return True

        return False

    async def unlike(self, replay_id: str, user_id: int) -> bool:
        """Remove a like from a replay.

        Args:
            replay_id: The replay ID to unlike
            user_id: The user ID unliking the replay

        Returns:
            True if like was removed, False if didn't exist
        """
        stmt = delete(ReplayLike).where(
            ReplayLike.replay_id == replay_id,
            ReplayLike.user_id == user_id,
        )

        result = await self.session.execute(stmt)

        if result.rowcount > 0:
            # Like was removed, decrement counter
            await self._increment_like_count(replay_id, -1)
            await self.session.flush()
            logger.debug(f"User {user_id} unliked replay {replay_id}")
            return True

        return False

    async def has_liked(self, replay_id: str, user_id: int) -> bool:
        """Check if a user has liked a replay.

        Args:
            replay_id: The replay ID
            user_id: The user ID

        Returns:
            True if the user has liked the replay
        """
        result = await self.session.execute(
            select(ReplayLike.id).where(
                ReplayLike.replay_id == replay_id,
                ReplayLike.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_likes_for_replays(
        self, replay_ids: list[str], user_id: int | None
    ) -> dict[str, bool]:
        """Get like status for multiple replays for a user.

        Args:
            replay_ids: List of replay IDs to check
            user_id: The user ID (None for unauthenticated)

        Returns:
            Dict mapping replay_id to whether user has liked it
        """
        if user_id is None or not replay_ids:
            return {rid: False for rid in replay_ids}

        result = await self.session.execute(
            select(ReplayLike.replay_id).where(
                ReplayLike.replay_id.in_(replay_ids),
                ReplayLike.user_id == user_id,
            )
        )

        liked_ids = {row[0] for row in result.fetchall()}
        return {rid: rid in liked_ids for rid in replay_ids}

    async def _increment_like_count(self, replay_id: str, delta: int) -> None:
        """Atomically increment or decrement the like_count on GameReplay.

        Uses atomic SQL UPDATE to avoid race conditions.

        Args:
            replay_id: The replay ID
            delta: Amount to change (positive or negative)
        """
        # Use case expression to ensure count never goes below 0
        new_count = case(
            (GameReplay.like_count + delta < 0, 0),
            else_=GameReplay.like_count + delta,
        )
        stmt = (
            update(GameReplay)
            .where(GameReplay.id == replay_id)
            .values(like_count=new_count)
        )
        await self.session.execute(stmt)
