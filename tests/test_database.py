"""Tests for database module."""

import pytest
import sqlite3
from pathlib import Path


class TestDatabase:
    """Test database operations."""

    def test_init_db(self, tmp_path):
        """Test database initialization."""
        from app.database import init_db

        db_path = tmp_path / "test.db"
        init_db(db_path)

        assert db_path.exists()

        # Verify tables were created
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "holdings" in tables
        assert "dividends" in tables
        assert "settings" in tables
        assert "dividend_calendar" in tables

    def test_get_connection(self, tmp_path):
        """Test getting a database connection."""
        from app.database import init_db, get_connection

        db_path = tmp_path / "test.db"
        init_db(db_path)

        with get_connection(db_path) as conn:
            assert conn is not None
            # Test connection is working
            result = conn.execute("SELECT 1").fetchone()
            assert result[0] == 1

    def test_dict_from_row(self):
        """Test dict_from_row conversion."""
        from app.database import dict_from_row

        # Create a mock row
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT 1 as id, 'test' as name")
        row = cursor.fetchone()
        conn.close()

        result = dict_from_row(row)
        assert result == {"id": 1, "name": "test"}

    def test_dict_from_row_none(self):
        """Test dict_from_row with None."""
        from app.database import dict_from_row

        result = dict_from_row(None)
        assert result is None
