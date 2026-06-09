"""Dividend model for Wealth Manager."""

from datetime import datetime
from typing import Any


class Dividend:
    """Represents a dividend record."""

    def __init__(
        self,
        id: int | None = None,
        symbol: str = "",
        dividend_date: str = "",
        dividend_per_share: float = 0.0,
        tax_rate: float = 0.0,
        actual_received: float = 0.0,
        status: str = "expected",
        notes: str = "",
        created_at: str | None = None,
    ):
        self.id = id
        self.symbol = symbol
        self.dividend_date = dividend_date
        self.dividend_per_share = dividend_per_share
        self.tax_rate = tax_rate
        self.actual_received = actual_received
        self.status = status
        self.notes = notes
        self.created_at = created_at or datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "dividend_date": self.dividend_date,
            "dividend_per_share": self.dividend_per_share,
            "tax_rate": self.tax_rate,
            "actual_received": self.actual_received,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @classmethod
    def from_row(cls, row: dict) -> "Dividend":
        """Create from database row."""
        return cls(
            id=row.get("id"),
            symbol=row.get("symbol", ""),
            dividend_date=row.get("dividend_date", ""),
            dividend_per_share=row.get("dividend_per_share", 0.0),
            tax_rate=row.get("tax_rate", 0.0),
            actual_received=row.get("actual_received", 0.0),
            status=row.get("status", "expected"),
            notes=row.get("notes", ""),
            created_at=row.get("created_at"),
        )


class DividendCalendarEntry:
    """Represents a dividend calendar entry from BaoStock."""

    def __init__(
        self,
        symbol: str = "",
        plan_date: str = "",
        ex_dividend_date: str = "",
        record_date: str = "",
        dividend_per_share: float = 0.0,
        status: str = "announced",
    ):
        self.symbol = symbol
        self.plan_date = plan_date
        self.ex_dividend_date = ex_dividend_date
        self.record_date = record_date
        self.dividend_per_share = dividend_per_share
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "plan_date": self.plan_date,
            "ex_dividend_date": self.ex_dividend_date,
            "record_date": self.record_date,
            "dividend_per_share": self.dividend_per_share,
            "status": self.status,
        }
