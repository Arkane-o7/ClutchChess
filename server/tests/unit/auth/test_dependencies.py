"""Tests for authentication dependencies including DEV_MODE bypass."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kfchess.auth.dependencies import (
    get_current_user_with_dev_bypass,
    get_required_user_with_dev_bypass,
)


class TestGetCurrentUserWithDevBypass:
    """Tests for DEV_MODE user bypass logic."""

    @pytest.mark.asyncio
    async def test_returns_authenticated_user_when_present(self, mock_user):
        """Test that authenticated user is returned regardless of DEV_MODE."""
        request = MagicMock()

        # Even with DEV_MODE potentially enabled, authenticated user takes precedence
        result = await get_current_user_with_dev_bypass(request, mock_user)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_returns_none_when_no_auth_and_dev_mode_off(self, mock_settings):
        """Test returns None when not authenticated and DEV_MODE is off."""
        request = MagicMock()
        mock_settings.dev_mode = False
        mock_settings.dev_user_id = None

        with patch("kfchess.auth.dependencies.get_settings", return_value=mock_settings):
            result = await get_current_user_with_dev_bypass(request, None)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_dev_mode_on_but_no_dev_user_id(self, mock_settings):
        """Test returns None when DEV_MODE on but no dev_user_id configured."""
        request = MagicMock()
        mock_settings.dev_mode = True
        mock_settings.dev_user_id = None

        with patch("kfchess.auth.dependencies.get_settings", return_value=mock_settings):
            result = await get_current_user_with_dev_bypass(request, None)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_dev_user_when_dev_mode_enabled(self, mock_settings, mock_user):
        """Test returns dev user when DEV_MODE enabled and no auth."""
        request = MagicMock()
        mock_settings.dev_mode = True
        mock_settings.dev_user_id = 999

        mock_user.id = 999
        mock_user.username = "DevUser"

        with patch("kfchess.auth.dependencies.get_settings", return_value=mock_settings):
            with patch("kfchess.db.session.async_session_factory") as mock_factory:
                mock_session = AsyncMock()
                mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

                with patch("kfchess.db.repositories.UserRepository") as MockUserRepo:
                    mock_repo = MagicMock()
                    mock_repo.get_by_id = AsyncMock(return_value=mock_user)
                    MockUserRepo.return_value = mock_repo

                    result = await get_current_user_with_dev_bypass(request, None)

        assert result == mock_user
        mock_repo.get_by_id.assert_called_once_with(999)

    @pytest.mark.asyncio
    async def test_returns_none_when_dev_user_not_found(self, mock_settings):
        """Test returns None when dev_user_id points to non-existent user."""
        request = MagicMock()
        mock_settings.dev_mode = True
        mock_settings.dev_user_id = 999

        with patch("kfchess.auth.dependencies.get_settings", return_value=mock_settings):
            with patch("kfchess.db.session.async_session_factory") as mock_factory:
                mock_session = AsyncMock()
                mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

                with patch("kfchess.db.repositories.UserRepository") as MockUserRepo:
                    mock_repo = MagicMock()
                    mock_repo.get_by_id = AsyncMock(return_value=None)
                    MockUserRepo.return_value = mock_repo

                    result = await get_current_user_with_dev_bypass(request, None)

        assert result is None

    @pytest.mark.asyncio
    async def test_does_not_override_authenticated_user_in_dev_mode(self, mock_settings, mock_user):
        """Test that authenticated user is NOT overridden even in DEV_MODE."""
        request = MagicMock()
        mock_settings.dev_mode = True
        mock_settings.dev_user_id = 999

        # Authenticated as user 1, but dev_user_id is 999
        mock_user.id = 1
        mock_user.username = "AuthenticatedUser"

        # The authenticated user should be returned, not the dev user
        result = await get_current_user_with_dev_bypass(request, mock_user)

        assert result == mock_user
        assert result.id == 1


class TestGetRequiredUserWithDevBypass:
    """Tests for required user dependency with DEV_MODE bypass."""

    @pytest.mark.asyncio
    async def test_returns_user_when_authenticated(self, mock_user):
        """Test returns user when authenticated."""
        request = MagicMock()

        with patch(
            "kfchess.auth.dependencies.get_current_user_with_dev_bypass",
            new_callable=AsyncMock,
            return_value=mock_user,
        ):
            result = await get_required_user_with_dev_bypass(request, mock_user)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_returns_dev_user_in_dev_mode(self, mock_settings, mock_user):
        """Test returns dev user when in DEV_MODE."""
        request = MagicMock()

        with patch(
            "kfchess.auth.dependencies.get_current_user_with_dev_bypass",
            new_callable=AsyncMock,
            return_value=mock_user,
        ):
            result = await get_required_user_with_dev_bypass(request, None)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_raises_401_when_no_user(self):
        """Test raises 401 Unauthorized when no user available."""
        from fastapi import HTTPException

        request = MagicMock()

        with patch(
            "kfchess.auth.dependencies.get_current_user_with_dev_bypass",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_required_user_with_dev_bypass(request, None)

        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_raises_401_when_dev_mode_off_and_no_auth(self, mock_settings):
        """Test raises 401 when DEV_MODE off and not authenticated."""
        from fastapi import HTTPException

        request = MagicMock()
        mock_settings.dev_mode = False

        with patch(
            "kfchess.auth.dependencies.get_current_user_with_dev_bypass",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_required_user_with_dev_bypass(request, None)

        assert exc_info.value.status_code == 401
