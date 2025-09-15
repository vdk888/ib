"""
Integration tests for Order Status API endpoints (Step 11)
Tests the complete API workflow including service integration
"""

import pytest
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from typing import Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, os.path.join(project_root, "backend"))

from app.main import app


class TestOrderStatusAPIEndpoints:
    """Test Order Status API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def sample_orders_data(self):
        """Sample orders data for testing"""
        return {
            "metadata": {
                "generated_at": "2024-01-15 14:30:00",
                "total_orders": 2
            },
            "orders": [
                {
                    "symbol": "AAPL",
                    "action": "BUY",
                    "quantity": 100,
                    "stock_info": {
                        "ticker": "AAPL",
                        "name": "Apple Inc",
                        "currency": "USD"
                    },
                    "ibkr_details": {
                        "symbol": "AAPL",
                        "exchange": "SMART",
                        "primaryExchange": "NASDAQ"
                    }
                },
                {
                    "symbol": "GOOGL",
                    "action": "SELL",
                    "quantity": 50,
                    "stock_info": {
                        "ticker": "GOOGL",
                        "name": "Alphabet Inc",
                        "currency": "USD"
                    },
                    "ibkr_details": {
                        "symbol": "GOOGL",
                        "exchange": "SMART",
                        "primaryExchange": "NASDAQ"
                    }
                }
            ]
        }

    @pytest.fixture
    def sample_verification_results(self):
        """Sample verification results"""
        return {
            "comparison_summary": {
                "found_in_ibkr": 1,
                "missing_from_ibkr": 1,
                "quantity_mismatches": 0,
                "success_rate": 50.0,
                "total_orders": 2,
                "timestamp": "2024-01-15T14:30:00"
            },
            "order_matches": [
                {
                    "symbol": "AAPL",
                    "json_action": "BUY",
                    "json_quantity": 100,
                    "ibkr_status": "FILLED",
                    "ibkr_quantity": 100,
                    "match_status": "OK"
                },
                {
                    "symbol": "GOOGL",
                    "json_action": "SELL",
                    "json_quantity": 50,
                    "ibkr_status": "NOT_FOUND",
                    "ibkr_quantity": None,
                    "match_status": "MISSING"
                }
            ],
            "missing_orders": [
                {
                    "symbol": "GOOGL",
                    "action": "SELL",
                    "quantity": 50,
                    "currency": "USD",
                    "ticker": "GOOGL",
                    "exchange": "NASDAQ",
                    "reason": "Unknown - Requires Debug Investigation",
                    "details": "Run debug_order_executor.py to identify specific error codes",
                    "note": "Check contract details, account permissions, and market hours"
                }
            ],
            "recommendations": [
                "Check account settings and current positions",
                "Verify contract details and market availability"
            ],
            "extra_orders": [],
            "positions": {
                "AAPL": {
                    "position": 100,
                    "avg_cost": 150.0,
                    "currency": "USD",
                    "exchange": "NASDAQ",
                    "market_value": 15000.0
                }
            },
            "order_status_breakdown": {
                "FILLED": [
                    {
                        "order_id": 123,
                        "symbol": "AAPL",
                        "action": "BUY",
                        "quantity": 100,
                        "filled": 100,
                        "status": "FILLED",
                        "avg_fill_price": 150.0,
                        "order_type": "MKT"
                    }
                ]
            }
        }

    def test_check_order_status_success(self, client, sample_orders_data, sample_verification_results, tmp_path):
        """Test successful order status check"""
        # Create test orders file
        orders_file = tmp_path / "test_orders.json"
        with open(orders_file, 'w') as f:
            json.dump(sample_orders_data, f)

        # Mock the service
        mock_service = Mock()
        mock_service.load_orders_json.return_value = sample_orders_data
        mock_service.connect_to_ibkr.return_value = True
        mock_service.get_verification_results.return_value = sample_verification_results
        mock_service.disconnect = Mock()

        with patch('app.api.v1.endpoints.orders.OrderStatusService') as MockService:
            MockService.return_value = mock_service

            response = client.post(
                "/api/v1/orders/status/check",
                params={"orders_file": str(orders_file)}
            )

            assert response.status_code == 200
            data = response.json()

            # Check response structure
            assert data["success"] is True
            assert "comparison_summary" in data
            assert "order_matches" in data
            assert "missing_orders" in data
            assert "recommendations" in data
            assert "positions" in data
            assert "order_status_breakdown" in data

            # Check comparison summary
            summary = data["comparison_summary"]
            assert summary["success_rate"] == 50.0
            assert summary["total_orders"] == 2
            assert summary["found_in_ibkr"] == 1
            assert summary["missing_from_ibkr"] == 1

            # Check order matches
            assert len(data["order_matches"]) == 2
            aapl_match = next(m for m in data["order_matches"] if m["symbol"] == "AAPL")
            assert aapl_match["match_status"] == "OK"

            # Check missing orders analysis
            assert len(data["missing_orders"]) == 1
            assert data["missing_orders"][0]["symbol"] == "GOOGL"

            # Verify service calls
            MockService.assert_called_once_with(str(orders_file))
            mock_service.load_orders_json.assert_called_once()
            mock_service.connect_to_ibkr.assert_called_once()
            mock_service.fetch_account_data.assert_called_once()
            mock_service.get_verification_results.assert_called_once()
            mock_service.disconnect.assert_called_once()

    def test_check_order_status_file_not_found(self, client):
        """Test order status check with missing orders file"""
        mock_service = Mock()
        mock_service.load_orders_json.side_effect = FileNotFoundError("Orders file not found")

        with patch('app.api.v1.endpoints.orders.OrderStatusService') as MockService:
            MockService.return_value = mock_service

            response = client.post(
                "/api/v1/orders/status/check",
                params={"orders_file": "non_existent.json"}
            )

            assert response.status_code == 404
            data = response.json()
            assert "Orders file not found" in data["detail"]

    def test_check_order_status_ibkr_connection_failed(self, client, tmp_path):
        """Test order status check with IBKR connection failure"""
        # Create test orders file
        orders_file = tmp_path / "test_orders.json"
        with open(orders_file, 'w') as f:
            json.dump({"metadata": {"total_orders": 0}, "orders": []}, f)

        mock_service = Mock()
        mock_service.load_orders_json.return_value = {"metadata": {"total_orders": 0}, "orders": []}
        mock_service.connect_to_ibkr.return_value = False

        with patch('app.api.v1.endpoints.orders.OrderStatusService') as MockService:
            MockService.return_value = mock_service

            response = client.post(
                "/api/v1/orders/status/check",
                params={"orders_file": str(orders_file)}
            )

            assert response.status_code == 500
            data = response.json()
            assert "Failed to connect to IBKR Gateway" in data["detail"]

    def test_get_current_order_status_success(self, client):
        """Test getting current IBKR order status"""
        mock_orders_summary = {
            "orders_by_status": {
                "FILLED": [
                    {
                        "order_id": 123,
                        "symbol": "AAPL",
                        "action": "BUY",
                        "quantity": 100,
                        "filled": 100,
                        "status": "FILLED",
                        "avg_fill_price": 150.0,
                        "order_type": "MKT"
                    }
                ],
                "SUBMITTED": [
                    {
                        "order_id": 124,
                        "symbol": "GOOGL",
                        "action": "SELL",
                        "quantity": 50,
                        "filled": 0,
                        "status": "SUBMITTED",
                        "avg_fill_price": "N/A",
                        "order_type": "MKT"
                    }
                ]
            },
            "status_counts": {
                "FILLED": 1,
                "SUBMITTED": 1
            },
            "total_orders": 2,
            "order_details": [
                {
                    "order_id": 123,
                    "symbol": "AAPL",
                    "action": "BUY",
                    "quantity": 100,
                    "filled": 100,
                    "status": "FILLED"
                },
                {
                    "order_id": 124,
                    "symbol": "GOOGL",
                    "action": "SELL",
                    "quantity": 50,
                    "filled": 0,
                    "status": "SUBMITTED"
                }
            ]
        }

        mock_service = Mock()
        mock_service.connect_to_ibkr.return_value = True
        mock_service.get_order_status_summary.return_value = mock_orders_summary
        mock_service.disconnect = Mock()

        with patch('app.api.v1.endpoints.orders.OrderStatusService') as MockService:
            MockService.return_value = mock_service

            response = client.get("/api/v1/orders/status/current")

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert "orders_by_status" in data
            assert "status_counts" in data
            assert "total_orders" in data

            # Check status breakdown
            assert "FILLED" in data["orders_by_status"]
            assert "SUBMITTED" in data["orders_by_status"]
            assert len(data["orders_by_status"]["FILLED"]) == 1
            assert len(data["orders_by_status"]["SUBMITTED"]) == 1

            # Check counts
            assert data["status_counts"]["FILLED"] == 1
            assert data["status_counts"]["SUBMITTED"] == 1
            assert data["total_orders"] == 2

            # Verify service calls
            mock_service.connect_to_ibkr.assert_called_once()
            mock_service.fetch_account_data.assert_called_once()
            mock_service.get_order_status_summary.assert_called_once()
            mock_service.disconnect.assert_called_once()

    def test_get_positions_summary_success(self, client):
        """Test getting account positions summary"""
        mock_positions_summary = {
            "positions": {
                "AAPL": {
                    "position": 150,
                    "avg_cost": 145.50,
                    "currency": "USD",
                    "exchange": "NASDAQ",
                    "market_value": 21825.0
                },
                "GOOGL": {
                    "position": 75,
                    "avg_cost": 140.00,
                    "currency": "USD",
                    "exchange": "NASDAQ",
                    "market_value": 10500.0
                }
            },
            "total_positions": 2,
            "market_values": {
                "AAPL": 21825.0,
                "GOOGL": 10500.0
            },
            "total_market_value": 32325.0
        }

        mock_service = Mock()
        mock_service.connect_to_ibkr.return_value = True
        mock_service.get_positions_summary.return_value = mock_positions_summary
        mock_service.disconnect = Mock()

        with patch('app.api.v1.endpoints.orders.OrderStatusService') as MockService:
            MockService.return_value = mock_service

            response = client.get("/api/v1/orders/positions/summary")

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert "positions" in data
            assert "total_positions" in data
            assert "market_values" in data
            assert "total_market_value" in data

            # Check positions
            assert "AAPL" in data["positions"]
            assert "GOOGL" in data["positions"]
            assert data["positions"]["AAPL"]["position"] == 150
            assert data["positions"]["GOOGL"]["position"] == 75

            # Check totals
            assert data["total_positions"] == 2
            assert data["total_market_value"] == 32325.0

            # Verify service calls
            mock_service.connect_to_ibkr.assert_called_once()
            mock_service.fetch_account_data.assert_called_once()
            mock_service.get_positions_summary.assert_called_once()
            mock_service.disconnect.assert_called_once()

    def test_get_verification_results_no_cache(self, client):
        """Test getting cached verification results when none exist"""
        response = client.get("/api/v1/orders/verification/results")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is False
        assert "No cached results available" in data["message"]
        assert "suggestion" in data

    def test_connection_error_handling(self, client):
        """Test proper handling of IBKR connection errors"""
        mock_service = Mock()
        mock_service.connect_to_ibkr.side_effect = ConnectionError("Failed to connect to IBKR Gateway")

        with patch('app.api.v1.endpoints.orders.OrderStatusService') as MockService:
            MockService.return_value = mock_service

            response = client.get("/api/v1/orders/status/current")

            assert response.status_code == 500
            data = response.json()
            assert "Error fetching order status" in data["detail"]

    def test_general_exception_handling(self, client):
        """Test proper handling of general exceptions"""
        mock_service = Mock()
        mock_service.connect_to_ibkr.side_effect = Exception("Unexpected error")

        with patch('app.api.v1.endpoints.orders.OrderStatusService') as MockService:
            MockService.return_value = mock_service

            response = client.get("/api/v1/orders/positions/summary")

            assert response.status_code == 500
            data = response.json()
            assert "Error fetching positions summary" in data["detail"]


class TestOrderStatusAPIIntegration:
    """Integration tests for complete API workflow"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_complete_order_status_workflow(self, client, tmp_path):
        """Test complete order status checking workflow through API"""
        # Create test orders file
        orders_data = {
            "metadata": {"total_orders": 1},
            "orders": [{
                "symbol": "AAPL",
                "action": "BUY",
                "quantity": 100,
                "stock_info": {"ticker": "AAPL", "currency": "USD"},
                "ibkr_details": {"primaryExchange": "NASDAQ"}
            }]
        }

        orders_file = tmp_path / "test_orders.json"
        with open(orders_file, 'w') as f:
            json.dump(orders_data, f)

        # Mock complete verification results
        verification_results = {
            "comparison_summary": {
                "found_in_ibkr": 1,
                "missing_from_ibkr": 0,
                "quantity_mismatches": 0,
                "success_rate": 100.0,
                "total_orders": 1,
                "timestamp": "2024-01-15T14:30:00"
            },
            "order_matches": [{
                "symbol": "AAPL",
                "json_action": "BUY",
                "json_quantity": 100,
                "ibkr_status": "FILLED",
                "ibkr_quantity": 100,
                "match_status": "OK"
            }],
            "missing_orders": [],
            "recommendations": [],
            "extra_orders": [],
            "positions": {
                "AAPL": {
                    "position": 100,
                    "avg_cost": 150.0,
                    "currency": "USD",
                    "exchange": "NASDAQ",
                    "market_value": 15000.0
                }
            },
            "order_status_breakdown": {
                "FILLED": [{
                    "order_id": 123,
                    "symbol": "AAPL",
                    "action": "BUY",
                    "quantity": 100,
                    "filled": 100,
                    "status": "FILLED",
                    "avg_fill_price": 150.0,
                    "order_type": "MKT"
                }]
            }
        }

        mock_service = Mock()
        mock_service.load_orders_json.return_value = orders_data
        mock_service.connect_to_ibkr.return_value = True
        mock_service.get_verification_results.return_value = verification_results
        mock_service.disconnect = Mock()

        with patch('app.api.v1.endpoints.orders.OrderStatusService') as MockService:
            MockService.return_value = mock_service

            # 1. Check order status
            response = client.post(
                "/api/v1/orders/status/check",
                params={"orders_file": str(orders_file)}
            )

            assert response.status_code == 200
            check_data = response.json()

            # Verify complete response structure
            assert check_data["success"] is True
            assert check_data["comparison_summary"]["success_rate"] == 100.0
            assert len(check_data["order_matches"]) == 1
            assert len(check_data["missing_orders"]) == 0
            assert "AAPL" in check_data["positions"]

            # 2. Get current order status (separate call)
            mock_service.get_order_status_summary.return_value = {
                "orders_by_status": verification_results["order_status_breakdown"],
                "status_counts": {"FILLED": 1},
                "total_orders": 1,
                "order_details": verification_results["order_status_breakdown"]["FILLED"]
            }

            response = client.get("/api/v1/orders/status/current")
            assert response.status_code == 200
            status_data = response.json()
            assert status_data["total_orders"] == 1
            assert "FILLED" in status_data["orders_by_status"]

            # 3. Get positions summary (separate call)
            mock_service.get_positions_summary.return_value = {
                "positions": verification_results["positions"],
                "total_positions": 1,
                "market_values": {"AAPL": 15000.0},
                "total_market_value": 15000.0
            }

            response = client.get("/api/v1/orders/positions/summary")
            assert response.status_code == 200
            positions_data = response.json()
            assert positions_data["total_positions"] == 1
            assert positions_data["total_market_value"] == 15000.0

            # Verify all service interactions
            assert MockService.call_count >= 3  # Called for each endpoint
            # Each service instance should have been used
            assert mock_service.connect_to_ibkr.call_count >= 3
            assert mock_service.disconnect.call_count >= 3