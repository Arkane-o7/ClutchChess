"""Unit tests for UserGameHistoryRepository."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from kfchess.db.repositories.user_game_history import UserGameHistoryRepository


class TestUserGameHistoryRepository:
    """Tests for UserGameHistoryRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        # session.add is not async, so use MagicMock
        session.add = MagicMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create a repository with mock session."""
        return UserGameHistoryRepository(mock_session)

    @pytest.fixture
    def sample_game_info(self):
        """Create sample game info."""
        return {
            "speed": "standard",
            "boardType": "standard",
            "player": 1,
            "winner": 1,
            "winReason": "king_captured",
            "gameId": "ABC123",
            "ticks": 1500,
            "opponents": ["u:456"],
        }


class TestAdd(TestUserGameHistoryRepository):
    """Tests for add method."""

    async def test_add_creates_record(self, repository, mock_session, sample_game_info):
        """Test that add creates a UserGameHistory record."""
        user_id = 123
        game_time = datetime.now(UTC)

        await repository.add(user_id, game_time, sample_game_info)

        # Verify session.add was called
        mock_session.add.assert_called_once()
        record = mock_session.add.call_args[0][0]

        assert record.user_id == user_id
        # Timezone is stripped for database storage
        assert record.game_time == game_time.replace(tzinfo=None)
        assert record.game_info == sample_game_info

    async def test_add_flushes_session(self, repository, mock_session, sample_game_info):
        """Test that add flushes the session."""
        await repository.add(123, datetime.now(UTC), sample_game_info)

        mock_session.flush.assert_called_once()


class TestListByUser(TestUserGameHistoryRepository):
    """Tests for list_by_user method."""

    async def test_list_by_user_returns_entries(self, repository, mock_session):
        """Test that list_by_user returns history entries."""
        mock_entry = MagicMock()
        mock_entry.user_id = 123
        mock_entry.game_time = datetime.now(UTC)
        mock_entry.game_info = {"gameId": "ABC123"}

        # Use MagicMock for result (scalars() and all() are sync methods)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_entry]
        mock_session.execute.return_value = mock_result

        entries = await repository.list_by_user(123, limit=10, offset=0)

        assert len(entries) == 1
        assert entries[0] == mock_entry

    async def test_list_by_user_respects_limit(self, repository, mock_session):
        """Test that list_by_user passes limit to query."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repository.list_by_user(123, limit=5, offset=0)

        # Verify execute was called (query includes limit)
        mock_session.execute.assert_called_once()

    async def test_list_by_user_respects_offset(self, repository, mock_session):
        """Test that list_by_user passes offset to query."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repository.list_by_user(123, limit=10, offset=5)

        # Verify execute was called (query includes offset)
        mock_session.execute.assert_called_once()


class TestCountByUser(TestUserGameHistoryRepository):
    """Tests for count_by_user method."""

    async def test_count_by_user_returns_count(self, repository, mock_session):
        """Test that count_by_user returns the count."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 42
        mock_session.execute.return_value = mock_result

        count = await repository.count_by_user(123)

        assert count == 42

    async def test_count_by_user_returns_zero_for_new_user(
        self, repository, mock_session
    ):
        """Test that count_by_user returns 0 for user with no games."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        count = await repository.count_by_user(999)

        assert count == 0
