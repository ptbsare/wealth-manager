"""Tests for holdings API endpoints."""

import pytest


class TestHoldingsCRUD:
    """Test holdings CRUD operations."""

    def test_list_holdings_empty(self, client):
        """Test listing holdings when empty."""
        response = client.get("/api/holdings")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_holding(self, client, sample_holding_data):
        """Test creating a new holding."""
        response = client.post("/api/holdings", json=sample_holding_data)
        assert response.status_code == 201
        data = response.json()
        assert data["symbol"] == sample_holding_data["symbol"]
        assert data["quantity"] == sample_holding_data["quantity"]
        assert data["cost_price"] == sample_holding_data["cost_price"]
        assert "id" in data

    def test_create_holding_duplicate_symbol(self, client, sample_holding_data):
        """Test creating a holding with duplicate symbol merges quantities."""
        # Create initial holding
        response1 = client.post("/api/holdings", json=sample_holding_data)
        assert response1.status_code == 201
        initial = response1.json()
        
        # Add same stock again - should merge
        response2 = client.post("/api/holdings", json=sample_holding_data)
        assert response2.status_code == 201
        merged = response2.json()
        
        # Quantity should be doubled
        assert merged["quantity"] == initial["quantity"] * 2

    def test_get_holding(self, client, sample_holding_data):
        """Test getting a specific holding."""
        create_resp = client.post("/api/holdings", json=sample_holding_data)
        holding_id = create_resp.json()["id"]

        response = client.get(f"/api/holdings/{holding_id}")
        assert response.status_code == 200
        assert response.json()["id"] == holding_id

    def test_get_holding_not_found(self, client):
        """Test getting a non-existent holding."""
        response = client.get("/api/holdings/99999")
        assert response.status_code == 404

    def test_update_holding(self, client, sample_holding_data):
        """Test updating a holding."""
        create_resp = client.post("/api/holdings", json=sample_holding_data)
        holding_id = create_resp.json()["id"]

        update_data = {"quantity": 2000, "cost_price": 11.00}
        response = client.put(f"/api/holdings/{holding_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 2000
        assert data["cost_price"] == 11.00

    def test_update_holding_not_found(self, client):
        """Test updating a non-existent holding."""
        response = client.put("/api/holdings/99999", json={"quantity": 100})
        assert response.status_code == 404

    def test_delete_holding(self, client, sample_holding_data):
        """Test deleting a holding."""
        create_resp = client.post("/api/holdings", json=sample_holding_data)
        holding_id = create_resp.json()["id"]

        response = client.delete(f"/api/holdings/{holding_id}")
        assert response.status_code == 200

        # Verify deletion
        get_response = client.get(f"/api/holdings/{holding_id}")
        assert get_response.status_code == 404

    def test_delete_holding_not_found(self, client):
        """Test deleting a non-existent holding."""
        response = client.delete("/api/holdings/99999")
        assert response.status_code == 404

    def test_list_holdings_with_data(self, client, sample_holding_data):
        """Test listing holdings with data."""
        client.post("/api/holdings", json=sample_holding_data)
        response = client.get("/api/holdings")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == sample_holding_data["symbol"]

    def test_holding_calculated_fields(self, client, sample_holding_data):
        """Test that calculated fields are correct."""
        create_resp = client.post("/api/holdings", json=sample_holding_data)
        holding_id = create_resp.json()["id"]

        response = client.get(f"/api/holdings/{holding_id}")
        data = response.json()

        # cost_value = quantity * cost_price = 1000 * 10.50 = 10500
        assert data["cost_value"] == 10500.0
        # current_price is fetched from BaoStock (9.37 for sh.600000)
        # market_value = quantity * current_price
        assert data["market_value"] == data["current_price"] * data["quantity"]
        # profit = market_value - cost_value
        assert data["profit"] == data["market_value"] - data["cost_value"]


class TestHoldingModel:
    """Test Holding model calculations."""

    def test_holding_profit_calculation(self):
        """Test profit calculation in Holding model."""
        from app.models.holding import Holding

        holding = Holding(
            symbol="sh.600000",
            name="Test Stock",
            quantity=1000,
            cost_price=10.0,
            current_price=12.0,
        )

        assert holding.cost_value == 10000.0
        assert holding.market_value == 12000.0
        assert holding.profit == 2000.0
        assert holding.profit_rate == pytest.approx(20.0)

    def test_holding_loss_calculation(self):
        """Test loss calculation in Holding model."""
        from app.models.holding import Holding

        holding = Holding(
            symbol="sh.600000",
            name="Test Stock",
            quantity=1000,
            cost_price=12.0,
            current_price=10.0,
        )

        assert holding.profit == -2000.0
        assert holding.profit_rate == pytest.approx(-16.67, rel=0.01)

    def test_holding_zero_cost(self):
        """Test holding with zero cost."""
        from app.models.holding import Holding

        holding = Holding(
            symbol="sh.600000",
            name="Test Stock",
            quantity=1000,
            cost_price=0,
            current_price=12.0,
        )

        assert holding.profit_rate == 0.0

    def test_holding_to_dict(self):
        """Test holding serialization."""
        from app.models.holding import Holding

        holding = Holding(
            id=1,
            symbol="sh.600000",
            name="Test Stock",
            quantity=100,
            cost_price=10.0,
            current_price=12.0,
        )

        data = holding.to_dict()
        assert data["id"] == 1
        assert data["symbol"] == "sh.600000"
        assert data["cost_value"] == 1000.0
        assert data["market_value"] == 1200.0

    def test_holding_from_row(self):
        """Test holding creation from database row."""
        from app.models.holding import Holding

        row = {
            "id": 1,
            "symbol": "sh.600000",
            "name": "Test Stock",
            "quantity": 100,
            "cost_price": 10.0,
            "current_price": 12.0,
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }

        holding = Holding.from_row(row)
        assert holding.id == 1
        assert holding.symbol == "sh.600000"
        assert holding.quantity == 100
