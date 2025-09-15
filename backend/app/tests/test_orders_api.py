#!/usr/bin/env python3
"""
API integration tests for Orders endpoints
Tests Step 9: Rebalancing Orders Service API endpoints
"""
import pytest
import json
import os
import tempfile
import shutil
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Import the FastAPI app and dependencies
from backend.app.main import app
from backend.app.core.dependencies import get_rebalancing_service


class TestOrdersAPI:
    """Test suite for Orders API endpoints"""

    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
        self.temp_dir = tempfile.mkdtemp()

        # Mock universe data
        self.mock_universe_data = {
            "metadata": {
                "total_stocks": 3,
                "screens": ["growth", "value"]
            },
            "screens": {
                "growth": {
                    "stocks": [
                        {
                            "ticker": "AAPL",
                            "name": "Apple Inc",
                            "currency": "USD",
                            "sector": "Technology",
                            "country": "US",
                            "quantity": 100,
                            "screens": ["growth"],
                            "ibkr_details": {
                                "found": True,
                                "symbol": "AAPL",
                                "exchange": "NASDAQ",
                                "primaryExchange": "NASDAQ",
                                "conId": 265598
                            }
                        }
                    ]
                }
            }
        }

        # Mock rebalancing results
        self.mock_rebalancing_results = {
            "orders": [
                {
                    "symbol": "AAPL",
                    "action": "BUY",
                    "quantity": 20,
                    "current_quantity": 80,
                    "target_quantity": 100,
                    "stock_info": {
                        "ticker": "AAPL",
                        "name": "Apple Inc",
                        "currency": "USD",
                        "screens": ["growth"]
                    },
                    "ibkr_details": {
                        "symbol": "AAPL",
                        "exchange": "NASDAQ",
                        "primaryExchange": "NASDAQ",
                        "conId": 265598
                    }
                }
            ],
            "metadata": {
                "generated_at": "2024-01-15 14:30:00",
                "total_orders": 1,
                "buy_orders": 1,
                "sell_orders": 0,
                "total_buy_quantity": 20,
                "total_sell_quantity": 0
            },
            "target_quantities": {"AAPL": 100},
            "current_positions": {"AAPL": 80}
        }

    def teardown_method(self):
        """Clean up after tests"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_generate_orders_success(self):
        """Test successful order generation endpoint"""
        # Mock the rebalancing service
        mock_service = Mock()
        mock_service.run_rebalancing.return_value = self.mock_rebalancing_results

        # Override dependency
        app.dependency_overrides[get_rebalancing_service] = lambda: mock_service

        try:
            response = self.client.post("/api/v1/orders/generate")

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert "orders" in data
            assert "metadata" in data
            assert data["message"] == "Rebalancing orders generated successfully"

            # Verify order structure
            orders = data["orders"]
            assert len(orders) == 1
            order = orders[0]
            assert order["symbol"] == "AAPL"
            assert order["action"] == "BUY"
            assert order["quantity"] == 20

        finally:
            app.dependency_overrides.clear()

    def test_generate_orders_with_custom_universe_file(self):
        """Test order generation with custom universe file path"""
        mock_service = Mock()
        mock_service.run_rebalancing.return_value = self.mock_rebalancing_results

        app.dependency_overrides[get_rebalancing_service] = lambda: mock_service

        try:
            response = self.client.post(
                "/api/v1/orders/generate",
                params={"universe_file": "custom/path/universe.json"}
            )

            assert response.status_code == 200
            # Verify the service was called with custom path
            mock_service.run_rebalancing.assert_called_once_with("custom/path/universe.json")

        finally:
            app.dependency_overrides.clear()

    def test_generate_orders_file_not_found(self):
        """Test order generation with non-existent universe file"""
        mock_service = Mock()
        mock_service.run_rebalancing.side_effect = FileNotFoundError("Universe file not found")

        app.dependency_overrides[get_rebalancing_service] = lambda: mock_service

        try:
            response = self.client.post("/api/v1/orders/generate")

            assert response.status_code == 404
            data = response.json()
            assert "Universe file not found" in data["detail"]

        finally:
            app.dependency_overrides.clear()

    def test_generate_orders_ibkr_connection_error(self):
        """Test order generation with IBKR connection failure"""
        mock_service = Mock()
        mock_service.run_rebalancing.side_effect = ConnectionError("Failed to connect to IBKR")

        app.dependency_overrides[get_rebalancing_service] = lambda: mock_service

        try:
            response = self.client.post("/api/v1/orders/generate")

            assert response.status_code == 500
            data = response.json()
            assert "Failed to connect to IBKR" in data["detail"]

        finally:
            app.dependency_overrides.clear()

    def test_get_orders_success(self):
        """Test successful orders retrieval"""
        # Create mock orders file
        orders_data = {
            "metadata": self.mock_rebalancing_results["metadata"],
            "orders": self.mock_rebalancing_results["orders"]
        }

        # Mock the file system access
        with patch("builtins.open", create=True) as mock_open:
            with patch("os.path.exists", return_value=True):
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(orders_data)

                response = self.client.get("/api/v1/orders")

                assert response.status_code == 200
                data = response.json()

                assert data["success"] is True
                assert "orders" in data
                assert "metadata" in data
                assert len(data["orders"]) == 1

    def test_get_orders_file_not_found(self):
        """Test orders retrieval when no orders file exists"""
        with patch("os.path.exists", return_value=False):
            response = self.client.get("/api/v1/orders")

            assert response.status_code == 404
            data = response.json()
            assert "No orders found" in data["detail"]

    def test_get_orders_invalid_json(self):
        """Test orders retrieval with corrupted orders file"""
        with patch("builtins.open", create=True) as mock_open:
            with patch("os.path.exists", return_value=True):
                # Return invalid JSON
                mock_open.return_value.__enter__.return_value.read.return_value = "invalid json"

                response = self.client.get("/api/v1/orders")

                assert response.status_code == 500
                data = response.json()
                assert "Error reading orders file" in data["detail"]

    def test_preview_orders_success(self):
        """Test successful orders preview generation"""
        mock_service = Mock()
        mock_service.load_universe_data.return_value = self.mock_universe_data
        mock_service.calculate_target_quantities.return_value = {"AAPL": 100}
        mock_service.fetch_current_positions.return_value = ({"AAPL": 80}, {})
        mock_service.generate_orders.return_value = self.mock_rebalancing_results["orders"]
        mock_service.symbol_details = {"AAPL": {}}

        app.dependency_overrides[get_rebalancing_service] = lambda: mock_service

        try:
            response = self.client.post("/api/v1/orders/preview")

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert "orders" in data
            assert "(PREVIEW)" in data["metadata"]["generated_at"]
            assert "not saved" in data["message"].lower()

            # Verify no save method was called
            assert not hasattr(mock_service, 'save_orders_json') or \
                   not mock_service.save_orders_json.called

        finally:
            app.dependency_overrides.clear()

    def test_get_current_positions_success(self):
        """Test successful current positions retrieval"""
        mock_service = Mock()
        current_positions = {"AAPL": 100, "MSFT": 75}
        contract_details = {
            "AAPL": {"symbol": "AAPL", "conId": 265598},
            "MSFT": {"symbol": "MSFT", "conId": 272093}
        }
        mock_service.fetch_current_positions.return_value = (current_positions, contract_details)

        app.dependency_overrides[get_rebalancing_service] = lambda: mock_service

        try:
            response = self.client.get("/api/v1/orders/positions/current")

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["positions"] == current_positions
            assert data["contract_details"] == contract_details
            assert "retrieved from IBKR" in data["message"]

        finally:
            app.dependency_overrides.clear()

    def test_get_current_positions_connection_error(self):
        """Test current positions with IBKR connection error"""
        mock_service = Mock()
        mock_service.fetch_current_positions.side_effect = Exception("IBKR connection failed")

        app.dependency_overrides[get_rebalancing_service] = lambda: mock_service

        try:
            response = self.client.get("/api/v1/orders/positions/current")

            assert response.status_code == 500
            data = response.json()
            assert "Error fetching current positions" in data["detail"]

        finally:
            app.dependency_overrides.clear()

    def test_get_target_quantities_success(self):
        """Test successful target quantities calculation"""
        mock_service = Mock()
        mock_service.load_universe_data.return_value = self.mock_universe_data
        target_quantities = {"AAPL": 100, "MSFT": 75, "GOOGL": 50}
        mock_service.calculate_target_quantities.return_value = target_quantities

        app.dependency_overrides[get_rebalancing_service] = lambda: mock_service

        try:
            response = self.client.get("/api/v1/orders/positions/targets")

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["target_quantities"] == target_quantities
            assert data["total_symbols"] == 3
            assert data["total_shares"] == 225  # 100 + 75 + 50

        finally:
            app.dependency_overrides.clear()

    def test_get_target_quantities_with_custom_universe(self):
        """Test target quantities with custom universe file"""
        mock_service = Mock()
        mock_service.load_universe_data.return_value = self.mock_universe_data
        mock_service.calculate_target_quantities.return_value = {"AAPL": 100}

        app.dependency_overrides[get_rebalancing_service] = lambda: mock_service

        try:
            response = self.client.get(
                "/api/v1/orders/positions/targets",
                params={"universe_file": "custom/universe.json"}
            )

            assert response.status_code == 200
            # Verify the service was called with custom path
            mock_service.load_universe_data.assert_called_once_with("custom/universe.json")

        finally:
            app.dependency_overrides.clear()

    def test_get_target_quantities_file_not_found(self):
        """Test target quantities with non-existent universe file"""
        mock_service = Mock()
        mock_service.load_universe_data.side_effect = FileNotFoundError("Universe file not found")

        app.dependency_overrides[get_rebalancing_service] = lambda: mock_service

        try:
            response = self.client.get("/api/v1/orders/positions/targets")

            assert response.status_code == 404
            data = response.json()
            assert "Universe file not found" in data["detail"]

        finally:
            app.dependency_overrides.clear()


class TestOrdersAPIResponseValidation:
    """Test response model validation for Orders API"""

    def test_rebalancing_response_validation(self):
        """Test that API responses match Pydantic model validation"""
        client = TestClient(app)

        # Create valid mock response
        valid_response = {
            "orders": [
                {
                    "symbol": "AAPL",
                    "action": "BUY",
                    "quantity": 100,
                    "current_quantity": 0,
                    "target_quantity": 100,
                    "stock_info": {
                        "ticker": "AAPL",
                        "name": "Apple Inc",
                        "currency": "USD",
                        "screens": ["growth"]
                    },
                    "ibkr_details": {
                        "symbol": "AAPL",
                        "exchange": "NASDAQ",
                        "primaryExchange": "NASDAQ",
                        "conId": 265598
                    }
                }
            ],
            "metadata": {
                "generated_at": "2024-01-15 14:30:00",
                "total_orders": 1,
                "buy_orders": 1,
                "sell_orders": 0,
                "total_buy_quantity": 100,
                "total_sell_quantity": 0
            },
            "target_quantities": {"AAPL": 100},
            "current_positions": {"AAPL": 0}
        }

        mock_service = Mock()
        mock_service.run_rebalancing.return_value = valid_response

        app.dependency_overrides[get_rebalancing_service] = lambda: mock_service

        try:
            response = client.post("/api/v1/orders/generate")

            # Should succeed with valid data structure
            assert response.status_code == 200

            data = response.json()
            # Verify all required fields are present
            required_fields = ["success", "orders", "metadata", "target_quantities", "current_positions", "message"]
            for field in required_fields:
                assert field in data

        finally:
            app.dependency_overrides.clear()

    def test_orders_endpoint_openapi_schema(self):
        """Test that Orders endpoints are properly documented in OpenAPI schema"""
        client = TestClient(app)

        # Get OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        paths = schema["paths"]

        # Verify all orders endpoints are documented
        expected_endpoints = [
            "/api/v1/orders/generate",
            "/api/v1/orders",
            "/api/v1/orders/preview",
            "/api/v1/orders/positions/current",
            "/api/v1/orders/positions/targets"
        ]

        for endpoint in expected_endpoints:
            assert endpoint in paths, f"Endpoint {endpoint} not found in OpenAPI schema"

        # Verify endpoint has proper documentation
        generate_endpoint = paths["/api/v1/orders/generate"]
        assert "post" in generate_endpoint
        assert "summary" in generate_endpoint["post"]
        assert "description" in generate_endpoint["post"]
        assert "responses" in generate_endpoint["post"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])