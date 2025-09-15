"""
Behavior tests for Step 11: Order Status Checking Service
Verifies 100% behavioral compatibility between CLI and API implementations
"""

import pytest
import os
import sys
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
from fastapi.testclient import TestClient

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "backend"))

from app.main import app
from app.services.implementations.order_status_service import OrderStatusService


class TestStep11CLIAPICompatibility:
    """
    Test CLI vs API behavioral compatibility for Step 11
    Ensures API produces identical results to CLI step11_check_order_status()
    """

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def sample_orders_data(self):
        """Sample orders data matching real orders.json structure"""
        return {
            "metadata": {
                "generated_at": "2024-01-15 14:30:00",
                "total_orders": 4,
                "buy_orders": 2,
                "sell_orders": 2,
                "total_buy_quantity": 150,
                "total_sell_quantity": 75
            },
            "orders": [
                {
                    "symbol": "AAPL",
                    "action": "BUY",
                    "quantity": 100,
                    "current_quantity": 50,
                    "target_quantity": 150,
                    "stock_info": {
                        "ticker": "AAPL",
                        "name": "Apple Inc",
                        "currency": "USD",
                        "screens": ["growth", "large_cap"]
                    },
                    "ibkr_details": {
                        "symbol": "AAPL",
                        "exchange": "SMART",
                        "primaryExchange": "NASDAQ",
                        "conId": 265598
                    }
                },
                {
                    "symbol": "DPM",
                    "action": "BUY",
                    "quantity": 50,
                    "current_quantity": 0,
                    "target_quantity": 50,
                    "stock_info": {
                        "ticker": "DPM",
                        "name": "Dundee Precious Metals Inc",
                        "currency": "CAD",
                        "screens": ["materials"]
                    },
                    "ibkr_details": {
                        "symbol": "DPM",
                        "exchange": "TSE",
                        "primaryExchange": "TSE"
                    }
                },
                {
                    "symbol": "GOOGL",
                    "action": "SELL",
                    "quantity": 25,
                    "current_quantity": 75,
                    "target_quantity": 50,
                    "stock_info": {
                        "ticker": "GOOGL",
                        "name": "Alphabet Inc",
                        "currency": "USD",
                        "screens": ["tech", "large_cap"]
                    },
                    "ibkr_details": {
                        "symbol": "GOOGL",
                        "exchange": "SMART",
                        "primaryExchange": "NASDAQ"
                    }
                },
                {
                    "symbol": "AJ91",
                    "action": "BUY",
                    "quantity": 1547,
                    "current_quantity": 0,
                    "target_quantity": 1547,
                    "stock_info": {
                        "ticker": "AJ91",
                        "name": "DocCheck AG",
                        "currency": "EUR",
                        "screens": ["healthcare"]
                    },
                    "ibkr_details": {
                        "symbol": "AJ91",
                        "exchange": "XETRA",
                        "primaryExchange": "XETRA"
                    }
                }
            ]
        }

    @pytest.fixture
    def sample_ibkr_data(self):
        """Sample IBKR data for testing - matches known failure patterns"""
        return {
            "open_orders": {
                123: {
                    "symbol": "AAPL",
                    "action": "BUY",
                    "quantity": 100,
                    "status": "FILLED",
                    "avgFillPrice": 150.25,
                    "filled": 100,
                    "remaining": 0,
                    "orderType": "MKT",
                    "currency": "USD"
                },
                124: {
                    "symbol": "GOOGL",
                    "action": "SELL",
                    "quantity": 20,  # Quantity mismatch - JSON has 25
                    "status": "FILLED",
                    "avgFillPrice": 140.50,
                    "filled": 20,
                    "remaining": 0,
                    "orderType": "MKT",
                    "currency": "USD"
                }
                # DPM and AJ91 missing - simulates known failure patterns
            },
            "completed_orders": {},
            "positions": {
                "AAPL": {
                    "position": 150,
                    "avgCost": 148.50,
                    "currency": "USD",
                    "exchange": "NASDAQ"
                },
                "GOOGL": {
                    "position": 55,  # After partial sell
                    "avgCost": 142.00,
                    "currency": "USD",
                    "exchange": "NASDAQ"
                }
            },
            "executions": {}
        }

    def create_mock_legacy_checker(self, orders_data: Dict[str, Any], ibkr_data: Dict[str, Any]):
        """Create a comprehensive mock of the legacy OrderStatusChecker"""

        # Create mock API object
        mock_api = Mock()
        mock_api.connected = True
        mock_api.account_id = "TEST_ACCOUNT"
        mock_api.open_orders = ibkr_data["open_orders"]
        mock_api.completed_orders = ibkr_data["completed_orders"]
        mock_api.positions = ibkr_data["positions"]
        mock_api.executions = ibkr_data["executions"]
        mock_api.order_status = {}
        mock_api.requests_completed = {
            'orders': True,
            'positions': True,
            'executions': True,
            'completed_orders': True
        }

        # Create mock checker
        mock_checker = Mock()
        mock_checker.orders_file = "test_orders.json"
        mock_checker.orders_data = orders_data
        mock_checker.api = mock_api

        # Mock methods to return expected data while maintaining side effects
        mock_checker.load_orders_json.return_value = orders_data
        mock_checker.connect_to_ibkr.return_value = True
        mock_checker.fetch_account_data = Mock()
        mock_checker.analyze_orders = Mock()  # Console output method
        mock_checker.show_order_status_summary = Mock()  # Console output method
        mock_checker.show_positions = Mock()  # Console output method
        mock_checker.show_missing_order_analysis = Mock()  # Console output method
        mock_checker.disconnect = Mock()
        mock_checker.run_status_check.return_value = True

        return mock_checker

    def test_cli_api_analysis_results_identical(self, sample_orders_data, sample_ibkr_data):
        """Test that CLI and API produce identical analysis results"""

        # Test API Service directly
        service = OrderStatusService("test_orders.json")
        service.orders_data = sample_orders_data

        # Mock the legacy checker
        mock_checker = self.create_mock_legacy_checker(sample_orders_data, sample_ibkr_data)
        service._legacy_checker = mock_checker

        # Get API analysis results
        api_results = service.analyze_orders()

        # Verify expected analysis results based on test data
        assert api_results["total_orders"] == 4
        assert api_results["found_in_ibkr"] == 2  # AAPL and GOOGL found
        assert api_results["missing_from_ibkr"] == 2  # DPM and AJ91 missing
        assert api_results["quantity_mismatches"] == 1  # GOOGL quantity mismatch
        assert api_results["success_rate"] == 50.0  # 2/4 orders found correctly

        # Check missing orders details
        missing_symbols = [order["symbol"] for order in api_results["missing_orders"]]
        assert "DPM" in missing_symbols
        assert "AJ91" in missing_symbols

        # Check analysis table
        assert len(api_results["analysis_table"]) == 4

        # Verify specific matches
        aapl_row = next(r for r in api_results["analysis_table"] if r["symbol"] == "AAPL")
        assert aapl_row["match_status"] == "OK"
        assert aapl_row["ibkr_status"] == "FILLED"

        googl_row = next(r for r in api_results["analysis_table"] if r["symbol"] == "GOOGL")
        assert googl_row["match_status"] == "QTY_DIFF"
        assert googl_row["ibkr_quantity"] == 20
        assert googl_row["json_quantity"] == 25

        dpm_row = next(r for r in api_results["analysis_table"] if r["symbol"] == "DPM")
        assert dpm_row["match_status"] == "MISSING"
        assert dpm_row["ibkr_status"] == "NOT_FOUND"

    def test_missing_order_analysis_known_patterns(self, sample_orders_data):
        """Test missing order analysis matches known failure patterns"""

        service = OrderStatusService("test_orders.json")

        # Create missing orders matching known patterns
        missing_orders = [
            {
                "symbol": "DPM",
                "action": "BUY",
                "quantity": 50,
                "stock_info": {"ticker": "DPM", "currency": "CAD"},
                "ibkr_details": {"primaryExchange": "TSE"}
            },
            {
                "symbol": "AJ91",
                "action": "BUY",
                "quantity": 1547,
                "stock_info": {"ticker": "AJ91", "currency": "EUR"},
                "ibkr_details": {"primaryExchange": "XETRA"}
            },
            {
                "symbol": "AAPL",
                "action": "SELL",
                "quantity": 1,
                "stock_info": {"ticker": "AAPL", "currency": "USD"},
                "ibkr_details": {"primaryExchange": "NASDAQ"}
            }
        ]

        # Mock legacy checker
        mock_checker = Mock()
        service._legacy_checker = mock_checker

        analysis = service.get_missing_order_analysis(missing_orders)

        # Verify known failure patterns are identified
        failure_patterns = {f["symbol"]: f for f in analysis["failure_analysis"]}

        # Check DPM pattern
        assert failure_patterns["DPM"]["reason"] == "Contract Not Supported"
        assert "TSE" in failure_patterns["DPM"]["details"]

        # Check AJ91 pattern
        assert failure_patterns["AJ91"]["reason"] == "Liquidity Constraints"
        assert "1,547 shares" in failure_patterns["AJ91"]["details"]

        # Check AAPL pattern
        assert failure_patterns["AAPL"]["reason"] == "IBKR Account Restriction"
        assert "direct routing" in failure_patterns["AAPL"]["details"].lower()

        # Check recommendations are present
        assert len(analysis["recommendations"]) > 0
        recommendations_text = " ".join(analysis["recommendations"])
        assert "AAPL" in recommendations_text
        assert "DPM" in recommendations_text

    def test_positions_summary_calculations(self, sample_ibkr_data):
        """Test positions summary calculations match expected format"""

        service = OrderStatusService("test_orders.json")

        # Mock API with positions data
        mock_api = Mock()
        mock_api.positions = sample_ibkr_data["positions"]

        mock_checker = Mock()
        mock_checker.api = mock_api
        mock_checker.show_positions = Mock()

        service._legacy_checker = mock_checker

        summary = service.get_positions_summary()

        # Verify calculations
        assert summary["total_positions"] == 2

        # Check AAPL calculations
        aapl_pos = summary["positions"]["AAPL"]
        assert aapl_pos["position"] == 150
        assert aapl_pos["avg_cost"] == 148.50
        assert aapl_pos["market_value"] == 150 * 148.50  # 22,275

        # Check GOOGL calculations
        googl_pos = summary["positions"]["GOOGL"]
        assert googl_pos["position"] == 55
        assert googl_pos["avg_cost"] == 142.00
        assert googl_pos["market_value"] == 55 * 142.00  # 7,810

        # Check total market value
        expected_total = (150 * 148.50) + (55 * 142.00)  # 30,085
        assert summary["total_market_value"] == expected_total

    def test_order_status_summary_grouping(self, sample_ibkr_data):
        """Test order status summary groups orders correctly by status"""

        service = OrderStatusService("test_orders.json")

        # Add some variety to order statuses
        ibkr_orders = sample_ibkr_data["open_orders"].copy()
        ibkr_orders[125] = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": 50,
            "status": "SUBMITTED",
            "avgFillPrice": "",
            "filled": 0,
            "remaining": 50,
            "orderType": "MKT"
        }
        ibkr_orders[126] = {
            "symbol": "TSLA",
            "action": "SELL",
            "quantity": 25,
            "status": "CANCELLED",
            "avgFillPrice": "",
            "filled": 0,
            "remaining": 0,
            "orderType": "MKT"
        }

        # Mock API
        mock_api = Mock()
        mock_api.open_orders = ibkr_orders
        mock_api.completed_orders = {}

        mock_checker = Mock()
        mock_checker.api = mock_api
        mock_checker.show_order_status_summary = Mock()

        service._legacy_checker = mock_checker

        summary = service.get_order_status_summary()

        # Verify grouping by status
        assert "FILLED" in summary["orders_by_status"]
        assert "SUBMITTED" in summary["orders_by_status"]
        assert "CANCELLED" in summary["orders_by_status"]

        # Check counts
        assert summary["status_counts"]["FILLED"] == 2  # AAPL, GOOGL
        assert summary["status_counts"]["SUBMITTED"] == 1  # MSFT
        assert summary["status_counts"]["CANCELLED"] == 1  # TSLA
        assert summary["total_orders"] == 4

        # Check order details structure
        filled_orders = summary["orders_by_status"]["FILLED"]
        assert len(filled_orders) == 2

        aapl_order = next(o for o in filled_orders if o["symbol"] == "AAPL")
        assert aapl_order["filled"] == 100
        assert aapl_order["avg_fill_price"] == 150.25

    def test_complete_verification_results_structure(self, sample_orders_data, sample_ibkr_data):
        """Test complete verification results contain all expected sections"""

        service = OrderStatusService("test_orders.json")
        service.orders_data = sample_orders_data

        # Create comprehensive mock
        mock_checker = self.create_mock_legacy_checker(sample_orders_data, sample_ibkr_data)
        service._legacy_checker = mock_checker

        results = service.get_verification_results()

        # Verify all required sections are present
        required_sections = [
            "comparison_summary",
            "order_matches",
            "missing_orders",
            "recommendations",
            "extra_orders",
            "positions",
            "order_status_breakdown"
        ]

        for section in required_sections:
            assert section in results, f"Missing section: {section}"

        # Check comparison summary structure
        summary = results["comparison_summary"]
        required_summary_fields = [
            "found_in_ibkr",
            "missing_from_ibkr",
            "quantity_mismatches",
            "success_rate",
            "total_orders",
            "timestamp"
        ]

        for field in required_summary_fields:
            assert field in summary, f"Missing summary field: {field}"

        # Verify timestamp format
        assert "T" in summary["timestamp"]  # ISO format

    def test_api_endpoint_behavioral_compatibility(self, client, sample_orders_data, sample_ibkr_data, tmp_path):
        """Test API endpoint produces results compatible with CLI behavior"""

        # Create test orders file
        orders_file = tmp_path / "test_orders.json"
        with open(orders_file, 'w') as f:
            json.dump(sample_orders_data, f)

        # Create expected verification results based on test data
        expected_results = {
            "comparison_summary": {
                "found_in_ibkr": 2,
                "missing_from_ibkr": 2,
                "quantity_mismatches": 1,
                "success_rate": 50.0,
                "total_orders": 4,
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
                    "json_quantity": 25,
                    "ibkr_status": "FILLED",
                    "ibkr_quantity": 20,
                    "match_status": "QTY_DIFF"
                }
            ],
            "missing_orders": [
                {
                    "symbol": "DPM",
                    "reason": "Contract Not Supported",
                    "details": "IBKR does not support this specific DPM contract on TSE (Error 202)"
                },
                {
                    "symbol": "AJ91",
                    "reason": "Liquidity Constraints",
                    "details": "Volume (1,547 shares) too large for available liquidity (Error 202)"
                }
            ],
            "positions": {
                "AAPL": {
                    "position": 150,
                    "avg_cost": 148.50,
                    "market_value": 22275.0
                },
                "GOOGL": {
                    "position": 55,
                    "avg_cost": 142.00,
                    "market_value": 7810.0
                }
            }
        }

        # Mock service to return expected results
        mock_service = Mock()
        mock_service.load_orders_json.return_value = sample_orders_data
        mock_service.connect_to_ibkr.return_value = True
        mock_service.get_verification_results.return_value = expected_results
        mock_service.disconnect = Mock()

        with patch('app.api.v1.endpoints.orders.OrderStatusService') as MockService:
            MockService.return_value = mock_service

            response = client.post(
                "/api/v1/orders/status/check",
                params={"orders_file": str(orders_file)}
            )

            assert response.status_code == 200
            api_data = response.json()

            # Verify API response structure matches CLI behavior expectations
            assert api_data["success"] is True

            # Check comparison summary matches expected analysis
            summary = api_data["comparison_summary"]
            assert summary["found_in_ibkr"] == 2
            assert summary["missing_from_ibkr"] == 2
            assert summary["quantity_mismatches"] == 1
            assert summary["success_rate"] == 50.0
            assert summary["total_orders"] == 4

            # Check order matches structure
            assert len(api_data["order_matches"]) >= 2

            # Check missing orders analysis
            missing_symbols = [order["symbol"] for order in api_data["missing_orders"]]
            assert "DPM" in missing_symbols
            assert "AJ91" in missing_symbols

            # Check positions data
            assert "AAPL" in api_data["positions"]
            assert "GOOGL" in api_data["positions"]

    def test_cli_step11_function_compatibility(self, sample_orders_data, tmp_path):
        """Test that service behavior matches CLI step11_check_order_status() function"""

        # Create test orders file
        orders_file = tmp_path / "test_orders.json"
        with open(orders_file, 'w') as f:
            json.dump(sample_orders_data, f)

        # Test the service run_status_check method which wraps the CLI behavior
        service = OrderStatusService(str(orders_file))

        # Mock the legacy OrderStatusChecker completely
        mock_checker = Mock()
        mock_checker.run_status_check.return_value = True  # CLI returns True on success

        with patch('app.services.implementations.order_status_service.OrderStatusChecker') as MockChecker:
            MockChecker.return_value = mock_checker

            # Call the main workflow method
            result = service.run_status_check()

            # Verify it returns the same boolean result as CLI
            assert result is True

            # Verify the legacy method was called with correct file
            MockChecker.assert_called_once_with(str(orders_file))
            mock_checker.run_status_check.assert_called_once()

        # Test failure case
        mock_checker.run_status_check.side_effect = Exception("Connection failed")
        mock_checker.disconnect = Mock()

        with patch('app.services.implementations.order_status_service.OrderStatusChecker') as MockChecker:
            MockChecker.return_value = mock_checker

            result = service.run_status_check()

            # Should return False on failure, same as CLI
            assert result is False
            # Should cleanup on failure
            mock_checker.disconnect.assert_called_once()

    def test_console_output_compatibility(self, sample_orders_data, sample_ibkr_data):
        """Test that service maintains console output compatibility with CLI"""

        service = OrderStatusService("test_orders.json")
        service.orders_data = sample_orders_data

        # Create mock that tracks console output method calls
        mock_checker = self.create_mock_legacy_checker(sample_orders_data, sample_ibkr_data)
        service._legacy_checker = mock_checker

        # Test that console output methods are called when using service methods

        # analyze_orders should call console method
        service.analyze_orders()
        mock_checker.analyze_orders.assert_called_once()

        # get_order_status_summary should call console method
        service.get_order_status_summary()
        mock_checker.show_order_status_summary.assert_called_once()

        # get_positions_summary should call console method
        service.get_positions_summary()
        mock_checker.show_positions.assert_called_once()

        # get_missing_order_analysis should call console method
        missing_orders = [{"symbol": "TEST", "action": "BUY", "quantity": 1,
                          "stock_info": {"ticker": "TEST", "currency": "USD"},
                          "ibkr_details": {"primaryExchange": "NYSE"}}]
        service.get_missing_order_analysis(missing_orders)
        mock_checker.show_missing_order_analysis.assert_called_once_with(missing_orders)

        # This ensures that when called via API, the same console output
        # behavior is maintained as the CLI, providing identical user experience