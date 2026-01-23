"""Integration tests for user login and session flow."""

import pytest
from httpx import ASGITransport, AsyncClient

from kfchess.main import app


def generate_test_email() -> str:
    """Generate a unique test email."""
    import uuid

    return f"test_{uuid.uuid4().hex[:8]}@example.com"


async def register_and_login(client: AsyncClient, email: str, password: str) -> dict:
    """Helper to register and login a user, returning user data."""
    # Register
    response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201
    user_data = response.json()

    # Login
    login_response = await client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 204

    user_data["password"] = password
    return user_data


class TestLoginFlow:
    """Test the complete login flow."""

    @pytest.mark.asyncio
    async def test_login_success(self):
        """Test successful login with valid credentials."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = generate_test_email()
            password = "testpassword123"

            # Register first
            await client.post(
                "/api/auth/register",
                json={"email": email, "password": password},
            )

            # Login
            response = await client.post(
                "/api/auth/login",
                data={"username": email, "password": password},
            )

            assert response.status_code == 204
            assert "kfchess_auth" in client.cookies

    @pytest.mark.asyncio
    async def test_login_wrong_password_fails(self):
        """Test login fails with wrong password."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = generate_test_email()
            password = "testpassword123"

            # Register first
            await client.post(
                "/api/auth/register",
                json={"email": email, "password": password},
            )

            # Login with wrong password
            response = await client.post(
                "/api/auth/login",
                data={"username": email, "password": "wrongpassword123"},
            )

            assert response.status_code == 400
            data = response.json()
            assert "LOGIN_BAD_CREDENTIALS" in data.get("detail", "")

    @pytest.mark.asyncio
    async def test_login_nonexistent_user_fails(self):
        """Test login fails for non-existent user."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/login",
                data={
                    "username": "nonexistent@example.com",
                    "password": "somepassword123",
                },
            )

            assert response.status_code == 400
            data = response.json()
            assert "LOGIN_BAD_CREDENTIALS" in data.get("detail", "")

    @pytest.mark.asyncio
    async def test_login_missing_username_fails(self):
        """Test login fails when username is missing."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/login",
                data={"password": "somepassword123"},
            )

            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_missing_password_fails(self):
        """Test login fails when password is missing."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = generate_test_email()

            # Register first
            await client.post(
                "/api/auth/register",
                json={"email": email, "password": "testpassword123"},
            )

            response = await client.post(
                "/api/auth/login",
                data={"username": email},
            )

            assert response.status_code == 422


class TestSessionManagement:
    """Test session and authentication state management."""

    @pytest.mark.asyncio
    async def test_access_me_without_login_fails(self):
        """Test accessing /users/me without authentication fails."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/users/me")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_me_after_login_succeeds(self):
        """Test accessing /users/me after login succeeds."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = generate_test_email()
            password = "testpassword123"
            user_data = await register_and_login(client, email, password)

            response = await client.get("/api/users/me")
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == email
            assert data["id"] == user_data["id"]

    @pytest.mark.asyncio
    async def test_logout_clears_session(self):
        """Test that logout clears the authentication."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = generate_test_email()
            password = "testpassword123"
            await register_and_login(client, email, password)

            # Verify we're logged in
            me_response = await client.get("/api/users/me")
            assert me_response.status_code == 200

            # Logout
            logout_response = await client.post("/api/auth/logout")
            assert logout_response.status_code == 204

            # Try to access /users/me again
            me_after_logout = await client.get("/api/users/me")
            assert me_after_logout.status_code == 401

    @pytest.mark.asyncio
    async def test_multiple_logins_work(self):
        """Test that user can log in multiple times."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = generate_test_email()
            password = "testpassword123"

            # Register
            await client.post(
                "/api/auth/register",
                json={"email": email, "password": password},
            )

            # First login
            await client.post(
                "/api/auth/login",
                data={"username": email, "password": password},
            )

            # Logout
            await client.post("/api/auth/logout")

            # Second login
            login_response = await client.post(
                "/api/auth/login",
                data={"username": email, "password": password},
            )
            assert login_response.status_code == 204

            # Should be able to access /users/me
            me_response = await client.get("/api/users/me")
            assert me_response.status_code == 200


class TestUserUpdate:
    """Test user profile update functionality."""

    @pytest.mark.asyncio
    async def test_update_username(self):
        """Test updating username."""
        import uuid

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = generate_test_email()
            await register_and_login(client, email, "testpassword123")

            # Use unique username to avoid conflicts with previous test runs
            new_username = f"Updated{uuid.uuid4().hex[:8]}"
            response = await client.patch(
                "/api/users/me",
                json={"username": new_username},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["username"] == new_username

    @pytest.mark.asyncio
    async def test_update_password(self):
        """Test updating password."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = generate_test_email()
            old_password = "testpassword123"
            new_password = "newpassword456"

            await register_and_login(client, email, old_password)

            # Update password
            response = await client.patch(
                "/api/users/me",
                json={"password": new_password},
            )
            assert response.status_code == 200

            # Logout
            await client.post("/api/auth/logout")

            # Login with new password should work
            login_response = await client.post(
                "/api/auth/login",
                data={"username": email, "password": new_password},
            )
            assert login_response.status_code == 204

    @pytest.mark.asyncio
    async def test_update_password_old_password_fails(self):
        """Test that old password no longer works after update."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = generate_test_email()
            old_password = "testpassword123"
            new_password = "newpassword456"

            await register_and_login(client, email, old_password)

            # Update password
            await client.patch(
                "/api/users/me",
                json={"password": new_password},
            )

            # Logout
            await client.post("/api/auth/logout")

            # Login with old password should fail
            login_response = await client.post(
                "/api/auth/login",
                data={"username": email, "password": old_password},
            )
            assert login_response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_picture_url(self):
        """Test updating picture URL."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = generate_test_email()
            await register_and_login(client, email, "testpassword123")

            picture_url = "https://example.com/avatar.jpg"
            response = await client.patch(
                "/api/users/me",
                json={"picture_url": picture_url},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["picture_url"] == picture_url

    @pytest.mark.asyncio
    async def test_update_without_login_fails(self):
        """Test that updating without authentication fails."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/api/users/me",
                json={"username": "NewName"},
            )

            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_password_too_short_fails(self):
        """Test that updating password to too short value fails."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = generate_test_email()
            await register_and_login(client, email, "testpassword123")

            response = await client.patch(
                "/api/users/me",
                json={"password": "short"},
            )

            assert response.status_code == 422
