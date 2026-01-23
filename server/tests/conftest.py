"""Pytest configuration and fixtures."""

import os

# Disable rate limiting for all tests
os.environ["RATE_LIMITING_ENABLED"] = "false"

# Clear the settings cache to pick up the new environment variable
from kfchess.settings import get_settings

get_settings.cache_clear()

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from kfchess.main import app  # noqa: E402


@pytest.fixture
async def client() -> AsyncClient:
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
