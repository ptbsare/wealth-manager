"""Tests for dividends API endpoints."""

import pytest


class TestDividendsCRUD:
    """Test dividends CRUD operations."""

    def test_list_dividends_empty(self, client):
        """Test listing dividends when empty."""
        response = client.get("/api/dividends")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_dividend(self, client, sample_dividend_data):
        """Test creating a new dividend record."""
        response = client.post("/api/dividends", json=sample_dividend_data)
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == sample_dividend_data["symbol"]
        assert data["dividend_per_share"] == sample_dividend_data["dividend_per_share"]
        assert "id" in data

    def test_list_dividends_with_data(self, client, sample_dividend_data):
        """Test listing dividends with data."""
        client.post("/api/dividends", json=sample_dividend_data)
        response = client.get("/api/dividends")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_list_dividends_by_symbol(self, client, sample_dividend_data):
        """Test listing dividends filtered by symbol."""
        client.post("/api/dividends", json=sample_dividend_data)
        response = client.get(f"/api/dividends?symbol={sample_dividend_data['symbol']}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == sample_dividend_data["symbol"]

    def test_dividend_calendar_empty(self, client):
        """Test dividend calendar when empty."""
        response = client.get("/api/dividends/calendar")
        assert response.status_code == 200
        assert response.json() == []

    def test_portfolio_stats_empty(self, client):
        """Test portfolio stats when no data."""
        response = client.get("/api/dividends/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_holdings"] == 0
        assert data["total_cost"] == 0
        assert data["total_market_value"] == 0

    def test_portfolio_stats_with_data(self, client, sample_holding_data, sample_dividend_data):
        """Test portfolio stats with holdings and dividends."""
        # Create holding
        holding_resp = client.post("/api/holdings", json=sample_holding_data)
        assert holding_resp.status_code == 201

        # Create dividend
        dividend_resp = client.post("/api/dividends", json=sample_dividend_data)
        assert dividend_resp.status_code == 200

        response = client.get("/api/dividends/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_holdings"] == 1
        assert data["total_cost"] > 0


class TestDividendModel:
    """Test Dividend model."""

    def test_dividend_to_dict(self):
        """Test dividend serialization."""
        from app.models.dividend import Dividend

        dividend = Dividend(
            id=1,
            symbol="sh.600000",
            dividend_date="2026-06-15",
            dividend_per_share=0.50,
            tax_rate=0,
            actual_received=500.0,
            status="expected",
        )

        data = dividend.to_dict()
        assert data["id"] == 1
        assert data["symbol"] == "sh.600000"
        assert data["dividend_per_share"] == 0.50

    def test_dividend_from_row(self):
        """Test dividend creation from database row."""
        from app.models.dividend import Dividend

        row = {
            "id": 1,
            "symbol": "sh.600000",
            "dividend_date": "2026-06-15",
            "dividend_per_share": 0.50,
            "tax_rate": 0,
            "actual_received": 500.0,
            "status": "expected",
            "notes": "",
            "created_at": "2026-01-01",
        }

        dividend = Dividend.from_row(row)
        assert dividend.id == 1
        assert dividend.symbol == "sh.600000"

    def test_dividend_calendar_entry_to_dict(self):
        """Test dividend calendar entry serialization."""
        from app.models.dividend import DividendCalendarEntry

        entry = DividendCalendarEntry(
            symbol="sh.600000",
            plan_date="2026-06-15",
            ex_dividend_date="2026-06-10",
            record_date="2026-06-12",
            dividend_per_share=0.50,
        )

        data = entry.to_dict()
        assert data["symbol"] == "sh.600000"
        assert data["plan_date"] == "2026-06-15"
