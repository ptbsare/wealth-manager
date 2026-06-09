"""Database setup and management for Wealth Manager."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import DB_PATH

CREATE_TABLE_SQL = """
-- Holdings table
CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL DEFAULT '',
    quantity REAL NOT NULL DEFAULT 0,
    cost_price REAL NOT NULL DEFAULT 0,
    current_price REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Dividends table
CREATE TABLE IF NOT EXISTS dividends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    dividend_date TEXT NOT NULL,
    dividend_per_share REAL NOT NULL DEFAULT 0,
    tax_rate REAL NOT NULL DEFAULT 0,
    actual_received REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'expected',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

-- Dividend calendar cache
CREATE TABLE IF NOT EXISTS dividend_calendar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    plan_date TEXT NOT NULL,
    ex_dividend_date TEXT NOT NULL DEFAULT '',
    record_date TEXT NOT NULL DEFAULT '',
    dividend_per_share REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'announced',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Notification rules table
CREATE TABLE IF NOT EXISTS notification_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    symbol TEXT NOT NULL DEFAULT '',
    condition TEXT NOT NULL DEFAULT '',
    threshold REAL NOT NULL DEFAULT 0,
    email_subject TEXT NOT NULL DEFAULT '股票价格提醒',
    email_template TEXT NOT NULL DEFAULT '',
    recipients TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_dividends_symbol ON dividends(symbol);
CREATE INDEX IF NOT EXISTS idx_dividends_date ON dividends(dividend_date);
CREATE INDEX IF NOT EXISTS idx_dividend_calendar_symbol ON dividend_calendar(symbol);
CREATE INDEX IF NOT EXISTS idx_dividend_calendar_date ON dividend_calendar(plan_date);
CREATE INDEX IF NOT EXISTS idx_notification_rules_active ON notification_rules(active);
"""


# Global variable to allow test override
_db_path_override = None


def get_db_path() -> Path:
    """Get the current database path."""
    global _db_path_override
    if _db_path_override:
        return _db_path_override
    return DB_PATH


def set_db_path(path: Path | str) -> None:
    """Set the database path (for testing)."""
    global _db_path_override
    _db_path_override = Path(path)


def clear_db_path_override() -> None:
    """Clear the database path override."""
    global _db_path_override
    _db_path_override = None


def init_db(db_path: Path | str = None) -> None:
    """Initialize the database."""
    if db_path is None:
        db_path = get_db_path()
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_connection(db_path) as conn:
        conn.executescript(CREATE_TABLE_SQL)
        conn.commit()


@contextmanager
def get_connection(db_path: Path | str = None):
    """Get a database connection."""
    if db_path is None:
        db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def dict_from_row(row: sqlite3.Row | None) -> dict | None:
    """Convert a sqlite3.Row to a dict."""
    if row is None:
        return None
    return dict(row)
