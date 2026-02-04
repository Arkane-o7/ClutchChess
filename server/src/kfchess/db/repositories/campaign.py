"""Campaign progress repository for database operations."""

import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kfchess.db.models import CampaignProgress

logger = logging.getLogger(__name__)


class CampaignProgressRepository:
    """Repository for managing campaign progress in the database."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: The database session to use
        """
        self.session = session

    async def get_progress(self, user_id: int) -> dict:
        """Get progress JSONB for a user.

        Args:
            user_id: The user ID

        Returns:
            Progress dict or empty dict if not found
        """
        result = await self.session.execute(
            select(CampaignProgress.progress).where(
                CampaignProgress.user_id == user_id
            )
        )
        row = result.scalar_one_or_none()
        return row if row is not None else {}

    async def update_progress(self, user_id: int, progress: dict) -> None:
        """Update or create progress for a user (upsert).

        Args:
            user_id: The user ID
            progress: The progress dict to save
        """
        # Use PostgreSQL INSERT ... ON CONFLICT DO UPDATE for upsert
        stmt = insert(CampaignProgress).values(
            user_id=user_id,
            progress=progress,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_campaign_progress_user_id",
            set_={"progress": progress},
        )
        await self.session.execute(stmt)
        await self.session.flush()

        logger.debug(f"Updated campaign progress for user {user_id}")

    async def exists(self, user_id: int) -> bool:
        """Check if progress record exists for a user.

        Args:
            user_id: The user ID

        Returns:
            True if progress exists
        """
        result = await self.session.execute(
            select(CampaignProgress.id).where(CampaignProgress.user_id == user_id)
        )
        return result.scalar_one_or_none() is not None
