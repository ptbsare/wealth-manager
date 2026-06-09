"""Dividend service for Wealth Manager with caching."""

import logging
import json
import os
from datetime import datetime
from typing import Any, Optional

from app.config import Settings
from app.database import get_connection, dict_from_row
from app.models.dividend import Dividend, DividendCalendarEntry
from app.models.holding import Holding
from app.services.baostock_service import BaoStockService, get_cached_data, set_cached_data

logger = logging.getLogger(__name__)

# Cache for portfolio stats
STATS_CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cache', 'portfolio_stats.json')
STATS_CACHE_EXPIRY = 5 * 60  # 5 minutes in seconds


def load_stats_cache():
    """Load cached portfolio stats if valid."""
    try:
        if not os.path.exists(STATS_CACHE_FILE):
            return None
        
        with open(STATS_CACHE_FILE, 'r') as f:
            cache = json.load(f)
        
        cached_time = cache.get('timestamp', 0)
        if datetime.now().timestamp() - cached_time > STATS_CACHE_EXPIRY:
            return None
        
        return cache.get('data')
    except Exception as e:
        logger.debug(f"Stats cache load error: {e}")
        return None


def save_stats_cache(data):
    """Save portfolio stats to cache."""
    try:
        os.makedirs(os.path.dirname(STATS_CACHE_FILE), exist_ok=True)
        cache = {
            'timestamp': datetime.now().timestamp(),
            'data': data
        }
        with open(STATS_CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception as e:
        logger.debug(f"Stats cache save error: {e}")


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

        # Invalidate stats cache
        save_stats_cache(None)
        
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

        # Invalidate stats cache
        save_stats_cache(None)
        
        return self.get_holding(holding_id)

    def delete_holding(self, holding_id: int) -> bool:
        """Delete a holding."""
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM holdings WHERE id = ?", (holding_id,)
            )
            conn.commit()
            
            # Invalidate stats cache
            save_stats_cache(None)
            
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
        """Get dividend calendar with caching."""
        return self.bao.get_dividend_calendar(year)

    def get_portfolio_stats(self, received_years: int = 3, expected_years: int = 1) -> dict[str, Any]:
        """Get portfolio statistics with configurable time ranges and caching."""
        
        # Check cache first
        cached = load_stats_cache()
        if cached and cached.get('received_years') == received_years and cached.get('expected_years') == expected_years:
            logger.debug("Using cached portfolio stats")
            return cached
        
        holdings = self.get_holdings()
        
        # Update prices in background - don't block
        try:
            self.update_prices()
        except Exception as e:
            logger.debug(f"Price update failed: {e}")

        total_cost = sum(h.cost_value for h in holdings)
        total_market_value = sum(h.market_value for h in holdings)

        # Batch load all dividend data
        all_dividends = {}
        current_year = datetime.now().year
        
        for holding in holdings:
            for year in range(current_year - received_years, current_year + expected_years + 1):
                try:
                    dividends = self.bao.get_dividend_data(holding.symbol, year, use_cache=True)
                    if dividends:
                        all_dividends[(holding.symbol, year)] = dividends
                except Exception as e:
                    logger.debug(f"Failed to get dividends: {e}")

        # Calculate received dividends
        total_dividends_received = 0.0
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for holding in holdings:
            for year in range(current_year - received_years, current_year + 1):
                dividends = all_dividends.get((holding.symbol, year), [])
                for div in dividends:
                    for date_str in div.get('dates', []):
                        try:
                            date_dt = datetime.strptime(date_str, '%Y-%m-%d')
                            if date_dt < today:
                                total_dividends_received += div['amount'] * holding.quantity
                                break
                        except:
                            continue

        # Calculate expected dividends
        total_dividends_expected = 0.0
        
        for holding in holdings:
            for year in range(current_year, current_year + expected_years + 1):
                dividends = all_dividends.get((holding.symbol, year), [])
                for div in dividends:
                    for date_str in div.get('dates', []):
                        try:
                            date_dt = datetime.strptime(date_str, '%Y-%m-%d')
                            if date_dt >= today:
                                total_dividends_expected += div['amount'] * holding.quantity
                                break
                        except:
                            continue

        payback_progress = (total_dividends_received / total_cost * 100) if total_cost > 0 else 0
        dividend_yield = (total_dividends_received / total_cost * 100) if total_cost > 0 else 0

        result = {
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
        
        # Save to cache
        save_stats_cache(result)
        
        return result
