"""Test configuration and fixtures for Wealth Manager."""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Set test database
os.environ.setdefault("TESTING", "true")

from app.main import app
from app.database import init_db, get_connection, set_db_path, clear_db_path_override
from app.config import Settings


@pytest.fixture
def tmp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_wealth.db"


@pytest.fixture
def client(tmp_db_path):
    """Create a test client with a temporary database."""
    # Set the database path for this test
    set_db_path(tmp_db_path)

    # Initialize database
    init_db(tmp_db_path)

    # Clear any cached settings
    from app.config import get_settings_cached
    get_settings_cached.cache_clear()
    
    # Set polling interval to very long to avoid polling during tests
    import sqlite3
    conn = sqlite3.connect(str(tmp_db_path))
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                 ("polling_interval", "999999"))
    conn.commit()
    conn.close()

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    clear_db_path_override()


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for MCP endpoints."""
    response = client.get("/api/settings")
    token = response.json()["mcp_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_holding_data():
    """Sample holding data for testing."""
    return {
        "symbol": "sh.600000",
        "name": "浦发银行",
        "quantity": 1000,
        "cost_price": 10.50,
    }


@pytest.fixture
def sample_dividend_data():
    """Sample dividend data for testing."""
    return {
        "symbol": "sh.600000",
        "dividend_date": "2026-06-15",
        "dividend_per_share": 0.50,
        "tax_rate": 0,
        "actual_received": 500.0,
        "status": "expected",
        "notes": "2025年度分红",
    }
