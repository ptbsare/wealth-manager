"""Tests for MCP API endpoints."""

import pytest


class TestMCPAuth:
    """Test MCP authentication."""

    def test_mcp_holdings_no_auth(self, client):
        """Test accessing MCP holdings without auth."""
        response = client.get("/mcp/holdings")
        assert response.status_code == 401

    def test_mcp_holdings_invalid_token(self, client):
        """Test accessing MCP holdings with invalid token."""
        response = client.get(
            "/mcp/holdings",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 403

    def test_mcp_holdings_valid_token(self, client, auth_headers):
        """Test accessing MCP holdings with valid token."""
        response = client.get("/mcp/holdings", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "holdings" in data
        assert "count" in data

    def test_mcp_dividends_valid_token(self, client, auth_headers):
        """Test accessing MCP dividends with valid token."""
        response = client.get("/mcp/dividends", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "dividends" in data

    def test_mcp_calendar_valid_token(self, client, auth_headers):
        """Test accessing MCP calendar with valid token."""
        response = client.get("/mcp/calendar", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "calendar" in data

    def test_mcp_stats_valid_token(self, client, auth_headers):
        """Test accessing MCP stats with valid token."""
        response = client.get("/mcp/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_holdings" in data
        assert "total_cost" in data


class TestMCPCRUD:
    """Test MCP CRUD operations."""

    def test_mcp_create_holding(self, client, auth_headers, sample_holding_data):
        """Test creating holding via MCP."""
        response = client.post("/mcp/holdings", json=sample_holding_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == sample_holding_data["symbol"]

    def test_mcp_update_holding(self, client, auth_headers, sample_holding_data):
        """Test updating holding via MCP."""
        # Create holding
        create_resp = client.post("/mcp/holdings", json=sample_holding_data, headers=auth_headers)
        holding_id = create_resp.json()["id"]

        # Update holding
        update_data = {"quantity": 2000}
        response = client.put(
            f"/mcp/holdings/{holding_id}",
            json=update_data,
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["quantity"] == 2000

    def test_mcp_delete_holding(self, client, auth_headers, sample_holding_data):
        """Test deleting holding via MCP."""
        # Create holding
        create_resp = client.post("/mcp/holdings", json=sample_holding_data, headers=auth_headers)
        holding_id = create_resp.json()["id"]

        # Delete holding
        response = client.delete(
            f"/mcp/holdings/{holding_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify deletion using regular API
        get_response = client.get(f"/api/holdings/{holding_id}")
        assert get_response.status_code == 404

    def test_mcp_create_dividend(self, client, auth_headers, sample_dividend_data):
        """Test creating dividend via MCP."""
        response = client.post("/mcp/dividends", json=sample_dividend_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == sample_dividend_data["symbol"]


class TestSettings:
    """Test settings API."""

    def test_get_settings(self, client):
        """Test getting settings."""
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert "mcp_token" in data
        assert "smtp_host" in data

    def test_update_settings(self, client):
        """Test updating settings."""
        settings_data = {
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "smtp_user": "test@test.com",
            "smtp_from": "test@test.com",
            "smtp_to": "recipient@test.com",
        }
        response = client.put("/api/settings", json=settings_data)
        assert response.status_code == 200

        # Verify update
        get_response = client.get("/api/settings")
        data = get_response.json()
        assert data["smtp_host"] == "smtp.test.com"
        assert data["smtp_port"] == 587

    def test_test_email_no_config(self, client):
        """Test email test with no SMTP config."""
        response = client.post("/api/settings/test-email")
        assert response.status_code == 400
