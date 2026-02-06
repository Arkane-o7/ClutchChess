"""Integration tests for campaign game flow.

These tests verify the full flow of starting a campaign level,
completing it, and updating progress.

Run with: uv run pytest tests/integration/test_campaign_flow.py -v
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from clutchchess.campaign.levels import get_level
from clutchchess.campaign.service import CampaignService
from clutchchess.db.models import CampaignProgress, User
from clutchchess.db.repositories.campaign import CampaignProgressRepository
from clutchchess.game.state import GameStatus
from clutchchess.services.game_service import GameService


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user for campaign tests."""
    user = User(
        email="campaign_flow_test@example.com",
        hashed_password="test_hash",
        is_active=True,
        is_verified=True,
        username="CampaignFlowTest",
        ratings={},
    )
    db_session.add(user)
    await db_session.flush()

    yield user

    # Cleanup
    from sqlalchemy import delete

    await db_session.execute(
        delete(CampaignProgress).where(CampaignProgress.user_id == user.id)
    )
    await db_session.delete(user)
    await db_session.commit()


class TestCampaignGameCreation:
    """Tests for creating campaign games."""

    async def test_create_campaign_game_with_service(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test creating a campaign game and verifying state."""
        game_service = GameService()
        level = get_level(0)
        assert level is not None

        game_id, player_key, player_num = game_service.create_campaign_game(
            level=level,
            user_id=test_user.id,
        )

        # Verify game was created
        assert game_id is not None
        assert player_key is not None
        assert player_num == 1

        # Verify game state
        state = game_service.get_game(game_id)
        assert state is not None
        assert state.status == GameStatus.PLAYING  # Auto-started

        # Verify campaign tracking
        managed = game_service.get_managed_game(game_id)
        assert managed is not None
        assert managed.campaign_level_id == 0
        assert managed.campaign_user_id == test_user.id


class TestCampaignProgressUpdate:
    """Tests for updating campaign progress after game completion."""

    async def test_complete_level_updates_progress(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that completing a level updates user progress."""
        repo = CampaignProgressRepository(db_session)
        service = CampaignService(repo)

        # Initially no progress
        progress = await service.get_progress(test_user.id)
        assert len(progress.levels_completed) == 0

        # Complete level 0
        new_belt = await service.complete_level(test_user.id, 0)
        await db_session.commit()

        # Check progress was updated
        progress = await service.get_progress(test_user.id)
        assert "0" in progress.levels_completed
        assert progress.levels_completed["0"] is True
        assert not new_belt  # Belt not complete with just one level

    async def test_complete_full_belt_marks_belt_complete(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that completing all 8 levels in a belt marks it complete."""
        repo = CampaignProgressRepository(db_session)
        service = CampaignService(repo)

        # Complete levels 0-7 (belt 1)
        for level_id in range(8):
            new_belt = await service.complete_level(test_user.id, level_id)
            await db_session.commit()

        # Last level should return True for new_belt
        assert new_belt is True

        # Check belt is marked complete
        progress = await service.get_progress(test_user.id)
        assert "1" in progress.belts_completed
        assert progress.belts_completed["1"] is True

    async def test_progress_unlocks_next_level(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that completing a level unlocks the next one."""
        repo = CampaignProgressRepository(db_session)
        service = CampaignService(repo)

        # Initially only level 0 is unlocked
        progress = await service.get_progress(test_user.id)
        assert progress.is_level_unlocked(0)
        assert not progress.is_level_unlocked(1)

        # Complete level 0
        await service.complete_level(test_user.id, 0)
        await db_session.commit()

        # Now level 1 should be unlocked
        progress = await service.get_progress(test_user.id)
        assert progress.is_level_unlocked(1)


class TestCampaignGameFlow:
    """Tests for full campaign game flow."""

    async def test_start_game_and_verify_tracking(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test starting a campaign game and verifying it's tracked correctly."""
        game_service = GameService()
        level = get_level(5)  # Pick a middle level
        assert level is not None

        game_id, _, _ = game_service.create_campaign_game(
            level=level,
            user_id=test_user.id,
        )

        managed = game_service.get_managed_game(game_id)
        assert managed is not None

        # Should track the campaign context
        assert managed.campaign_level_id == 5
        assert managed.campaign_user_id == test_user.id

        # Should have AI player
        assert 2 in managed.ai_players

    async def test_multiple_users_independent_progress(
        self, db_session: AsyncSession
    ) -> None:
        """Test that multiple users have independent progress."""
        # Create two users
        user1 = User(
            email="campaign_user1@example.com",
            hashed_password="hash1",
            is_active=True,
            is_verified=True,
            username="CampaignUser1",
            ratings={},
        )
        user2 = User(
            email="campaign_user2@example.com",
            hashed_password="hash2",
            is_active=True,
            is_verified=True,
            username="CampaignUser2",
            ratings={},
        )
        db_session.add(user1)
        db_session.add(user2)
        await db_session.flush()

        try:
            repo = CampaignProgressRepository(db_session)
            service = CampaignService(repo)

            # User 1 completes level 0
            await service.complete_level(user1.id, 0)
            await db_session.commit()

            # User 2 completes levels 0 and 1
            await service.complete_level(user2.id, 0)
            await service.complete_level(user2.id, 1)
            await db_session.commit()

            # Check progress is independent
            progress1 = await service.get_progress(user1.id)
            progress2 = await service.get_progress(user2.id)

            assert len(progress1.levels_completed) == 1
            assert len(progress2.levels_completed) == 2

            assert "0" in progress1.levels_completed
            assert "1" not in progress1.levels_completed

            assert "0" in progress2.levels_completed
            assert "1" in progress2.levels_completed

        finally:
            # Cleanup
            from sqlalchemy import delete

            await db_session.execute(
                delete(CampaignProgress).where(
                    CampaignProgress.user_id.in_([user1.id, user2.id])
                )
            )
            await db_session.delete(user1)
            await db_session.delete(user2)
            await db_session.commit()
