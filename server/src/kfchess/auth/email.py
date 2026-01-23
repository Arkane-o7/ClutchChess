"""Email sending functionality using Resend.

Handles verification and password reset emails. Falls back to console
output in development when Resend is not configured.

Email sending is done in a thread pool to avoid blocking the event loop,
since the Resend SDK uses synchronous HTTP calls.

Email failures are logged but not raised - this prevents registration
and password reset flows from failing due to email service issues.
Users can request new emails if needed.
"""

import asyncio
import logging
from functools import partial
from typing import Any

import resend

from kfchess.settings import get_settings

logger = logging.getLogger(__name__)


def _send_email_sync(api_key: str, email_params: dict[str, Any]) -> None:
    """Send email synchronously (called from thread pool).

    Args:
        api_key: Resend API key
        email_params: Email parameters dict
    """
    resend.api_key = api_key
    resend.Emails.send(email_params)


async def _send_email_async(email_params: dict[str, Any]) -> None:
    """Send email asynchronously using thread pool.

    This runs the synchronous Resend SDK call in a thread pool to avoid
    blocking the event loop.

    Args:
        email_params: Email parameters dict
    """
    settings = get_settings()
    loop = asyncio.get_event_loop()

    # Run the blocking call in the default thread pool executor
    await loop.run_in_executor(
        None,  # Use default executor
        partial(_send_email_sync, settings.resend_api_key, email_params),
    )


async def send_verification_email(email: str, token: str) -> bool:
    """Send email verification link.

    Email failures are logged but not raised to prevent registration
    from failing. Users can request a new verification email if needed.

    Args:
        email: User's email address
        token: Verification token to include in link

    Returns:
        True if email was sent successfully, False otherwise
    """
    settings = get_settings()

    if not settings.resend_enabled:
        logger.info(f"[DEV] Verification token for {email}: {token}")
        return True

    verify_url = f"{settings.frontend_url}/verify?token={token}"

    email_params = {
        "from": settings.email_from,
        "to": email,
        "subject": "Verify your Kung Fu Chess account",
        "html": f"""
        <h1>Welcome to Kung Fu Chess!</h1>
        <p>Click the link below to verify your email address:</p>
        <p><a href="{verify_url}">Verify Email</a></p>
        <p>If you didn't create this account, you can ignore this email.</p>
        <p>This link will expire in 24 hours.</p>
        """,
    }

    try:
        await _send_email_async(email_params)
        logger.info(f"Verification email sent to {email}")
        return True
    except Exception as e:
        # Log error but don't raise - user can request new verification email
        logger.error(f"Failed to send verification email to {email}: {e}")
        return False


async def send_password_reset_email(email: str, token: str) -> bool:
    """Send password reset link.

    Email failures are logged but not raised to prevent the password
    reset flow from failing and to avoid leaking information about
    which emails exist in the system.

    Args:
        email: User's email address
        token: Reset token to include in link

    Returns:
        True if email was sent successfully, False otherwise
    """
    settings = get_settings()

    if not settings.resend_enabled:
        logger.info(f"[DEV] Password reset token for {email}: {token}")
        return True

    reset_url = f"{settings.frontend_url}/reset-password?token={token}"

    email_params = {
        "from": settings.email_from,
        "to": email,
        "subject": "Reset your Kung Fu Chess password",
        "html": f"""
        <h1>Password Reset Request</h1>
        <p>Click the link below to reset your password:</p>
        <p><a href="{reset_url}">Reset Password</a></p>
        <p>If you didn't request this, you can ignore this email.</p>
        <p>This link will expire in 1 hour.</p>
        """,
    }

    try:
        await _send_email_async(email_params)
        logger.info(f"Password reset email sent to {email}")
        return True
    except Exception as e:
        # Log error but don't raise - prevents leaking email existence info
        logger.error(f"Failed to send password reset email to {email}: {e}")
        return False
