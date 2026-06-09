"""Tests for email service."""

import pytest
from unittest.mock import patch, MagicMock


class TestEmailService:
    """Test email service."""

    def test_send_email_no_config(self):
        """Test sending email without SMTP config."""
        from app.services.email_service import EmailService
        from app.config import Settings

        settings = Settings()
        service = EmailService(settings)
        result = service.send_email("Test", "Test body")
        assert result is False

    def test_test_configuration_no_config(self):
        """Test configuration check with no SMTP config."""
        from app.services.email_service import EmailService
        from app.config import Settings

        settings = Settings()
        service = EmailService(settings)
        success, message = service.test_configuration()
        assert success is False
        assert "SMTP host not configured" in message

    @patch("smtplib.SMTP")
    def test_send_email_with_config(self, mock_smtp):
        """Test sending email with valid config."""
        from app.services.email_service import EmailService
        from app.config import Settings

        settings = Settings(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="password",
            smtp_from="test@test.com",
            smtp_to="recipient@test.com",
            smtp_use_tls=True,
        )
        service = EmailService(settings)

        # Mock SMTP
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_smtp_instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        result = service.send_email("Test Subject", "Test Body")
        assert result is True
        mock_smtp_instance.send_message.assert_called_once()

    def test_dividend_notification(self):
        """Test dividend notification email."""
        from app.services.email_service import EmailService
        from app.config import Settings

        settings = Settings(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_from="test@test.com",
            smtp_to="recipient@test.com",
            smtp_use_tls=True,
        )
        service = EmailService(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp_instance = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_smtp_instance)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            result = service.send_dividend_notification(
                symbol="sh.600000",
                dividend_date="2026-06-15",
                amount=500.0,
            )
            assert result is True
