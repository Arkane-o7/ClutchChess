"""Tests for S3 profile picture upload service."""

from unittest.mock import MagicMock, patch

import pytest

from kfchess.services.s3 import (
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE,
    S3UploadError,
    _detect_content_type,
    upload_profile_picture,
)

# Minimal valid file headers for each image type
VALID_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
VALID_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20
VALID_GIF = b"GIF89a" + b"\x00" * 20
VALID_WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 20

VALID_FILES = {
    "image/png": VALID_PNG,
    "image/jpeg": VALID_JPEG,
    "image/gif": VALID_GIF,
    "image/webp": VALID_WEBP,
}


def _mock_s3_settings():
    return MagicMock(
        s3_enabled=True,
        aws_access_key_id="key",
        aws_secret_access_key="secret",
        aws_region="us-west-2",
        aws_bucket="test-bucket",
    )


class TestDetectContentType:
    """Tests for magic byte detection."""

    def test_detects_png(self):
        assert _detect_content_type(VALID_PNG) == "image/png"

    def test_detects_jpeg(self):
        assert _detect_content_type(VALID_JPEG) == "image/jpeg"

    def test_detects_gif87a(self):
        assert _detect_content_type(b"GIF87a" + b"\x00" * 10) == "image/gif"

    def test_detects_gif89a(self):
        assert _detect_content_type(VALID_GIF) == "image/gif"

    def test_detects_webp(self):
        assert _detect_content_type(VALID_WEBP) == "image/webp"

    def test_rejects_riff_non_webp(self):
        data = b"RIFF" + b"\x00\x00\x00\x00" + b"AVI " + b"\x00" * 20
        assert _detect_content_type(data) is None

    def test_returns_none_for_unknown(self):
        assert _detect_content_type(b"not an image") is None

    def test_returns_none_for_empty(self):
        assert _detect_content_type(b"") is None


class TestUploadProfilePicture:
    """Tests for upload_profile_picture."""

    def test_rejects_empty_file(self):
        with pytest.raises(ValueError, match="empty"):
            upload_profile_picture(b"", "image/png")

    def test_rejects_file_too_large(self):
        data = b"\x89PNG\r\n\x1a\n" + b"x" * MAX_FILE_SIZE
        with pytest.raises(ValueError, match="exceeds maximum"):
            upload_profile_picture(data, "image/png")

    def test_rejects_invalid_content_type(self):
        with pytest.raises(ValueError, match="not allowed"):
            upload_profile_picture(b"data", "text/plain")

    def test_rejects_mismatched_magic_bytes(self):
        # Claim PNG but send JPEG bytes
        with pytest.raises(ValueError, match="does not match"):
            upload_profile_picture(VALID_JPEG, "image/png")

    def test_rejects_fake_content_type(self):
        # Claim image/png but send HTML
        with pytest.raises(ValueError, match="does not match"):
            upload_profile_picture(b"<html>xss</html>", "image/png")

    @pytest.mark.parametrize("content_type", sorted(ALLOWED_CONTENT_TYPES))
    def test_accepts_valid_content_types(self, content_type):
        file_bytes = VALID_FILES[content_type]
        with patch("kfchess.services.s3.get_settings", return_value=_mock_s3_settings()):
            with patch("kfchess.services.s3._get_s3_client") as mock_get_client:
                mock_client = MagicMock()
                mock_get_client.return_value = mock_client

                url = upload_profile_picture(file_bytes, content_type)

                mock_client.put_object.assert_called_once()
                assert "test-bucket" in url
                assert "profile-pics/" in url

    def test_raises_when_s3_not_configured(self):
        with patch("kfchess.services.s3.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(s3_enabled=False)
            with pytest.raises(S3UploadError, match="not configured"):
                upload_profile_picture(VALID_PNG, "image/png")

    def test_returns_correct_url_format(self):
        settings = _mock_s3_settings()
        settings.aws_region = "us-west-2"
        settings.aws_bucket = "my-bucket"

        with patch("kfchess.services.s3.get_settings", return_value=settings):
            with patch("kfchess.services.s3._get_s3_client") as mock_get_client:
                mock_get_client.return_value = MagicMock()

                url = upload_profile_picture(VALID_JPEG, "image/jpeg")

                assert url.startswith("https://s3-us-west-2.amazonaws.com/my-bucket/profile-pics/")

    def test_wraps_boto3_errors(self):
        with patch("kfchess.services.s3.get_settings", return_value=_mock_s3_settings()):
            with patch("kfchess.services.s3._get_s3_client") as mock_get_client:
                mock_client = MagicMock()
                mock_client.put_object.side_effect = Exception("network error")
                mock_get_client.return_value = mock_client

                with pytest.raises(S3UploadError, match="Failed to upload"):
                    upload_profile_picture(VALID_PNG, "image/png")

    def test_uploads_with_public_read_acl(self):
        with patch("kfchess.services.s3.get_settings", return_value=_mock_s3_settings()):
            with patch("kfchess.services.s3._get_s3_client") as mock_get_client:
                mock_client = MagicMock()
                mock_get_client.return_value = mock_client

                upload_profile_picture(VALID_PNG, "image/png")

                call_kwargs = mock_client.put_object.call_args[1]
                assert call_kwargs["ACL"] == "public-read"
                assert call_kwargs["ContentType"] == "image/png"
                assert call_kwargs["Body"] == VALID_PNG

    def test_exactly_max_size_succeeds(self):
        # PNG header + padding to exactly MAX_FILE_SIZE
        file_bytes = VALID_PNG[:8] + b"\x00" * (MAX_FILE_SIZE - 8)
        assert len(file_bytes) == MAX_FILE_SIZE

        with patch("kfchess.services.s3.get_settings", return_value=_mock_s3_settings()):
            with patch("kfchess.services.s3._get_s3_client") as mock_get_client:
                mock_get_client.return_value = MagicMock()

                url = upload_profile_picture(file_bytes, "image/png")
                assert "profile-pics/" in url
