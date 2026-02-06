"""Integration tests for CampaignProgressRepository.

These tests verify the campaign progress system works correctly with the real database.

Run with: uv run pytest tests/integration/test_campaign_repository.py -v
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from clutchchess.db.models import CampaignProgress, User
from clutchchess.db.repositories.campaign import CampaignProgressRepository


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user for campaign tests."""
    user = User(
        email="campaign_test_user@example.com",
        hashed_password="test_hash",
        is_active=True,
        is_verified=True,
        username="CampaignTestUser",
        ratings={},
    )
    db_session.add(user)
    await db_session.flush()

    yield user

    # Cleanup: delete campaign progress first (if any), then user
    from sqlalchemy import delete

    await db_session.execute(
        delete(CampaignProgress).where(CampaignProgress.user_id == user.id)
    )
    await db_session.delete(user)
    await db_session.commit()


@pytest.fixture
async def test_users(db_session: AsyncSession) -> tuple[User, User]:
    """Create two test users for campaign tests."""
    user1 = User(
        email="campaign_test_user1@example.com",
        hashed_password="test_hash_1",
        is_active=True,
        is_verified=True,
        username="CampaignTestUser1",
        ratings={},
    )
    user2 = User(
        email="campaign_test_user2@example.com",
        hashed_password="test_hash_2",
        is_active=True,
        is_verified=True,
        username="CampaignTestUser2",
        ratings={},
    )
    db_session.add(user1)
    db_session.add(user2)
    await db_session.flush()

    yield user1, user2

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


class TestCampaignProgressRepositoryGetProgress:
    """Tests for get_progress operation."""

    @pytest.mark.asyncio
    async def test_get_progress_no_record(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test get_progress returns empty dict when no record exists."""
        repo = CampaignProgressRepository(db_session)

        progress = await repo.get_progress(test_user.id)

        assert progress == {}

    @pytest.mark.asyncio
    async def test_get_progress_with_record(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test get_progress returns stored progress."""
        repo = CampaignProgressRepository(db_session)

        # Create progress record
        expected_progress = {
            "levelsCompleted": {"0": True, "1": True},
            "beltsCompleted": {},
        }
        await repo.update_progress(test_user.id, expected_progress)
        await db_session.commit()

        # Fetch it back
        progress = await repo.get_progress(test_user.id)

        assert progress == expected_progress


class TestCampaignProgressRepositoryUpdateProgress:
    """Tests for update_progress operation."""

    @pytest.mark.asyncio
    async def test_update_progress_creates_record(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test update_progress creates a new record if none exists."""
        repo = CampaignProgressRepository(db_session)

        progress = {"levelsCompleted": {"0": True}, "beltsCompleted": {}}
        await repo.update_progress(test_user.id, progress)
        await db_session.commit()

        # Verify it was created
        fetched = await repo.get_progress(test_user.id)
        assert fetched == progress

    @pytest.mark.asyncio
    async def test_update_progress_updates_existing(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test update_progress updates an existing record."""
        repo = CampaignProgressRepository(db_session)

        # Create initial progress
        initial = {"levelsCompleted": {"0": True}, "beltsCompleted": {}}
        await repo.update_progress(test_user.id, initial)
        await db_session.commit()

        # Update with more progress
        updated = {
            "levelsCompleted": {"0": True, "1": True, "2": True},
            "beltsCompleted": {},
        }
        await repo.update_progress(test_user.id, updated)
        await db_session.commit()

        # Verify update
        fetched = await repo.get_progress(test_user.id)
        assert fetched == updated

    @pytest.mark.asyncio
    async def test_update_progress_belt_completion(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test updating progress with belt completion."""
        repo = CampaignProgressRepository(db_session)

        # Complete all levels in belt 1
        progress = {
            "levelsCompleted": {str(i): True for i in range(8)},
            "beltsCompleted": {"1": True},
        }
        await repo.update_progress(test_user.id, progress)
        await db_session.commit()

        fetched = await repo.get_progress(test_user.id)
        assert fetched["beltsCompleted"] == {"1": True}
        assert len(fetched["levelsCompleted"]) == 8

    @pytest.mark.asyncio
    async def test_update_progress_idempotent(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test that updating with same data is idempotent."""
        repo = CampaignProgressRepository(db_session)

        progress = {"levelsCompleted": {"0": True}, "beltsCompleted": {}}

        # Update multiple times with same data
        await repo.update_progress(test_user.id, progress)
        await db_session.commit()
        await repo.update_progress(test_user.id, progress)
        await db_session.commit()
        await repo.update_progress(test_user.id, progress)
        await db_session.commit()

        # Should still have same data
        fetched = await repo.get_progress(test_user.id)
        assert fetched == progress


class TestCampaignProgressRepositoryExists:
    """Tests for exists operation."""

    @pytest.mark.asyncio
    async def test_exists_no_record(self, db_session: AsyncSession, test_user: User):
        """Test exists returns False when no record."""
        repo = CampaignProgressRepository(db_session)

        exists = await repo.exists(test_user.id)

        assert exists is False

    @pytest.mark.asyncio
    async def test_exists_with_record(self, db_session: AsyncSession, test_user: User):
        """Test exists returns True after creating record."""
        repo = CampaignProgressRepository(db_session)

        await repo.update_progress(test_user.id, {"levelsCompleted": {}, "beltsCompleted": {}})
        await db_session.commit()

        exists = await repo.exists(test_user.id)

        assert exists is True


class TestCampaignProgressRepositoryIsolation:
    """Tests for user data isolation."""

    @pytest.mark.asyncio
    async def test_users_have_separate_progress(
        self, db_session: AsyncSession, test_users: tuple[User, User]
    ):
        """Test that each user has their own progress."""
        user1, user2 = test_users
        repo = CampaignProgressRepository(db_session)

        # User 1 completes levels 0-3
        progress1 = {
            "levelsCompleted": {"0": True, "1": True, "2": True, "3": True},
            "beltsCompleted": {},
        }
        await repo.update_progress(user1.id, progress1)

        # User 2 completes only level 0
        progress2 = {"levelsCompleted": {"0": True}, "beltsCompleted": {}}
        await repo.update_progress(user2.id, progress2)

        await db_session.commit()

        # Verify isolation
        fetched1 = await repo.get_progress(user1.id)
        fetched2 = await repo.get_progress(user2.id)

        assert len(fetched1["levelsCompleted"]) == 4
        assert len(fetched2["levelsCompleted"]) == 1

    @pytest.mark.asyncio
    async def test_nonexistent_user_returns_empty(self, db_session: AsyncSession):
        """Test that querying nonexistent user returns empty dict."""
        repo = CampaignProgressRepository(db_session)

        progress = await repo.get_progress(999999999)

        assert progress == {}


class TestCampaignProgressCascadeDelete:
    """Tests for cascade delete behavior."""

    @pytest.mark.asyncio
    async def test_deleting_user_removes_progress(self, db_session: AsyncSession):
        """Test that deleting a user cascades to delete their progress."""
        # Create user
        user = User(
            email="cascade_test@example.com",
            hashed_password="test_hash",
            is_active=True,
            is_verified=True,
            username="CascadeTestUser",
            ratings={},
        )
        db_session.add(user)
        await db_session.flush()

        # Create progress
        repo = CampaignProgressRepository(db_session)
        await repo.update_progress(
            user.id, {"levelsCompleted": {"0": True}, "beltsCompleted": {}}
        )
        await db_session.commit()

        # Verify progress exists
        assert await repo.exists(user.id) is True

        # Delete user
        await db_session.delete(user)
        await db_session.commit()

        # Progress should be gone (cascade delete)
        assert await repo.exists(user.id) is False
