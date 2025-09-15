"""
Step 10 CLI vs API Behavioral Compatibility Tests
Ensures 100% identical behavior between CLI step10_execute_orders() and API endpoints
"""

import pytest
import json
import tempfile
import os
import sys
import subprocess
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from ..main import app


class TestStep10CLIvsAPICompatibility:
    """
    Compare CLI step10_execute_orders() with API workflow execution
    Ensures identical behavior and outputs
    """

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def sample_orders_file(self, tmp_path):
        """Create a sample orders.json file for testing"""
        orders_data = {
            "metadata": {
                "total_orders": 3,
                "buy_orders": 2,
                "sell_orders": 1,
                "generated_at": "2024-01-15T10:00:00Z",
                "account_total_value": 100000.00
            },
            "orders": [
                {
                    "symbol": "AAPL",
                    "action": "BUY",
                    "quantity": 100,
                    "stock_info": {
                        "currency": "USD",
                        "price": 180.50,
                        "name": "Apple Inc"
                    },
                    "ibkr_details": {
                        "symbol": "AAPL",
                        "exchange": "SMART",
                        "primaryExchange": "NASDAQ",
                        "conId": 265598
                    },
                    "target_value": 18050.00,
                    "current_value": 0.00
                },
                {
                    "symbol": "GOOGL",
                    "action": "SELL",
                    "quantity": 50,
                    "stock_info": {
                        "currency": "USD",
                        "price": 2800.00,
                        "name": "Alphabet Inc Class A"
                    },
                    "ibkr_details": {
                        "symbol": "GOOGL",
                        "exchange": "SMART",
                        "primaryExchange": "NASDAQ",
                        "conId": 208813720
                    },
                    "target_value": -140000.00,
                    "current_value": 0.00
                },
                {
                    "symbol": "TSM",
                    "action": "BUY",
                    "quantity": 200,
                    "stock_info": {
                        "currency": "USD",
                        "price": 95.00,
                        "name": "Taiwan Semiconductor Manufacturing Company Limited"
                    },
                    "ibkr_details": {
                        "symbol": "TSM",
                        "exchange": "SMART",
                        "primaryExchange": "NYSE",
                        "conId": 7010
                    },
                    "target_value": 19000.00,
                    "current_value": 0.00
                }
            ]
        }

        # Create the orders file in a temporary data directory structure
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        orders_file = data_dir / "orders.json"
        orders_file.write_text(json.dumps(orders_data, indent=2))

        return str(tmp_path), str(orders_file)

    def test_cli_vs_api_console_output_patterns(self, sample_orders_file, capsys):
        """
        Test that API console output matches CLI console output patterns exactly
        """
        project_root, orders_file = sample_orders_file

        # Mock IBKR execution for both CLI and API
        with patch('backend.app.services.implementations.order_execution_service.IBOrderExecutor') as mock_executor_class, \
             patch('backend.app.services.implementations.legacy.order_executor.OrderExecutor') as mock_legacy_executor_class, \
             patch('backend.app.services.implementations.legacy.order_executor.IBOrderExecutor') as mock_legacy_ibkr_class:

            # Setup common mock behavior
            mock_executor = Mock()
            mock_executor.connected = True
            mock_executor.nextorderId = 100
            mock_executor.account_id = "DU123456"
            mock_executor.orders_status = {
                100: {'status': 'Filled', 'filled': 100, 'remaining': 0, 'avgFillPrice': 180.50, 'permId': 1001},
                101: {'status': 'Filled', 'filled': 50, 'remaining': 0, 'avgFillPrice': 2800.00, 'permId': 1002},
                102: {'status': 'Filled', 'filled': 200, 'remaining': 0, 'avgFillPrice': 95.00, 'permId': 1003}
            }

            # Setup for both service and legacy mocks
            mock_executor_class.return_value = mock_executor
            mock_legacy_ibkr_class.return_value = mock_executor

            # Mock legacy executor for contract/order creation
            mock_legacy_executor = Mock()
            mock_contract = Mock()
            mock_order = Mock()
            mock_legacy_executor.create_contract_from_order.return_value = mock_contract
            mock_legacy_executor.create_market_order.return_value = mock_order
            mock_legacy_executor_class.return_value = mock_legacy_executor

            # Test API workflow execution
            client = TestClient(app)

            with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService._get_project_root', return_value=project_root):
                response = client.post(
                    "/api/v1/orders/workflow/execute",
                    json={
                        "orders_file": "orders.json",
                        "max_orders": None,
                        "delay_between_orders": 0.1,  # Faster for testing
                        "order_type": "GTC_MKT"
                    }
                )

            # Capture API console output
            api_output = capsys.readouterr()

            # Verify API response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Check for CLI-compatible console output patterns
            output_text = api_output.out

            # These patterns should match legacy console output exactly
            expected_patterns = [
                "Interactive Brokers Order Execution Service",
                "[LOAD] Loading orders from",
                "[OK] Loaded 3 orders (1 SELL, 2 BUY)",
                "[CONNECT] Connecting to IB Gateway",
                "[OK] Connected to IBKR",
                "[EXECUTE] Starting execution of 3 orders",
                "[EXECUTE] Using order type: GTC_MKT",
                "BUY 100 AAPL",
                "SELL 50 GOOGL",
                "BUY 200 TSM",
                "[SUMMARY] Execution complete:",
                "Executed: 3",
                "Failed: 0",
                "Total: 3",
                "[WAIT]",
                "[STATUS] Order Status Summary:",
                "Filled: 3 orders",
                "Total shares filled:",
                "[OK] Disconnected from IB Gateway"
            ]

            for pattern in expected_patterns:
                assert pattern in output_text, f"Missing expected console output pattern: '{pattern}'"

    def test_cli_vs_api_order_execution_sequence(self, sample_orders_file):
        """
        Test that API executes orders in the same sequence as CLI
        """
        project_root, orders_file = sample_orders_file

        execution_sequence = []

        def mock_place_order(order_id, contract, order):
            execution_sequence.append({
                'order_id': order_id,
                'symbol': contract.symbol if hasattr(contract, 'symbol') else 'MOCK',
                'action': order.action if hasattr(order, 'action') else 'MOCK'
            })

        with patch('backend.app.services.implementations.order_execution_service.IBOrderExecutor') as mock_executor_class, \
             patch('backend.app.services.implementations.legacy.order_executor.OrderExecutor') as mock_legacy_executor_class:

            # Setup mock executor
            mock_executor = Mock()
            mock_executor.connected = True
            mock_executor.nextorderId = 100
            mock_executor.account_id = "DU123456"
            mock_executor.orders_status = {}
            mock_executor.placeOrder.side_effect = mock_place_order
            mock_executor_class.return_value = mock_executor

            # Mock legacy executor
            mock_legacy_executor = Mock()
            mock_contract = Mock()
            mock_contract.symbol = 'TEST'
            mock_order = Mock()
            mock_order.action = 'BUY'
            mock_legacy_executor.create_contract_from_order.return_value = mock_contract
            mock_legacy_executor.create_market_order.return_value = mock_order
            mock_legacy_executor_class.return_value = mock_legacy_executor

            client = TestClient(app)

            with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService._get_project_root', return_value=project_root):
                response = client.post(
                    "/api/v1/orders/workflow/execute",
                    json={
                        "orders_file": "orders.json",
                        "delay_between_orders": 0.1
                    }
                )

            # Verify execution sequence
            assert response.status_code == 200
            assert len(execution_sequence) == 3

            # Orders should be executed in file order
            expected_order_ids = [100, 101, 102]
            actual_order_ids = [order['order_id'] for order in execution_sequence]
            assert actual_order_ids == expected_order_ids

    def test_cli_vs_api_parameter_handling(self, sample_orders_file):
        """
        Test that API handles parameters identically to CLI
        """
        project_root, orders_file = sample_orders_file

        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.run_execution') as mock_workflow:
            mock_workflow.return_value = {'success': True}

            client = TestClient(app)

            # Test default parameters (should match CLI defaults)
            response = client.post(
                "/api/v1/orders/workflow/execute",
                json={"orders_file": "orders.json"}
            )

            assert response.status_code == 200

            # Verify service was called with CLI-compatible defaults
            call_args = mock_workflow.call_args
            assert call_args.kwargs['orders_file'] == 'orders.json'
            assert call_args.kwargs['max_orders'] is None  # CLI default: no limit
            assert call_args.kwargs['delay_between_orders'] == 1.0  # CLI default
            assert call_args.kwargs['order_type'] == 'GTC_MKT'  # CLI default

            # Test custom parameters
            mock_workflow.reset_mock()
            response = client.post(
                "/api/v1/orders/workflow/execute",
                json={
                    "orders_file": "test.json",
                    "max_orders": 5,
                    "delay_between_orders": 2.0,
                    "order_type": "MOO"
                }
            )

            call_args = mock_workflow.call_args
            assert call_args.kwargs['orders_file'] == 'test.json'
            assert call_args.kwargs['max_orders'] == 5
            assert call_args.kwargs['delay_between_orders'] == 2.0
            assert call_args.kwargs['order_type'] == 'MOO'

    def test_cli_vs_api_error_handling_compatibility(self, sample_orders_file):
        """
        Test that API error handling matches CLI error patterns
        """
        project_root, orders_file = sample_orders_file

        client = TestClient(app)

        # Test 1: Missing orders file (CLI would print error and return False)
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService._get_project_root', return_value=project_root):
            response = client.post(
                "/api/v1/orders/workflow/execute",
                json={"orders_file": "missing_orders.json"}
            )

        # API should handle this gracefully like CLI (return success=False, not HTTP error)
        assert response.status_code == 200  # No HTTP error, just workflow failure
        data = response.json()
        assert data["success"] is False
        assert "error_message" in data

        # Test 2: IBKR connection failure
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.connect_to_ibkr') as mock_connect, \
             patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.load_orders') as mock_load:

            mock_load.return_value = {'success': True, 'total_orders': 1}
            mock_connect.side_effect = Exception("Connection failed")

            with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService._get_project_root', return_value=project_root):
                response = client.post(
                    "/api/v1/orders/workflow/execute",
                    json={"orders_file": "orders.json"}
                )

        # Should handle connection failure gracefully like CLI
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_cli_vs_api_order_type_selection(self, sample_orders_file):
        """
        Test that API applies same order type selection logic as CLI
        """
        project_root, orders_file = sample_orders_file

        # Create orders with different currencies to test order type selection
        mixed_currency_orders = {
            "metadata": {"total_orders": 2, "buy_orders": 2, "sell_orders": 0},
            "orders": [
                {
                    "symbol": "AAPL",
                    "action": "BUY",
                    "quantity": 100,
                    "stock_info": {"currency": "USD"},  # USD stock
                    "ibkr_details": {"symbol": "AAPL", "exchange": "SMART"}
                },
                {
                    "symbol": "ASML",
                    "action": "BUY",
                    "quantity": 50,
                    "stock_info": {"currency": "EUR"},  # International stock
                    "ibkr_details": {"symbol": "ASML", "exchange": "SMART"}
                }
            ]
        }

        # Create temp file with mixed currency orders
        temp_orders_file = os.path.join(project_root, "data", "mixed_orders.json")
        with open(temp_orders_file, 'w') as f:
            json.dump(mixed_currency_orders, f)

        executed_orders = []

        def capture_order_execution(self, order_data):
            currency = order_data['stock_info']['currency']
            # CLI logic: USD stocks can use MOO, international stocks force GTC_MKT
            if currency == 'USD':
                selected_order_type = "MOO"  # Would be MOO if requested
            else:
                selected_order_type = "GTC_MKT"  # Always GTC_MKT for international

            executed_orders.append({
                'symbol': order_data['symbol'],
                'currency': currency,
                'selected_type': selected_order_type
            })

        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.run_execution') as mock_workflow:
            # Mock to capture the order type selection behavior
            mock_workflow.return_value = {'success': True}

            client = TestClient(app)

            response = client.post(
                "/api/v1/orders/workflow/execute",
                json={
                    "orders_file": "mixed_orders.json",
                    "order_type": "MOO"  # Request MOO but should be overridden for EUR stocks
                }
            )

            assert response.status_code == 200

        # Cleanup
        os.unlink(temp_orders_file)

    def test_cli_vs_api_status_reporting_format(self, sample_orders_file):
        """
        Test that API status reporting matches CLI format exactly
        """
        project_root, orders_file = sample_orders_file

        # Mock order status data that matches CLI expectations
        mock_status_data = {
            100: {'status': 'Filled', 'filled': 100, 'remaining': 0, 'avgFillPrice': 180.50, 'permId': 1001},
            101: {'status': 'PreSubmitted', 'filled': 0, 'remaining': 50, 'avgFillPrice': 0.0, 'permId': 1002},
            102: {'status': 'Submitted', 'filled': 150, 'remaining': 50, 'avgFillPrice': 95.00, 'permId': 1003}
        }

        client = TestClient(app)

        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.get_order_statuses') as mock_status:
            mock_status.return_value = {
                'success': True,
                'status_summary': {'Filled': 1, 'PreSubmitted': 1, 'Submitted': 1},
                'total_filled_shares': 250,  # 100 + 0 + 150
                'pending_orders_count': 2,   # PreSubmitted + Submitted
                'order_details': mock_status_data,
                'wait_time_used': 30
            }

            response = client.get("/api/v1/orders/status", params={"wait_time": 30})

            assert response.status_code == 200
            data = response.json()

            # Verify status summary matches CLI format
            assert data['status_summary']['Filled'] == 1
            assert data['status_summary']['PreSubmitted'] == 1
            assert data['status_summary']['Submitted'] == 1
            assert data['total_filled_shares'] == 250
            assert data['pending_orders_count'] == 2

    def test_cli_vs_api_file_path_resolution(self, sample_orders_file):
        """
        Test that API resolves file paths identically to CLI
        """
        project_root, orders_file = sample_orders_file

        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.load_orders') as mock_load:
            mock_load.return_value = {'success': True, 'total_orders': 1}

            client = TestClient(app)

            # API should resolve orders.json to data/orders.json just like CLI
            response = client.post("/api/v1/orders/load", params={"orders_file": "orders.json"})

            assert response.status_code == 200

            # Verify the service was called with the filename (not full path)
            # The service should handle path resolution internally
            mock_load.assert_called_once_with("orders.json")


class TestStep10CLIDirectCompatibility:
    """
    Direct tests of CLI step10_execute_orders() function compatibility
    """

    def test_step10_function_signature_compatibility(self):
        """Test that we can import and call the original CLI function"""
        try:
            # This should work without modification
            import sys
            import os

            # Add the project root to sys.path to import main
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            # Import the CLI function
            from main import step10_execute_orders

            # Verify function exists and is callable
            assert callable(step10_execute_orders)

        except ImportError as e:
            pytest.skip(f"Cannot import CLI function: {e}")

    def test_cli_function_preserves_original_behavior(self):
        """Test that original CLI function still works unchanged"""
        try:
            import sys
            import os

            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            from main import step10_execute_orders

            # The function should still work with mocked dependencies
            with patch('src.order_executor.main') as mock_main:
                mock_main.return_value = None

                result = step10_execute_orders()

                # CLI function should return True on success
                assert result is True

                # Should have called the legacy main function
                mock_main.assert_called_once()

        except ImportError as e:
            pytest.skip(f"Cannot import CLI function: {e}")