"""Integration tests for DEV_MODE authentication bypass."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from kfchess.main import app


def generate_test_email() -> str:
    """Generate a unique test email."""
    import uuid

    return f"test_{uuid.uuid4().hex[:8]}@example.com"


class TestDevModeBypass:
    """Test DEV_MODE authentication bypass functionality."""

    @pytest.mark.asyncio
    async def test_dev_mode_bypasses_auth_for_users_me(self):
        """Test that DEV_MODE allows accessing /users/me without login."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First, register a user to use as the dev user
            email = generate_test_email()
            password = "testpassword123"

            response = await client.post(
                "/api/auth/register",
                json={"email": email, "password": password},
            )
            assert response.status_code == 201
            user_data = response.json()
            user_id = user_data["id"]

            # Now test with a fresh client (no cookies) but DEV_MODE enabled
            async with AsyncClient(transport=transport, base_url="http://test") as fresh_client:
                # Create mock settings with dev mode enabled
                mock_settings = MagicMock()
                mock_settings.dev_mode = True
                mock_settings.dev_user_id = user_id

                with patch(
                    "kfchess.auth.dependencies.get_settings",
                    return_value=mock_settings,
                ):
                    # Should be able to access /users/me without authentication
                    response = await fresh_client.get("/api/users/me")

                    assert response.status_code == 200
                    data = response.json()
                    assert data["id"] == user_id
                    assert data["email"] == email

    @pytest.mark.asyncio
    async def test_dev_mode_does_not_override_authenticated_user(self):
        """Test that authenticated user is NOT overridden by DEV_MODE."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Register and login as user A
            email_a = generate_test_email()
            password = "testpassword123"

            response = await client.post(
                "/api/auth/register",
                json={"email": email_a, "password": password},
            )
            assert response.status_code == 201
            user_a_data = response.json()
            user_a_id = user_a_data["id"]

            await client.post(
                "/api/auth/login",
                data={"username": email_a, "password": password},
            )

            # Register user B (to set as dev user)
            email_b = generate_test_email()
            async with AsyncClient(transport=transport, base_url="http://test") as client_b:
                response = await client_b.post(
                    "/api/auth/register",
                    json={"email": email_b, "password": password},
                )
                assert response.status_code == 201
                user_b_data = response.json()
                user_b_id = user_b_data["id"]

            # Enable DEV_MODE pointing to user B
            mock_settings = MagicMock()
            mock_settings.dev_mode = True
            mock_settings.dev_user_id = user_b_id

            with patch(
                "kfchess.auth.dependencies.get_settings",
                return_value=mock_settings,
            ):
                # User A is authenticated, should still get user A (not B)
                response = await client.get("/api/users/me")

                assert response.status_code == 200
                data = response.json()
                # Should return user A, not the dev user B
                assert data["id"] == user_a_id
                assert data["email"] == email_a

    @pytest.mark.asyncio
    async def test_dev_mode_off_requires_auth(self):
        """Test that with DEV_MODE off, authentication is required."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create mock settings with dev mode disabled
            mock_settings = MagicMock()
            mock_settings.dev_mode = False
            mock_settings.dev_user_id = None

            with patch(
                "kfchess.auth.dependencies.get_settings",
                return_value=mock_settings,
            ):
                # Should get 401 without authentication
                response = await client.get("/api/users/me")
                assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_dev_mode_with_nonexistent_user_fails(self):
        """Test that DEV_MODE with non-existent user ID returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create mock settings pointing to non-existent user
            mock_settings = MagicMock()
            mock_settings.dev_mode = True
            mock_settings.dev_user_id = 999999  # Non-existent ID

            with patch(
                "kfchess.auth.dependencies.get_settings",
                return_value=mock_settings,
            ):
                # Should get 401 since user doesn't exist
                response = await client.get("/api/users/me")
                assert response.status_code == 401
