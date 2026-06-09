"""Polling service for stock prices and notification checking."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from app.config import get_settings
from app.database import get_connection
from app.services.baostock_service import BaoStockService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class PollingService:
    """Service for polling stock prices and checking notification conditions."""
    
    def __init__(self):
        self.running = False
        self.task = None
        self.settings = get_settings()
        self.bao_service = BaoStockService(self.settings)
        self.email_service = EmailService(self.settings)
        self.price_history = {}  # {symbol: [{date, price}]}
        self.last_prices = {}  # {symbol: last_price}
    
    async def start(self):
        """Start the polling service."""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._polling_loop())
        logger.info("Polling service started")
    
    async def stop(self):
        """Stop the polling service."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Polling service stopped")
    
    async def _polling_loop(self):
        """Main polling loop."""
        while self.running:
            try:
                # Get polling interval from settings
                interval = self._get_polling_interval()
                
                # Update stock prices
                await self._update_prices()
                
                # Check notification conditions
                await self._check_notifications()
                
                # Wait for next poll
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    def _get_polling_interval(self) -> int:
        """Get polling interval from settings in seconds."""
        try:
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT value FROM settings WHERE key = 'polling_interval'"
                ).fetchone()
                if row and row["value"]:
                    return int(row["value"])
        except Exception:
            pass
        return 300  # Default: 5 minutes
    
    async def _update_prices(self):
        """Update stock prices for all holdings."""
        try:
            from app.services.dividend_service import DividendService
            dividend_service = DividendService(self.settings, self.bao_service)
            holdings = dividend_service.get_holdings()
            
            today = datetime.now().strftime("%Y-%m-%d")
            
            for holding in holdings:
                symbol = holding.symbol
                try:
                    # Get current price
                    current_price = self.bao_service.get_stock_current_price(symbol)
                    
                    if current_price:
                        # Store price history
                        if symbol not in self.price_history:
                            self.price_history[symbol] = []
                        
                        # Add today's price if not already added
                        today_prices = [p for p in self.price_history[symbol] if p["date"] == today]
                        if not today_prices:
                            self.price_history[symbol].append({
                                "date": today,
                                "price": current_price
                            })
                        
                        # Keep only last 30 days of history
                        cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                        self.price_history[symbol] = [
                            p for p in self.price_history[symbol] if p["date"] >= cutoff_date
                        ]
                        
                        # Update holding price
                        dividend_service.update_holding(holding.id, current_price=current_price)
                        
                        # Store last price
                        self.last_prices[symbol] = current_price
                        
                except Exception as e:
                    logger.warning(f"Failed to update price for {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to update prices: {e}")
    
    async def _check_notifications(self):
        """Check notification conditions and send alerts."""
        try:
            with get_connection() as conn:
                # Get active notification rules
                rows = conn.execute(
                    """SELECT * FROM notification_rules 
                       WHERE active = 1"""
                ).fetchall()
                
                for row in rows:
                    rule = dict(row)
                    try:
                        await self._evaluate_rule(rule)
                    except Exception as e:
                        logger.error(f"Failed to evaluate rule {rule.get('name')}: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to check notifications: {e}")
    
    async def _evaluate_rule(self, rule: dict):
        """Evaluate a single notification rule."""
        rule_type = rule.get("rule_type")
        condition = rule.get("condition")
        threshold = float(rule.get("threshold", 0))
        symbol = rule.get("symbol", "")
        
        if rule_type == "price_drop_percent":
            # Check if stock dropped by X% in a day
            await self._check_price_drop_percent(symbol, threshold, rule)
            
        elif rule_type == "price_below":
            # Check if stock price is below X
            await self._check_price_below(symbol, threshold, rule)
            
        elif rule_type == "portfolio_drop_percent":
            # Check if portfolio value dropped by X%
            await self._check_portfolio_drop(threshold, rule)
    
    async def _check_price_drop_percent(self, symbol: str, threshold: float, rule: dict):
        """Check if stock dropped by threshold percent in a day."""
        if not symbol or symbol not in self.price_history:
            return
        
        prices = self.price_history[symbol]
        if len(prices) < 2:
            return
        
        # Get today's and yesterday's prices
        today = prices[-1]
        yesterday = prices[-2] if len(prices) >= 2 else None
        
        if not yesterday:
            return
        
        yesterday_price = yesterday["price"]
        today_price = today["price"]
        
        if yesterday_price <= 0:
            return
        
        change_percent = ((today_price - yesterday_price) / yesterday_price) * 100
        
        if change_percent <= -threshold:
            # Condition met, send notification
            await self._send_notification(rule, {
                "symbol": symbol,
                "change_percent": abs(change_percent),
                "current_price": today_price,
                "previous_price": yesterday_price
            })
    
    async def _check_price_below(self, symbol: str, threshold: float, rule: dict):
        """Check if stock price is below threshold."""
        if not symbol or symbol not in self.last_prices:
            return
        
        current_price = self.last_prices[symbol]
        
        if current_price <= threshold:
            # Condition met, send notification
            await self._send_notification(rule, {
                "symbol": symbol,
                "current_price": current_price,
                "threshold": threshold
            })
    
    async def _check_portfolio_drop(self, threshold: float, rule: dict):
        """Check if portfolio value dropped by threshold percent."""
        try:
            from app.services.dividend_service import DividendService
            dividend_service = DividendService(self.settings, self.bao_service)
            
            # Get current portfolio value
            stats = dividend_service.get_portfolio_stats()
            current_value = stats["total_market_value"]
            
            # Get previous portfolio value from settings
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT value FROM settings WHERE key = 'last_portfolio_value'"
                ).fetchone()
                
                if row and row["value"]:
                    previous_value = float(row["value"])
                else:
                    previous_value = current_value
                
                # Update last portfolio value
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    ("last_portfolio_value", str(current_value))
                )
                conn.commit()
            
            if previous_value <= 0:
                return
            
            change_percent = ((current_value - previous_value) / previous_value) * 100
            
            if change_percent <= -threshold:
                # Condition met, send notification
                await self._send_notification(rule, {
                    "change_percent": abs(change_percent),
                    "current_value": current_value,
                    "previous_value": previous_value
                })
                
        except Exception as e:
            logger.error(f"Failed to check portfolio drop: {e}")
    
    async def _send_notification(self, rule: dict, data: dict):
        """Send notification email."""
        # Check if we recently sent this notification (avoid spam)
        cache_key = f"notification_sent_{rule['id']}"
        with get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (cache_key,)
            ).fetchone()
            
            if row and row["value"]:
                last_sent = datetime.fromisoformat(row["value"])
                # Don't send more than once per hour
                if datetime.now() - last_sent < timedelta(hours=1):
                    return
        
        # Prepare email content
        template = rule.get("email_template", "")
        subject = rule.get("email_subject", "股票价格提醒")
        
        # Replace variables in template
        content = template
        for key, value in data.items():
            content = content.replace(f"{{{key}}}", str(value))
        
        # Send email
        recipients = rule.get("recipients", "").split(",")
        recipients = [r.strip() for r in recipients if r.strip()]
        
        if recipients:
            for recipient in recipients:
                self.email_service.send_email(
                    subject=subject,
                    body=content,
                    html_body=f"<pre>{content}</pre>"
                )
            
            # Update last sent time
            with get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (cache_key, datetime.now().isoformat())
                )
                conn.commit()
            
            logger.info(f"Notification sent for rule: {rule.get('name')}")
    
    def get_status(self) -> dict:
        """Get polling service status."""
        return {
            "running": self.running,
            "last_prices": self.last_prices,
            "price_history_days": {
                symbol: len(prices) 
                for symbol, prices in self.price_history.items()
            }
        }


# Global polling service instance
polling_service = PollingService()
