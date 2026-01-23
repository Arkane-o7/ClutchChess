"""Tests for authentication Pydantic schemas."""

import pytest
from pydantic import ValidationError

from kfchess.auth.schemas import UserCreate, UserRead, UserUpdate


class TestUserCreateSchema:
    """Tests for UserCreate schema validation."""

    def test_valid_user_create_minimal(self):
        """Test creating user with only required fields."""
        user = UserCreate(
            email="user@example.com",
            password="validpass123",
        )
        assert user.email == "user@example.com"
        assert user.password == "validpass123"
        assert user.username is None  # Optional, will be auto-generated

    def test_valid_user_create_with_username(self):
        """Test creating user with custom username."""
        user = UserCreate(
            email="user@example.com",
            password="validpass123",
            username="CustomUser",
        )
        assert user.username == "CustomUser"

    def test_password_minimum_length_valid(self):
        """Test password at exactly minimum length (8 chars)."""
        user = UserCreate(
            email="user@example.com",
            password="12345678",  # Exactly 8 characters
        )
        assert user.password == "12345678"

    def test_password_maximum_length_valid(self):
        """Test password at maximum length (128 chars)."""
        password = "x" * 128
        user = UserCreate(
            email="user@example.com",
            password=password,
        )
        assert len(user.password) == 128

    def test_password_too_short_raises_error(self):
        """Test password below minimum length raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="user@example.com",
                password="1234567",  # 7 characters - too short
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "at least 8 characters" in str(errors[0]["msg"])

    def test_password_too_long_raises_error(self):
        """Test password above maximum length raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="user@example.com",
                password="x" * 129,  # 129 characters - too long
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "at most 128 characters" in str(errors[0]["msg"])

    def test_password_empty_raises_error(self):
        """Test empty password raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="user@example.com",
                password="",
            )
        errors = exc_info.value.errors()
        assert any("at least 8 characters" in str(e["msg"]) for e in errors)

    def test_invalid_email_raises_error(self):
        """Test invalid email format raises validation error."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="not-an-email",
                password="validpass123",
            )

    def test_missing_email_raises_error(self):
        """Test missing email raises validation error."""
        with pytest.raises(ValidationError):
            UserCreate(password="validpass123")

    def test_missing_password_raises_error(self):
        """Test missing password raises validation error."""
        with pytest.raises(ValidationError):
            UserCreate(email="user@example.com")


class TestUserUpdateSchema:
    """Tests for UserUpdate schema validation."""

    def test_update_username_only(self):
        """Test updating only username."""
        update = UserUpdate(username="NewUsername")
        assert update.username == "NewUsername"
        assert update.password is None
        assert update.picture_url is None

    def test_update_picture_url_only(self):
        """Test updating only picture URL."""
        update = UserUpdate(picture_url="https://example.com/photo.jpg")
        assert update.picture_url == "https://example.com/photo.jpg"

    def test_update_password_valid(self):
        """Test updating password with valid value."""
        update = UserUpdate(password="newpassword123")
        assert update.password == "newpassword123"

    def test_update_password_too_short_raises_error(self):
        """Test updating password with too short value raises error."""
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(password="short")
        errors = exc_info.value.errors()
        assert any("at least 8 characters" in str(e["msg"]) for e in errors)

    def test_update_password_too_long_raises_error(self):
        """Test updating password with too long value raises error."""
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(password="x" * 129)
        errors = exc_info.value.errors()
        assert any("at most 128 characters" in str(e["msg"]) for e in errors)

    def test_update_password_none_is_valid(self):
        """Test that None password is valid (means don't update)."""
        update = UserUpdate(username="NewName", password=None)
        assert update.password is None

    def test_update_empty_is_valid(self):
        """Test that empty update is valid."""
        update = UserUpdate()
        assert update.username is None
        assert update.password is None
        assert update.picture_url is None

    def test_update_multiple_fields(self):
        """Test updating multiple fields at once."""
        update = UserUpdate(
            username="NewName",
            password="newpassword123",
            picture_url="https://example.com/new.jpg",
        )
        assert update.username == "NewName"
        assert update.password == "newpassword123"
        assert update.picture_url == "https://example.com/new.jpg"


class TestUserReadSchema:
    """Tests for UserRead schema."""

    def test_user_read_includes_required_fields(self):
        """Test UserRead includes all required fields."""
        from datetime import datetime

        user_data = {
            "id": 1,
            "email": "user@example.com",
            "is_active": True,
            "is_verified": True,
            "is_superuser": False,
            "username": "TestUser",
            "picture_url": None,
            "google_id": None,
            "ratings": {"standard": 1200},
            "created_at": datetime.now(),
            "last_online": datetime.now(),
        }
        user = UserRead(**user_data)
        assert user.id == 1
        assert user.email == "user@example.com"
        assert user.username == "TestUser"
        assert user.ratings == {"standard": 1200}

    def test_user_read_default_ratings(self):
        """Test UserRead has default empty ratings."""
        from datetime import datetime

        user_data = {
            "id": 1,
            "email": "user@example.com",
            "is_active": True,
            "is_verified": False,
            "is_superuser": False,
            "username": "TestUser",
            "created_at": datetime.now(),
            "last_online": datetime.now(),
        }
        user = UserRead(**user_data)
        assert user.ratings == {}
