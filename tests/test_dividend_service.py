"""Tests for dividend service."""

import pytest


class TestDividendService:
    """Test dividend service operations."""

    def test_get_holdings_empty(self, client):
        """Test getting holdings when empty."""
        from app.services.dividend_service import DividendService
        from app.services.baostock_service import BaoStockService
        from app.config import Settings

        settings = Settings()
        bao = BaoStockService(settings)
        service = DividendService(settings, bao)

        holdings = service.get_holdings()
        assert holdings == []

    def test_get_dividends_empty(self, client):
        """Test getting dividends when empty."""
        from app.services.dividend_service import DividendService
        from app.services.baostock_service import BaoStockService
        from app.config import Settings

        settings = Settings()
        bao = BaoStockService(settings)
        service = DividendService(settings, bao)

        dividends = service.get_dividends()
        assert dividends == []

    def test_add_holding(self, client):
        """Test adding a holding via service."""
        from app.services.dividend_service import DividendService
        from app.services.baostock_service import BaoStockService
        from app.config import Settings

        settings = Settings()
        bao = BaoStockService(settings)
        service = DividendService(settings, bao)

        holding = service.add_holding(
            symbol="sh.600000",
            name="浦发银行",
            quantity=1000,
            cost_price=10.50,
        )

        assert holding.symbol == "sh.600000"
        assert holding.quantity == 1000
        assert holding.cost_price == 10.50

    def test_add_dividend(self, client):
        """Test adding a dividend via service."""
        from app.services.dividend_service import DividendService
        from app.services.baostock_service import BaoStockService
        from app.config import Settings
        from app.models.dividend import Dividend

        settings = Settings()
        bao = BaoStockService(settings)
        service = DividendService(settings, bao)

        dividend = Dividend(
            symbol="sh.600000",
            dividend_date="2026-06-15",
            dividend_per_share=0.50,
            actual_received=500.0,
            status="expected",
        )

        created = service.add_dividend(dividend)
        assert created.symbol == "sh.600000"
        assert created.dividend_per_share == 0.50

    def test_get_holding_by_symbol(self, client):
        """Test getting holding by symbol."""
        from app.services.dividend_service import DividendService
        from app.services.baostock_service import BaoStockService
        from app.config import Settings

        settings = Settings()
        bao = BaoStockService(settings)
        service = DividendService(settings, bao)

        # Add holding
        service.add_holding(
            symbol="sh.600000",
            name="浦发银行",
            quantity=1000,
            cost_price=10.50,
        )

        # Get by symbol
        holding = service.get_holding_by_symbol("sh.600000")
        assert holding is not None
        assert holding.symbol == "sh.600000"

    def test_update_holding(self, client):
        """Test updating a holding via service."""
        from app.services.dividend_service import DividendService
        from app.services.baostock_service import BaoStockService
        from app.config import Settings

        settings = Settings()
        bao = BaoStockService(settings)
        service = DividendService(settings, bao)

        # Add holding
        holding = service.add_holding(
            symbol="sh.600000",
            name="浦发银行",
            quantity=1000,
            cost_price=10.50,
        )

        # Update holding
        updated = service.update_holding(holding.id, quantity=2000)
        assert updated.quantity == 2000

    def test_delete_holding(self, client):
        """Test deleting a holding via service."""
        from app.services.dividend_service import DividendService
        from app.services.baostock_service import BaoStockService
        from app.config import Settings

        settings = Settings()
        bao = BaoStockService(settings)
        service = DividendService(settings, bao)

        # Add holding
        holding = service.add_holding(
            symbol="sh.600000",
            name="浦发银行",
            quantity=1000,
            cost_price=10.50,
        )

        # Delete holding
        success = service.delete_holding(holding.id)
        assert success is True

        # Verify deletion
        deleted = service.get_holding(holding.id)
        assert deleted is None
