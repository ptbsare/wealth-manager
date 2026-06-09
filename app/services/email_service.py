"""Email service for Wealth Manager."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from app.config import Settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def send_email(self, subject: str, body: str, html_body: str | None = None) -> bool:
        """Send an email notification."""
        if not self.settings.smtp_host or not self.settings.smtp_from:
            logger.warning("SMTP not configured, skipping email")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.settings.smtp_from
            msg["To"] = self.settings.smtp_to or self.settings.smtp_from

            msg.attach(MIMEText(body, "plain", "utf-8"))
            if html_body:
                msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                if self.settings.smtp_use_tls:
                    server.starttls()
                if self.settings.smtp_user and self.settings.smtp_password:
                    server.login(self.settings.smtp_user, self.settings.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_dividend_notification(self, symbol: str, dividend_date: str, amount: float) -> bool:
        """Send a dividend notification email."""
        subject = f"💰 分红提醒: {symbol} 预计分红 {amount:.2f} 元"
        body = f"""
股票: {symbol}
分红日期: {dividend_date}
预计到账金额: {amount:.2f} 元

请注意查收！
        """.strip()
        html_body = f"""
<html>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: #4CAF50; color: white; padding: 20px; text-align: center;">
        <h1>💰 分红提醒</h1>
    </div>
    <div style="padding: 20px; background: #f9f9f9;">
        <p><strong>股票:</strong> {symbol}</p>
        <p><strong>分红日期:</strong> {dividend_date}</p>
        <p><strong>预计到账金额:</strong> ¥{amount:.2f}</p>
    </div>
    <div style="padding: 10px; text-align: center; color: #666; font-size: 12px;">
        <p>请注意查收！</p>
    </div>
</body>
</html>
        """.strip()
        return self.send_email(subject, body, html_body)

    def test_configuration(self) -> tuple[bool, str]:
        """Test email configuration."""
        if not self.settings.smtp_host:
            return False, "SMTP host not configured"
        if not self.settings.smtp_from:
            return False, "SMTP from address not configured"

        try:
            msg = MIMEMultipart()
            msg["Subject"] = "Wealth Manager - Email Test"
            msg["From"] = self.settings.smtp_from
            msg["To"] = self.settings.smtp_to or self.settings.smtp_from
            msg.attach(MIMEText("This is a test email from Wealth Manager.", "plain"))

            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                if self.settings.smtp_use_tls:
                    server.starttls()
                if self.settings.smtp_user and self.settings.smtp_password:
                    server.login(self.settings.smtp_user, self.settings.smtp_password)
                server.send_message(msg)

            return True, "Email sent successfully"
        except Exception as e:
            return False, f"Failed to send test email: {e}"
