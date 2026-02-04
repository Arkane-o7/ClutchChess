"""Campaign service with business logic."""

from dataclasses import dataclass

from kfchess.campaign.levels import MAX_BELT
from kfchess.db.repositories.campaign import CampaignProgressRepository


@dataclass
class CampaignProgressData:
    """User's campaign progress (domain object)."""

    levels_completed: dict[str, bool]
    belts_completed: dict[str, bool]

    @property
    def current_belt(self) -> int:
        """Highest unlocked belt (1-based).

        Returns the next belt after all completed belts,
        capped at MAX_BELT.
        """
        return min(MAX_BELT, len(self.belts_completed) + 1)

    def is_level_unlocked(self, level_id: int) -> bool:
        """Check if a level is playable.

        A level is unlocked if:
        - It's level 0 (first level)
        - The previous level was completed
        - It's the first level of an unlocked belt
        """
        if level_id == 0:
            return True

        # Previous level completed
        if str(level_id - 1) in self.levels_completed:
            return True

        # First level of an unlocked belt
        belt = level_id // 8 + 1
        belt_first_level = (belt - 1) * 8
        if level_id == belt_first_level and belt <= self.current_belt:
            return True

        return False

    def is_level_completed(self, level_id: int) -> bool:
        """Check if a level has been completed."""
        return str(level_id) in self.levels_completed


class CampaignService:
    """Campaign business logic - Phase 1: infrastructure only."""

    def __init__(self, progress_repo: CampaignProgressRepository) -> None:
        """Initialize the service.

        Args:
            progress_repo: Repository for campaign progress
        """
        self.progress_repo = progress_repo

    async def get_progress(self, user_id: int) -> CampaignProgressData:
        """Get user's campaign progress.

        Args:
            user_id: The user ID

        Returns:
            CampaignProgressData with levels and belts completed
        """
        data = await self.progress_repo.get_progress(user_id)
        return CampaignProgressData(
            levels_completed=data.get("levelsCompleted", {}),
            belts_completed=data.get("beltsCompleted", {}),
        )

    async def complete_level(self, user_id: int, level_id: int) -> bool:
        """Mark a level as completed and check belt completion.

        Args:
            user_id: The user ID
            level_id: The level that was completed

        Returns:
            True if a new belt was completed
        """
        progress = await self.get_progress(user_id)

        # Mark level completed
        progress.levels_completed[str(level_id)] = True

        # Check if belt is now complete
        belt = level_id // 8 + 1
        belt_start = (belt - 1) * 8
        belt_end = belt_start + 8

        new_belt_completed = False
        all_complete = all(
            str(lvl) in progress.levels_completed for lvl in range(belt_start, belt_end)
        )

        if all_complete and str(belt) not in progress.belts_completed:
            progress.belts_completed[str(belt)] = True
            new_belt_completed = True

        # Save progress
        await self.progress_repo.update_progress(
            user_id,
            {
                "levelsCompleted": progress.levels_completed,
                "beltsCompleted": progress.belts_completed,
            },
        )

        return new_belt_completed
