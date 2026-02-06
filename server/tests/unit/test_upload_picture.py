"""Tests for the POST /api/users/me/picture endpoint."""

from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from clutchchess.auth.dependencies import get_required_user_with_dev_bypass, get_user_manager_dep
from clutchchess.main import app
from clutchchess.services.s3 import MAX_FILE_SIZE, S3UploadError


def _make_user(**overrides):
    defaults = dict(
        id=1,
        username="testuser",
        email="test@example.com",
        picture_url=None,
        is_active=True,
        is_superuser=False,
        is_verified=True,
        ratings={},
        google_id=None,
        created_at=datetime.now(UTC),
        last_online=datetime.now(UTC),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.fixture
def mock_user():
    return _make_user()


@pytest.fixture
def client(mock_user) -> TestClient:
    app.dependency_overrides[get_required_user_with_dev_bypass] = lambda: mock_user

    mock_um = AsyncMock()
    app.dependency_overrides[get_user_manager_dep] = lambda: mock_um

    yield TestClient(app)

    app.dependency_overrides.clear()


class TestUploadPicture:
    """Tests for POST /api/users/me/picture."""

    def test_upload_success(self, client: TestClient) -> None:
        updated_user = _make_user(
            picture_url="https://s3-us-west-2.amazonaws.com/bucket/profile-pics/abc",
        )

        mock_um = app.dependency_overrides[get_user_manager_dep]()
        mock_um.update = AsyncMock(return_value=updated_user)

        with patch(
            "clutchchess.api.users.upload_profile_picture",
            return_value="https://s3-us-west-2.amazonaws.com/bucket/profile-pics/abc",
        ):
            response = client.post(
                "/api/users/me/picture",
                files={"file": ("avatar.png", BytesIO(b"imgdata"), "image/png")},
            )

        assert response.status_code == 200
        assert "profile-pics" in response.json()["picture_url"]

    def test_upload_invalid_content_type(self, client: TestClient) -> None:
        response = client.post(
            "/api/users/me/picture",
            files={"file": ("doc.pdf", BytesIO(b"data"), "application/pdf")},
        )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_upload_empty_file(self, client: TestClient) -> None:
        response = client.post(
            "/api/users/me/picture",
            files={"file": ("empty.png", BytesIO(b""), "image/png")},
        )

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_upload_file_too_large(self, client: TestClient) -> None:
        big_data = b"x" * (MAX_FILE_SIZE + 1)

        response = client.post(
            "/api/users/me/picture",
            files={"file": ("big.png", BytesIO(big_data), "image/png")},
        )

        assert response.status_code == 400
        assert "too large" in response.json()["detail"]

    def test_upload_s3_error_returns_generic_message(self, client: TestClient) -> None:
        with patch(
            "clutchchess.api.users.upload_profile_picture",
            side_effect=S3UploadError("boto3 internal: bucket=secret-bucket key=xyz"),
        ):
            response = client.post(
                "/api/users/me/picture",
                files={"file": ("img.png", BytesIO(b"data"), "image/png")},
            )

        assert response.status_code == 502
        detail = response.json()["detail"]
        assert "try again" in detail.lower()
        # Must NOT leak internal details
        assert "secret-bucket" not in detail
        assert "boto3" not in detail

    def test_upload_magic_byte_mismatch_returns_400(self, client: TestClient) -> None:
        with patch(
            "clutchchess.api.users.upload_profile_picture",
            side_effect=ValueError("File content does not match declared content type"),
        ):
            response = client.post(
                "/api/users/me/picture",
                files={"file": ("fake.png", BytesIO(b"notpng"), "image/png")},
            )

        assert response.status_code == 400
        assert "does not match" in response.json()["detail"]

    def test_upload_jpeg(self, client: TestClient) -> None:
        updated_user = _make_user(picture_url="https://example.com/pic.jpg")

        mock_um = app.dependency_overrides[get_user_manager_dep]()
        mock_um.update = AsyncMock(return_value=updated_user)

        with patch(
            "clutchchess.api.users.upload_profile_picture",
            return_value="https://example.com/pic.jpg",
        ):
            response = client.post(
                "/api/users/me/picture",
                files={"file": ("photo.jpg", BytesIO(b"jpegdata"), "image/jpeg")},
            )

        assert response.status_code == 200
