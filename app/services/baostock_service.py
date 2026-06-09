"""BaoStock service for fetching stock data with caching."""

import logging
import re
import json
import os
from datetime import datetime, timedelta
from typing import Any, Optional

import baostock as bs
import pandas as pd

from app.config import Settings

logger = logging.getLogger(__name__)

# Cache settings
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cache')
CACHE_EXPIRY_HOURS = 24


def validate_stock_code(symbol: str) -> bool:
    """Validate stock code format: sh.600000 or sz.000001"""
    pattern = r'^(sh|sz)\.\d{6}$'
    return bool(re.match(pattern, symbol))


def get_cache_path(key: str) -> str:
    """Get cache file path for a given key."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe_key = re.sub(r'[^\w\-]', '_', key)
    return os.path.join(CACHE_DIR, f'{safe_key}.json')


def get_cached_data(key: str) -> Optional[Any]:
    """Get cached data if it exists and hasn't expired."""
    cache_path = get_cache_path(key)
    if not os.path.exists(cache_path):
        return None
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        cached_time = datetime.fromisoformat(cache_data.get('timestamp', ''))
        if datetime.now() - cached_time > timedelta(hours=CACHE_EXPIRY_HOURS):
            return None
        
        return cache_data.get('data')
    except Exception as e:
        logger.debug(f'Cache read error: {e}')
        return None


def set_cached_data(key: str, data: Any) -> None:
    """Save data to cache."""
    try:
        cache_path = get_cache_path(key)
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, default=str)
    except Exception as e:
        logger.debug(f'Cache write error: {e}')


def clean_date(date_str: str) -> str:
    """Clean date string, return empty string if invalid."""
    if not date_str or date_str in ('nan', 'None', '', '0'):
        return ''
    return date_str


class BaoStockService:
    """Service for interacting with BaoStock API with caching."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._logged_in = False

    def _ensure_login(self) -> bool:
        """Ensure we're logged in to BaoStock."""
        if not self._logged_in:
            try:
                lg = bs.login()
                if lg.error_code == "0":
                    self._logged_in = True
                    return True
                else:
                    logger.warning(f"BaoStock login failed: {lg.error_msg}")
                    return False
            except Exception as e:
                logger.warning(f"BaoStock login error: {e}")
                return False
        return True

    def logout(self) -> None:
        """Logout from BaoStock."""
        if self._logged_in:
            try:
                bs.logout()
            except Exception as e:
                logger.warning(f"BaoStock logout error: {e}")
            self._logged_in = False

    def get_stock_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a stock using K-line data."""
        if not validate_stock_code(symbol):
            return None
        
        if not self._ensure_login():
            return None
        
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
            
            rs = bs.query_history_k_data_plus(
                symbol,
                'date,close',
                start_date=start_date,
                end_date=end_date,
                frequency='d',
                adjustflag='2'
            )

            if rs.error_code != "0":
                return None

            latest_price = None
            while rs.next():
                data = rs.get_data()
                if isinstance(data, pd.DataFrame) and not data.empty:
                    latest_price = float(data['close'].iloc[-1])
            
            return latest_price
        except Exception as e:
            logger.debug(f"Error getting stock price for {symbol}: {e}")
            return None

    def get_stock_name(self, symbol: str) -> Optional[str]:
        """Get stock name."""
        if not validate_stock_code(symbol):
            return None
        
        if not self._ensure_login():
            return None
        
        try:
            rs = bs.query_stock_basic(code=symbol)
            if rs.error_code != "0":
                return None

            while rs.next():
                data = rs.get_data()
                if isinstance(data, pd.DataFrame) and not data.empty:
                    return str(data['code_name'].iloc[0])
            return None
        except Exception as e:
            logger.debug(f"Error getting stock name for {symbol}: {e}")
            return None

    def get_dividend_data(self, symbol: str, year: Optional[int] = None, use_cache: bool = True) -> list[dict[str, Any]]:
        """Get dividend data for a stock from BaoStock with caching.
        
        Returns merged dividend records with all dates consolidated.
        """
        if not validate_stock_code(symbol):
            return []
        
        if year is None:
            year = datetime.now().year
        
        # Check cache first
        cache_key = f'dividend_{symbol}_{year}'
        if use_cache:
            cached = get_cached_data(cache_key)
            if cached is not None:
                logger.debug(f'Using cached dividend data for {symbol} {year}')
                return cached
        
        if not self._ensure_login():
            return []

        try:
            rs = bs.query_dividend_data(code=symbol, year=year)
            if rs.error_code != "0":
                logger.debug(f"No dividend data for {symbol} in {year}: {rs.error_msg}")
                return []

            # Collect all raw records
            raw_records = []
            while rs.next():
                try:
                    data = rs.get_data()
                    if isinstance(data, pd.DataFrame):
                        for _, row in data.iterrows():
                            raw_records.append({
                                'code': str(row.get('code', '')),
                                'plan_date': clean_date(str(row.get('dividPlanDate', ''))),
                                'regist_date': clean_date(str(row.get('dividRegistDate', ''))),
                                'ex_date': clean_date(str(row.get('dividOperateDate', ''))),
                                'pay_date': clean_date(str(row.get('dividPayDate', ''))),
                                'amount': float(row.get('dividCashPsBeforeTax', 0)),
                                'cash_stock': str(row.get('dividCashStock', '')),
                            })
                except Exception as e:
                    logger.debug(f"Error parsing dividend row: {e}")
                    continue
            
            # Merge duplicate records by grouping dates
            # Each unique (amount, cash_stock) combination is one dividend
            dividend_groups = {}
            for record in raw_records:
                # Create a key based on amount and cash_stock to identify same dividend
                key = f"{record['amount']}_{record['cash_stock']}"
                if key not in dividend_groups:
                    dividend_groups[key] = {
                        'code': record['code'],
                        'amount': record['amount'],
                        'cash_stock': record['cash_stock'],
                        'dates': set()
                    }
                
                # Add all non-empty dates
                for date_key in ['plan_date', 'regist_date', 'ex_date', 'pay_date']:
                    if record[date_key]:
                        dividend_groups[key]['dates'].add(record[date_key])
            
            # Convert to final format
            dividends = []
            for key, group in dividend_groups.items():
                dates = sorted(group['dates'])
                dividends.append({
                    'code': group['code'],
                    'amount': group['amount'],
                    'cash_stock': group['cash_stock'],
                    'dates': dates,  # All dates for this dividend
                    'plan_date': dates[0] if dates else '',
                    'regist_date': group['dates'] - {dates[0]} if len(dates) > 1 else set(),
                    'ex_date': '',
                    'pay_date': '',
                })
            
            # Save to cache
            if dividends:
                set_cached_data(cache_key, dividends)
            
            return dividends
        except Exception as e:
            logger.debug(f"Error getting dividend data for {symbol}: {e}")
            return []

    def get_dividend_calendar(self, year: Optional[int] = None, max_stocks: int = 50) -> list[dict[str, Any]]:
        """Get dividend calendar with events for each date.
        
        Returns events with types:
        - 'record': 股权登记日 (blue)
        - 'ex_dividend': 除权除息日 (orange)
        - 'pay': 派息日 (green) - only if different from record/ex
        """
        if not self._ensure_login():
            return []
        
        if year is None:
            year = datetime.now().year

        try:
            from app.services.dividend_service import DividendService
            dividend_service = DividendService(self.settings, self)
            holdings = dividend_service.get_holdings()
            
            if not holdings:
                return []
            
            calendar = []
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            for fetch_year in [year, year + 1]:
                for holding in holdings[:max_stocks]:
                    try:
                        dividends = self.get_dividend_data(holding.symbol, fetch_year)
                        
                        for div in dividends:
                            if not div['dates']:
                                continue
                            
                            # Check if any date is in the future
                            has_future = False
                            for date_str in div['dates']:
                                try:
                                    date_dt = datetime.strptime(date_str, '%Y-%m-%d')
                                    if date_dt >= today:
                                        has_future = True
                                        break
                                except:
                                    continue
                            
                            if not has_future:
                                continue
                            
                            expected_amount = div['amount'] * holding.quantity
                            
                            # Find record date (regist) - should be before ex date
                            regist_date = ''
                            ex_date = ''
                            pay_date = ''
                            
                            for date_str in div['dates']:
                                try:
                                    date_dt = datetime.strptime(date_str, '%Y-%m-%d')
                                    if date_dt >= today:
                                        if not regist_date:
                                            regist_date = date_str
                                        elif not ex_date and date_str != regist_date:
                                            ex_date = date_str
                                        elif not pay_date and date_str != regist_date and date_str != ex_date:
                                            pay_date = date_str
                                except:
                                    continue
                            
                            # Add record date event (blue)
                            if regist_date:
                                calendar.append({
                                    'symbol': holding.symbol,
                                    'name': holding.name,
                                    'date': regist_date,
                                    'type': 'record',
                                    'ex_dividend_date': ex_date,
                                    'record_date': regist_date,
                                    'dividend_per_share': div['amount'],
                                    'quantity': holding.quantity,
                                    'expected_amount': round(expected_amount, 2),
                                    'cash_stock': div['cash_stock'],
                                    'status': 'expected',
                                })
                            
                            # Add ex-dividend date event (orange)
                            if ex_date:
                                calendar.append({
                                    'symbol': holding.symbol,
                                    'name': holding.name,
                                    'date': ex_date,
                                    'type': 'ex_dividend',
                                    'ex_dividend_date': ex_date,
                                    'record_date': regist_date,
                                    'dividend_per_share': div['amount'],
                                    'quantity': holding.quantity,
                                    'expected_amount': round(expected_amount, 2),
                                    'cash_stock': div['cash_stock'],
                                    'status': 'expected',
                                })
                            
                            # Add pay date event (green) only if different
                            if pay_date and pay_date != regist_date and pay_date != ex_date:
                                calendar.append({
                                    'symbol': holding.symbol,
                                    'name': holding.name,
                                    'date': pay_date,
                                    'type': 'pay',
                                    'ex_dividend_date': ex_date,
                                    'record_date': regist_date,
                                    'dividend_per_share': div['amount'],
                                    'quantity': holding.quantity,
                                    'expected_amount': round(expected_amount, 2),
                                    'cash_stock': div['cash_stock'],
                                    'status': 'expected',
                                })
                    except Exception as e:
                        logger.debug(f"Failed to get dividend data for {holding.symbol} {fetch_year}: {e}")
                        continue

            calendar.sort(key=lambda x: x['date'])
            return calendar
        except Exception as e:
            logger.debug(f"Error getting dividend calendar: {e}")
            return []
