"""S3 service for profile picture uploads."""

import logging
import uuid

import boto3

from kfchess.settings import get_settings

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 64 * 1024  # 64 KB
MIN_FILE_SIZE = 1  # At least 1 byte
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

# Magic byte signatures for allowed image types
_MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",  # WebP starts with RIFF....WEBP
}

# Reusable boto3 client (lazy singleton)
_s3_client = None


class S3UploadError(Exception):
    """Raised when S3 upload fails."""


def _detect_content_type(file_bytes: bytes) -> str | None:
    """Detect image content type from magic bytes."""
    for magic, content_type in _MAGIC_BYTES.items():
        if file_bytes[:len(magic)] == magic:
            # Extra check for WebP: RIFF....WEBP
            if magic == b"RIFF" and (len(file_bytes) < 12 or file_bytes[8:12] != b"WEBP"):
                continue
            return content_type
    return None


def _get_s3_client():
    """Get or create a reusable boto3 S3 client."""
    global _s3_client
    if _s3_client is None:
        settings = get_settings()
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
    return _s3_client


def upload_profile_picture(file_bytes: bytes, content_type: str) -> str:
    """Upload a profile picture to S3.

    Args:
        file_bytes: Raw image bytes (max 64KB).
        content_type: MIME type (must be image/jpeg, image/png, image/gif, or image/webp).

    Returns:
        Public URL of the uploaded image.

    Raises:
        ValueError: If file is too small, too large, content type is invalid,
            or file bytes don't match declared content type.
        S3UploadError: If the upload to S3 fails.
    """
    if len(file_bytes) < MIN_FILE_SIZE:
        raise ValueError("File is empty")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError(f"File size {len(file_bytes)} exceeds maximum of {MAX_FILE_SIZE} bytes")

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(
            f"Content type '{content_type}' not allowed. "
            f"Must be one of: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
        )

    detected_type = _detect_content_type(file_bytes)
    if detected_type != content_type:
        raise ValueError("File content does not match declared content type")

    settings = get_settings()
    if not settings.s3_enabled:
        raise S3UploadError("S3 is not configured")

    key = f"profile-pics/{uuid.uuid4()}"

    try:
        client = _get_s3_client()
        client.put_object(
            Bucket=settings.aws_bucket,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
            ACL="public-read",
        )
    except S3UploadError:
        raise
    except Exception as e:
        logger.exception("S3 upload failed")
        raise S3UploadError(f"Failed to upload to S3: {e}") from e

    return f"https://s3-{settings.aws_region}.amazonaws.com/{settings.aws_bucket}/{key}"
