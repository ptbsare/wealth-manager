"""Configuration management for Wealth Manager."""

import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "wealth.db"


class Settings(BaseSettings):
    """Application settings."""

    # App settings
    app_name: str = "Wealth Manager"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # MCP API settings
    mcp_token: str = ""

    # SMTP settings
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_to: str = ""
    smtp_use_tls: bool = True

    # BaoStock settings
    baostock_username: str = ""
    baostock_password: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    """Get application settings, loading MCP token from database if needed."""
    settings = Settings()

    # Try to load MCP token from database
    try:
        from app.database import get_connection
        with get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = 'mcp_token'"
            ).fetchone()
            if row and row["value"]:
                settings.mcp_token = row["value"]
    except Exception:
        pass

    # If still no token, generate one
    if not settings.mcp_token:
        settings.mcp_token = secrets.token_urlsafe(32)
        # Save to database
        try:
            from app.database import get_connection
            with get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    ("mcp_token", settings.mcp_token),
                )
                conn.commit()
        except Exception:
            pass

    return settings


@lru_cache
def get_settings_cached() -> Settings:
    """Get cached application settings."""
    return get_settings()
