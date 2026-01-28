"""Integration tests for UserGameHistoryRepository.

These tests hit the real PostgreSQL database to catch issues like:
- Index usage for fast lookups
- JSON serialization edge cases
- Ordering and pagination

Run with: uv run pytest tests/integration/test_user_game_history_repository.py -v
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from kfchess.db.models import UserGameHistory
from kfchess.db.repositories.user_game_history import UserGameHistoryRepository

from .conftest import generate_test_id

# Use a consistent test user ID that won't conflict with real users
TEST_USER_ID = 999999


@pytest.fixture
async def cleanup_test_data(db_session: AsyncSession):
    """Clean up test data before and after tests."""
    # Clean before test
    await db_session.execute(
        delete(UserGameHistory).where(UserGameHistory.user_id == TEST_USER_ID)
    )
    await db_session.commit()

    yield

    # Clean after test
    await db_session.execute(
        delete(UserGameHistory).where(UserGameHistory.user_id == TEST_USER_ID)
    )
    await db_session.commit()


class TestUserGameHistoryRepositoryAdd:
    """Integration tests for adding game history entries."""

    @pytest.mark.asyncio
    async def test_add_creates_entry(
        self, db_session: AsyncSession, cleanup_test_data
    ):
        """Test that add creates a database entry."""
        repository = UserGameHistoryRepository(db_session)

        game_info = {
            "speed": "standard",
            "boardType": "standard",
            "player": 1,
            "winner": 1,
            "winReason": "king_captured",
            "gameId": generate_test_id(),
            "ticks": 1500,
            "opponents": ["u:456"],
        }
        game_time = datetime.now(UTC)

        record = await repository.add(TEST_USER_ID, game_time, game_info)
        await db_session.commit()

        assert record.user_id == TEST_USER_ID
        assert record.game_info == game_info

    @pytest.mark.asyncio
    async def test_add_with_timezone_aware_datetime(
        self, db_session: AsyncSession, cleanup_test_data
    ):
        """Test that timezone-aware datetimes are handled correctly."""
        repository = UserGameHistoryRepository(db_session)

        game_info = {
            "speed": "lightning",
            "boardType": "standard",
            "player": 2,
            "winner": 1,
            "gameId": generate_test_id(),
        }
        game_time = datetime.now(UTC)  # Timezone-aware

        await repository.add(TEST_USER_ID, game_time, game_info)
        await db_session.commit()

        # Verify we can read it back
        entries = await repository.list_by_user(TEST_USER_ID, limit=1, offset=0)
        assert len(entries) == 1


class TestUserGameHistoryRepositoryList:
    """Integration tests for listing game history."""

    @pytest.mark.asyncio
    async def test_list_by_user_returns_entries(
        self, db_session: AsyncSession, cleanup_test_data
    ):
        """Test that list_by_user returns the user's entries."""
        repository = UserGameHistoryRepository(db_session)

        # Add multiple entries
        base_time = datetime.now(UTC)
        for i in range(3):
            await repository.add(
                TEST_USER_ID,
                base_time - timedelta(hours=i),
                {"gameId": f"GAME{i}", "speed": "standard"},
            )
        await db_session.commit()

        entries = await repository.list_by_user(TEST_USER_ID, limit=10, offset=0)

        assert len(entries) == 3

    @pytest.mark.asyncio
    async def test_list_by_user_ordered_by_game_time_desc(
        self, db_session: AsyncSession, cleanup_test_data
    ):
        """Test that entries are ordered newest first."""
        repository = UserGameHistoryRepository(db_session)

        # Add entries with different times
        base_time = datetime.now(UTC)
        await repository.add(
            TEST_USER_ID,
            base_time - timedelta(hours=2),  # Oldest
            {"gameId": "GAME_OLD"},
        )
        await repository.add(
            TEST_USER_ID,
            base_time - timedelta(hours=1),  # Middle
            {"gameId": "GAME_MID"},
        )
        await repository.add(
            TEST_USER_ID,
            base_time,  # Newest
            {"gameId": "GAME_NEW"},
        )
        await db_session.commit()

        entries = await repository.list_by_user(TEST_USER_ID, limit=10, offset=0)

        assert len(entries) == 3
        assert entries[0].game_info["gameId"] == "GAME_NEW"
        assert entries[1].game_info["gameId"] == "GAME_MID"
        assert entries[2].game_info["gameId"] == "GAME_OLD"

    @pytest.mark.asyncio
    async def test_list_by_user_respects_limit(
        self, db_session: AsyncSession, cleanup_test_data
    ):
        """Test that limit parameter is respected."""
        repository = UserGameHistoryRepository(db_session)

        base_time = datetime.now(UTC)
        for i in range(5):
            await repository.add(
                TEST_USER_ID,
                base_time - timedelta(hours=i),
                {"gameId": f"GAME{i}"},
            )
        await db_session.commit()

        entries = await repository.list_by_user(TEST_USER_ID, limit=3, offset=0)

        assert len(entries) == 3

    @pytest.mark.asyncio
    async def test_list_by_user_respects_offset(
        self, db_session: AsyncSession, cleanup_test_data
    ):
        """Test that offset parameter is respected."""
        repository = UserGameHistoryRepository(db_session)

        base_time = datetime.now(UTC)
        for i in range(5):
            await repository.add(
                TEST_USER_ID,
                base_time - timedelta(hours=i),
                {"gameId": f"GAME{i}"},
            )
        await db_session.commit()

        # Skip first 2 entries
        entries = await repository.list_by_user(TEST_USER_ID, limit=10, offset=2)

        assert len(entries) == 3
        # Should get entries at index 2, 3, 4 (older entries)
        assert entries[0].game_info["gameId"] == "GAME2"

    @pytest.mark.asyncio
    async def test_list_by_user_returns_empty_for_nonexistent_user(
        self, db_session: AsyncSession, cleanup_test_data
    ):
        """Test that non-existent user returns empty list."""
        repository = UserGameHistoryRepository(db_session)

        entries = await repository.list_by_user(999888777, limit=10, offset=0)

        assert len(entries) == 0


class TestUserGameHistoryRepositoryCount:
    """Integration tests for counting game history."""

    @pytest.mark.asyncio
    async def test_count_by_user_returns_correct_count(
        self, db_session: AsyncSession, cleanup_test_data
    ):
        """Test that count returns the correct number."""
        repository = UserGameHistoryRepository(db_session)

        base_time = datetime.now(UTC)
        for i in range(7):
            await repository.add(
                TEST_USER_ID,
                base_time - timedelta(hours=i),
                {"gameId": f"GAME{i}"},
            )
        await db_session.commit()

        count = await repository.count_by_user(TEST_USER_ID)

        assert count == 7

    @pytest.mark.asyncio
    async def test_count_by_user_returns_zero_for_nonexistent_user(
        self, db_session: AsyncSession, cleanup_test_data
    ):
        """Test that non-existent user returns zero."""
        repository = UserGameHistoryRepository(db_session)

        count = await repository.count_by_user(999888777)

        assert count == 0


class TestUserGameHistoryRepositoryIndex:
    """Integration tests to verify index usage."""

    @pytest.mark.asyncio
    async def test_index_is_used_for_user_lookup(
        self, db_session: AsyncSession, cleanup_test_data
    ):
        """Test that the index is used for user lookups.

        This is a basic smoke test - in production you'd want to
        check EXPLAIN ANALYZE output, but that's complex to automate.
        """
        repository = UserGameHistoryRepository(db_session)

        # Add enough entries to make index usage meaningful
        base_time = datetime.now(UTC)
        for i in range(20):
            await repository.add(
                TEST_USER_ID,
                base_time - timedelta(hours=i),
                {"gameId": f"GAME{i}"},
            )
        await db_session.commit()

        # This should be fast due to index
        entries = await repository.list_by_user(TEST_USER_ID, limit=5, offset=0)

        assert len(entries) == 5
        # Verify ordering is correct (newest first due to index)
        assert entries[0].game_info["gameId"] == "GAME0"
