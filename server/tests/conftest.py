"""Pytest configuration and fixtures."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

# Disable rate limiting and email sending for all tests - must happen before app import
os.environ["RATE_LIMITING_ENABLED"] = "false"
os.environ["SEND_EMAILS"] = "false"

# Clear the settings cache to pick up the new environment variables
from clutchchess.settings import get_settings  # noqa: E402

get_settings.cache_clear()

from clutchchess.main import app  # noqa: E402


@pytest.fixture
async def client() -> AsyncClient:
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
