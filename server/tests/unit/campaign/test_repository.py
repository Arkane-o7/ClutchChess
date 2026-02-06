"""Tests for CampaignProgressRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from clutchchess.db.repositories.campaign import CampaignProgressRepository


class TestCampaignProgressRepository:
    """Tests for campaign progress repository."""

    @pytest.mark.asyncio
    async def test_get_progress_found(self) -> None:
        """Test getting existing progress."""
        progress_data = {"levelsCompleted": {"0": True}, "beltsCompleted": {}}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = progress_data

        session = AsyncMock()
        session.execute.return_value = mock_result

        repo = CampaignProgressRepository(session)
        result = await repo.get_progress(123)

        assert result == progress_data

    @pytest.mark.asyncio
    async def test_get_progress_not_found_returns_empty(self) -> None:
        """Test getting progress for user with no record."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        session = AsyncMock()
        session.execute.return_value = mock_result

        repo = CampaignProgressRepository(session)
        result = await repo.get_progress(123)

        assert result == {}

    @pytest.mark.asyncio
    async def test_update_progress(self) -> None:
        """Test updating progress."""
        session = AsyncMock()

        repo = CampaignProgressRepository(session)
        await repo.update_progress(123, {"levelsCompleted": {"0": True}})

        session.execute.assert_called_once()
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_found(self) -> None:
        """Test exists returns True when record exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1

        session = AsyncMock()
        session.execute.return_value = mock_result

        repo = CampaignProgressRepository(session)
        result = await repo.exists(123)

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_not_found(self) -> None:
        """Test exists returns False when no record."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        session = AsyncMock()
        session.execute.return_value = mock_result

        repo = CampaignProgressRepository(session)
        result = await repo.exists(123)

        assert result is False
