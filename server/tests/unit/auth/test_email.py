"""Tests for email sending functionality."""

from unittest.mock import AsyncMock, patch

import pytest

from clutchchess.auth.email import (
    send_password_reset_email,
    send_verification_email,
)


class TestSendVerificationEmail:
    """Tests for verification email sending."""

    @pytest.mark.asyncio
    async def test_logs_token_when_resend_disabled(self, mock_settings):
        """Test verification token logged to console when Resend disabled."""
        mock_settings.resend_enabled = False

        with patch("clutchchess.auth.email.get_settings", return_value=mock_settings):
            with patch("clutchchess.auth.email.logger") as mock_logger:
                result = await send_verification_email("user@test.com", "test_token_123")

        assert result is True
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        assert "[DEV]" in log_message
        assert "test_token_123" in log_message
        assert "user@test.com" in log_message

    @pytest.mark.asyncio
    async def test_sends_email_when_resend_enabled(self, mock_settings):
        """Test verification email is sent when Resend configured."""
        mock_settings.resend_enabled = True
        mock_settings.send_emails = True
        mock_settings.resend_api_key = "test_api_key"
        mock_settings.frontend_url = "http://localhost:5173"
        mock_settings.email_from = "noreply@test.com"

        with patch("clutchchess.auth.email.get_settings", return_value=mock_settings):
            with patch("clutchchess.auth.email._send_email_async", new_callable=AsyncMock) as mock_send:
                result = await send_verification_email("user@test.com", "verify_token")

        assert result is True
        mock_send.assert_called_once()

        # Verify email params
        call_args = mock_send.call_args[0][0]
        assert call_args["to"] == "user@test.com"
        assert call_args["from"] == "noreply@test.com"
        assert "Verify your Clutch Chess account" in call_args["subject"]
        assert "verify_token" in call_args["html"]
        assert "http://localhost:5173/verify" in call_args["html"]

    @pytest.mark.asyncio
    async def test_returns_false_on_send_failure(self, mock_settings):
        """Test returns False when email sending fails."""
        mock_settings.resend_enabled = True
        mock_settings.send_emails = True
        mock_settings.resend_api_key = "test_api_key"
        mock_settings.frontend_url = "http://localhost:5173"
        mock_settings.email_from = "noreply@test.com"

        with patch("clutchchess.auth.email.get_settings", return_value=mock_settings):
            with patch(
                "clutchchess.auth.email._send_email_async",
                new_callable=AsyncMock,
                side_effect=Exception("API error"),
            ):
                with patch("clutchchess.auth.email.logger") as mock_logger:
                    result = await send_verification_email("user@test.com", "token")

        assert result is False
        # Should log the error
        mock_logger.error.assert_called_once()
        error_message = mock_logger.error.call_args[0][0]
        assert "Failed to send verification email" in error_message

    @pytest.mark.asyncio
    async def test_does_not_raise_on_failure(self, mock_settings):
        """Test that email failure doesn't raise exception."""
        mock_settings.resend_enabled = True
        mock_settings.send_emails = True
        mock_settings.resend_api_key = "test_api_key"
        mock_settings.frontend_url = "http://localhost:5173"
        mock_settings.email_from = "noreply@test.com"

        with patch("clutchchess.auth.email.get_settings", return_value=mock_settings):
            with patch(
                "clutchchess.auth.email._send_email_async",
                new_callable=AsyncMock,
                side_effect=Exception("Network error"),
            ):
                # Should not raise
                result = await send_verification_email("user@test.com", "token")

        assert result is False


class TestSendPasswordResetEmail:
    """Tests for password reset email sending."""

    @pytest.mark.asyncio
    async def test_logs_token_when_resend_disabled(self, mock_settings):
        """Test password reset token logged when Resend disabled."""
        mock_settings.resend_enabled = False

        with patch("clutchchess.auth.email.get_settings", return_value=mock_settings):
            with patch("clutchchess.auth.email.logger") as mock_logger:
                result = await send_password_reset_email("user@test.com", "reset_token_456")

        assert result is True
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        assert "[DEV]" in log_message
        assert "reset_token_456" in log_message

    @pytest.mark.asyncio
    async def test_sends_email_when_resend_enabled(self, mock_settings):
        """Test password reset email is sent when Resend configured."""
        mock_settings.resend_enabled = True
        mock_settings.send_emails = True
        mock_settings.resend_api_key = "test_api_key"
        mock_settings.frontend_url = "http://localhost:5173"
        mock_settings.email_from = "noreply@test.com"

        with patch("clutchchess.auth.email.get_settings", return_value=mock_settings):
            with patch("clutchchess.auth.email._send_email_async", new_callable=AsyncMock) as mock_send:
                result = await send_password_reset_email("user@test.com", "reset_token")

        assert result is True
        mock_send.assert_called_once()

        # Verify email params
        call_args = mock_send.call_args[0][0]
        assert call_args["to"] == "user@test.com"
        assert "Reset your Clutch Chess password" in call_args["subject"]
        assert "reset_token" in call_args["html"]
        assert "http://localhost:5173/reset-password" in call_args["html"]

    @pytest.mark.asyncio
    async def test_returns_false_on_send_failure(self, mock_settings):
        """Test returns False when email sending fails."""
        mock_settings.resend_enabled = True
        mock_settings.send_emails = True
        mock_settings.resend_api_key = "test_api_key"
        mock_settings.frontend_url = "http://localhost:5173"
        mock_settings.email_from = "noreply@test.com"

        with patch("clutchchess.auth.email.get_settings", return_value=mock_settings):
            with patch(
                "clutchchess.auth.email._send_email_async",
                new_callable=AsyncMock,
                side_effect=Exception("API error"),
            ):
                result = await send_password_reset_email("user@test.com", "token")

        assert result is False

    @pytest.mark.asyncio
    async def test_does_not_raise_on_failure(self, mock_settings):
        """Test that email failure doesn't raise exception."""
        mock_settings.resend_enabled = True
        mock_settings.send_emails = True
        mock_settings.resend_api_key = "test_api_key"
        mock_settings.frontend_url = "http://localhost:5173"
        mock_settings.email_from = "noreply@test.com"

        with patch("clutchchess.auth.email.get_settings", return_value=mock_settings):
            with patch(
                "clutchchess.auth.email._send_email_async",
                new_callable=AsyncMock,
                side_effect=Exception("Network error"),
            ):
                # Should not raise
                result = await send_password_reset_email("user@test.com", "token")

        assert result is False


class TestEmailUrlGeneration:
    """Tests for email URL generation."""

    @pytest.mark.asyncio
    async def test_verification_url_includes_token(self, mock_settings):
        """Test verification URL includes the token as query param."""
        mock_settings.resend_enabled = True
        mock_settings.send_emails = True
        mock_settings.frontend_url = "https://clutchchess.com"
        mock_settings.resend_api_key = "key"
        mock_settings.email_from = "noreply@test.com"

        with patch("clutchchess.auth.email.get_settings", return_value=mock_settings):
            with patch("clutchchess.auth.email._send_email_async", new_callable=AsyncMock) as mock_send:
                await send_verification_email("user@test.com", "my_token")

        html = mock_send.call_args[0][0]["html"]
        assert "https://clutchchess.com/verify?token=my_token" in html

    @pytest.mark.asyncio
    async def test_reset_url_includes_token(self, mock_settings):
        """Test password reset URL includes the token as query param."""
        mock_settings.resend_enabled = True
        mock_settings.send_emails = True
        mock_settings.frontend_url = "https://clutchchess.com"
        mock_settings.resend_api_key = "key"
        mock_settings.email_from = "noreply@test.com"

        with patch("clutchchess.auth.email.get_settings", return_value=mock_settings):
            with patch("clutchchess.auth.email._send_email_async", new_callable=AsyncMock) as mock_send:
                await send_password_reset_email("user@test.com", "reset_token")

        html = mock_send.call_args[0][0]["html"]
        assert "https://clutchchess.com/reset-password?token=reset_token" in html
