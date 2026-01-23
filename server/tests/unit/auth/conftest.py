"""Pytest fixtures for auth unit tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from kfchess.db.models import User


@pytest.fixture
def mock_user() -> User:
    """Create a mock user for testing."""
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.username = "TestUser123"
    user.hashed_password = "hashed_password_here"
    user.is_active = True
    user.is_verified = True
    user.is_superuser = False
    user.google_id = None
    user.picture_url = None
    user.ratings = {}
    return user


@pytest.fixture
def mock_legacy_user() -> User:
    """Create a mock legacy Google-only user for testing."""
    user = MagicMock(spec=User)
    user.id = 2
    user.email = "legacy@gmail.com"
    user.username = "LegacyUser456"
    user.hashed_password = None  # No password - Google OAuth only
    user.is_active = True
    user.is_verified = True
    user.is_superuser = False
    user.google_id = "legacy@gmail.com"  # Same as email for legacy users
    user.picture_url = "https://example.com/photo.jpg"
    user.ratings = {"standard": 1200}
    return user


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.dev_mode = False
    settings.dev_user_id = None
    settings.secret_key = "test-secret-key-for-testing"
    settings.resend_enabled = False
    settings.resend_api_key = ""
    settings.send_emails = False  # Default to not sending real emails
    settings.frontend_url = "http://localhost:5173"
    settings.email_from = "noreply@test.com"
    settings.google_oauth_enabled = False
    settings.google_client_id = ""
    settings.google_client_secret = ""
    return settings


@pytest.fixture
def mock_user_db():
    """Create a mock user database for testing."""
    user_db = AsyncMock()
    user_db.session = AsyncMock()
    return user_db
