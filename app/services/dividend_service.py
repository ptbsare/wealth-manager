"""Dividend service for Wealth Manager."""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from app.config import Settings
from app.database import get_connection, dict_from_row
from app.models.dividend import Dividend, DividendCalendarEntry
from app.models.holding import Holding
from app.services.baostock_service import BaoStockService

logger = logging.getLogger(__name__)


class DividendService:
    """Service for dividend-related operations."""

    def __init__(self, settings: Settings, bao_service: BaoStockService):
        self.settings = settings
        self.bao = bao_service

    def get_holdings(self) -> list[Holding]:
        """Get all holdings from database."""
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM holdings ORDER BY symbol").fetchall()
            return [Holding.from_row(dict(row)) for row in rows]

    def get_holding(self, holding_id: int) -> Optional[Holding]:
        """Get a single holding by ID."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM holdings WHERE id = ?", (holding_id,)
            ).fetchone()
            return Holding.from_row(dict(row)) if row else None

    def get_holding_by_symbol(self, symbol: str) -> Optional[Holding]:
        """Get a holding by symbol."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM holdings WHERE symbol = ?", (symbol,)
            ).fetchone()
            return Holding.from_row(dict(row)) if row else None

    def add_holding(self, symbol: str, name: str, quantity: float, cost_price: float) -> Holding:
        """Add a new holding or merge with existing one."""
        existing = self.get_holding_by_symbol(symbol)
        if existing:
            new_quantity = existing.quantity + quantity
            total_cost = (existing.quantity * existing.cost_price) + (quantity * cost_price)
            new_cost_price = total_cost / new_quantity
            
            return self.update_holding(
                existing.id,
                quantity=new_quantity,
                cost_price=round(new_cost_price, 2)
            )

        current_price = self.bao.get_stock_current_price(symbol) or 0.0
        if not name:
            name = self.bao.get_stock_name(symbol) or symbol

        with get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO holdings (symbol, name, quantity, cost_price, current_price)
                   VALUES (?, ?, ?, ?, ?)""",
                (symbol, name, quantity, cost_price, current_price)
            )
            conn.commit()
            holding_id = cursor.lastrowid

        return self.get_holding(holding_id)

    def update_holding(self, holding_id: int, **kwargs) -> Optional[Holding]:
        """Update a holding."""
        if not kwargs:
            return self.get_holding(holding_id)

        set_clauses = []
        values = []
        for key, value in kwargs.items():
            if key in ("symbol", "name", "quantity", "cost_price", "current_price"):
                set_clauses.append(f"{key} = ?")
                values.append(value)

        if not set_clauses:
            return self.get_holding(holding_id)

        set_clauses.append("updated_at = datetime('now')")
        values.append(holding_id)

        with get_connection() as conn:
            conn.execute(
                f"UPDATE holdings SET {', '.join(set_clauses)} WHERE id = ?",
                values
            )
            conn.commit()

        return self.get_holding(holding_id)

    def delete_holding(self, holding_id: int) -> bool:
        """Delete a holding."""
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM holdings WHERE id = ?", (holding_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_prices(self) -> None:
        """Update current prices for all holdings from BaoStock."""
        holdings = self.get_holdings()
        for holding in holdings:
            try:
                price = self.bao.get_stock_current_price(holding.symbol)
                if price:
                    self.update_holding(holding.id, current_price=price)
            except Exception as e:
                logger.debug(f"Failed to update price for {holding.symbol}: {e}")

    def get_dividend_calendar(self, year: Optional[int] = None) -> list[dict[str, Any]]:
        """Get dividend calendar with expected amounts from BaoStock."""
        return self.bao.get_dividend_calendar(year)

    def get_portfolio_stats(self, received_years: int = 3, expected_years: int = 1) -> dict[str, Any]:
        """Get portfolio statistics with configurable time ranges.
        
        Args:
            received_years: Number of years to look back for received dividends (default 3)
            expected_years: Number of years to look forward for expected dividends (default 1)
        """
        holdings = self.get_holdings()
        self.update_prices()

        total_cost = 0.0
        total_market_value = 0.0

        for holding in holdings:
            total_cost += holding.cost_value
            total_market_value += holding.market_value

        # Calculate received dividends (past N years)
        received_start = datetime.now().year - received_years
        total_dividends_received = 0.0
        
        for holding in holdings:
            try:
                for year in range(received_start, datetime.now().year + 1):
                    dividends = self.bao.get_dividend_data(holding.symbol, year, use_cache=True)
                    for div in dividends:
                        for date_str in div.get('dates', []):
                            try:
                                date_dt = datetime.strptime(date_str, '%Y-%m-%d')
                                if date_dt < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                                    total_dividends_received += div['amount'] * holding.quantity
                                    break
                            except:
                                continue
            except Exception as e:
                logger.debug(f"Failed to get received dividends for {holding.symbol}: {e}")

        # Calculate expected dividends (next N years)
        total_dividends_expected = 0.0
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for holding in holdings:
            try:
                for year in range(datetime.now().year, datetime.now().year + expected_years + 1):
                    dividends = self.bao.get_dividend_data(holding.symbol, year, use_cache=True)
                    for div in dividends:
                        for date_str in div.get('dates', []):
                            try:
                                date_dt = datetime.strptime(date_str, '%Y-%m-%d')
                                if date_dt >= today:
                                    total_dividends_expected += div['amount'] * holding.quantity
                                    break
                            except:
                                continue
            except Exception as e:
                logger.debug(f"Failed to get expected dividends for {holding.symbol}: {e}")

        payback_progress = (total_dividends_received / total_cost * 100) if total_cost > 0 else 0
        dividend_yield = (total_dividends_received / total_cost * 100) if total_cost > 0 else 0

        return {
            "total_holdings": len(holdings),
            "total_cost": round(total_cost, 2),
            "total_market_value": round(total_market_value, 2),
            "total_profit": round(total_market_value - total_cost, 2),
            "profit_rate": round((total_market_value - total_cost) / total_cost * 100, 2) if total_cost > 0 else 0,
            "total_dividends_received": round(total_dividends_received, 2),
            "total_dividends_expected": round(total_dividends_expected, 2),
            "payback_progress": round(payback_progress, 2),
            "dividend_yield": round(dividend_yield, 2),
            "received_years": received_years,
            "expected_years": expected_years,
        }
