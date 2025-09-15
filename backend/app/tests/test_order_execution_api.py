"""
API endpoint tests for Order Execution Service
Tests REST API functionality and CLI compatibility
"""

import pytest
import json
import tempfile
import os
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from ..main import app
from ..services.implementations.order_execution_service import OrderExecutionError, IBKRConnectionError


class TestOrderExecutionAPI:
    """
    Test Order Execution API endpoints
    """

    @pytest.fixture
    def client(self):
        """FastAPI test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_orders_data(self):
        """Sample orders data for API testing"""
        return {
            "metadata": {
                "total_orders": 2,
                "buy_orders": 1,
                "sell_orders": 1
            },
            "orders": [
                {
                    "symbol": "AAPL",
                    "action": "BUY",
                    "quantity": 100,
                    "stock_info": {"currency": "USD"},
                    "ibkr_details": {
                        "symbol": "AAPL",
                        "exchange": "SMART",
                        "primaryExchange": "NASDAQ",
                        "conId": 265598
                    }
                },
                {
                    "symbol": "GOOGL",
                    "action": "SELL",
                    "quantity": 50,
                    "stock_info": {"currency": "USD"},
                    "ibkr_details": {
                        "symbol": "GOOGL",
                        "exchange": "SMART",
                        "primaryExchange": "NASDAQ",
                        "conId": 208813720
                    }
                }
            ]
        }

    @pytest.fixture
    def temp_orders_file(self, mock_orders_data):
        """Create temporary orders file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(mock_orders_data, f)
            temp_file = f.name

        yield os.path.basename(temp_file)

        # Cleanup
        try:
            os.unlink(temp_file)
        except FileNotFoundError:
            pass

    def test_health_check(self, client):
        """Test order execution service health endpoint"""
        response = client.get("/api/v1/orders/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Order Execution Service"
        assert "endpoints" in data
        assert "dependencies" in data

    def test_load_orders_success(self, client, temp_orders_file):
        """Test successful order loading via API"""
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.load_orders') as mock_load:
            mock_load.return_value = {
                'success': True,
                'metadata': {'total_orders': 2, 'buy_orders': 1, 'sell_orders': 1},
                'orders': [],
                'total_orders': 2
            }

            response = client.post(
                "/api/v1/orders/load",
                params={"orders_file": "test_orders.json"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["total_orders"] == 2
            assert data["orders_file"] == "test_orders.json"

    def test_load_orders_file_not_found(self, client):
        """Test load orders with missing file"""
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.load_orders') as mock_load:
            mock_load.side_effect = OrderExecutionError(
                message="Orders file not found",
                error_code="ORDERS_FILE_NOT_FOUND"
            )

            response = client.post(
                "/api/v1/orders/load",
                params={"orders_file": "missing.json"}
            )

            assert response.status_code == 400
            data = response.json()
            assert "error_code" in data
            assert data["error_code"] == "ORDERS_FILE_NOT_FOUND"

    def test_connect_to_ibkr_success(self, client):
        """Test successful IBKR connection via API"""
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.connect_to_ibkr') as mock_connect:
            mock_connect.return_value = True

            connection_data = {
                "host": "127.0.0.1",
                "port": 4002,
                "client_id": 20,
                "timeout": 15
            }

            response = client.post(
                "/api/v1/orders/connection/connect",
                json=connection_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "connection_details" in data

    def test_connect_to_ibkr_failure(self, client):
        """Test IBKR connection failure via API"""
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.connect_to_ibkr') as mock_connect:
            mock_connect.side_effect = IBKRConnectionError(
                message="Failed to connect to IBKR Gateway",
                error_code="IBKR_CONNECTION_FAILED"
            )

            response = client.post("/api/v1/orders/connection/connect", json={})

            assert response.status_code == 503
            data = response.json()
            assert "error_code" in data
            assert data["error_code"] == "IBKR_CONNECTION_FAILED"

    def test_execute_orders_success(self, client):
        """Test successful order execution via API"""
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.load_orders') as mock_load, \
             patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.execute_orders') as mock_execute:

            mock_load.return_value = {
                'success': True,
                'metadata': {'total_orders': 2},
                'orders': [],
                'total_orders': 2
            }

            mock_execute.return_value = {
                'success': True,
                'executed_count': 2,
                'failed_count': 0,
                'total_orders': 2,
                'order_statuses': {},
                'order_results': [],
                'execution_summary': {
                    'total_processed': 2,
                    'successful_submissions': 2,
                    'failed_submissions': 0,
                    'success_rate': 1.0
                }
            }

            execution_request = {
                "orders_file": "test_orders.json",
                "max_orders": 10,
                "delay_between_orders": 1.0,
                "order_type": "GTC_MKT"
            }

            response = client.post(
                "/api/v1/orders/execute",
                json=execution_request
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["executed_count"] == 2
            assert data["failed_count"] == 0
            assert data["execution_summary"]["success_rate"] == 1.0

    def test_execute_orders_validation_error(self, client):
        """Test order execution with invalid request data"""
        invalid_request = {
            "orders_file": "test.json",
            "max_orders": -1,  # Invalid: must be >= 1
            "delay_between_orders": 15.0,  # Invalid: must be <= 10.0
            "order_type": "INVALID_TYPE"
        }

        response = client.post(
            "/api/v1/orders/execute",
            json=invalid_request
        )

        assert response.status_code == 422  # Validation error

    def test_get_order_status_success(self, client):
        """Test successful order status retrieval via API"""
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.get_order_statuses') as mock_status:
            mock_status.return_value = {
                'success': True,
                'status_summary': {'Filled': 2},
                'total_filled_shares': 150,
                'pending_orders_count': 0,
                'order_details': {},
                'wait_time_used': 30
            }

            response = client.get(
                "/api/v1/orders/status",
                params={"wait_time": 30}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["total_filled_shares"] == 150
            assert data["pending_orders_count"] == 0

    def test_disconnect_success(self, client):
        """Test successful IBKR disconnection via API"""
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.disconnect') as mock_disconnect:
            mock_disconnect.return_value = None

            response = client.post("/api/v1/orders/connection/disconnect")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_workflow_execute_success(self, client):
        """Test complete workflow execution via API"""
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.run_execution') as mock_workflow:
            mock_workflow.return_value = {
                'success': True,
                'execution_summary': {
                    'total_processed': 2,
                    'successful_submissions': 2,
                    'failed_submissions': 0,
                    'success_rate': 1.0
                },
                'order_statuses': {},
                'status_summary': {'Filled': 2},
                'total_filled_shares': 150,
                'pending_orders_count': 0,
                'orders_loaded': 2,
                'workflow_completed_at': '2024-01-15T10:30:00Z'
            }

            workflow_request = {
                "orders_file": "orders.json",
                "order_type": "GTC_MKT"
            }

            response = client.post(
                "/api/v1/orders/workflow/execute",
                json=workflow_request
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["orders_loaded"] == 2
            assert data["execution_summary"]["success_rate"] == 1.0

    def test_workflow_execute_failure(self, client):
        """Test workflow execution failure via API"""
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.run_execution') as mock_workflow:
            mock_workflow.return_value = {
                'success': False,
                'error_message': 'Orders file not found',
                'execution_summary': None,
                'order_statuses': None,
                'failure_time': '2024-01-15T10:30:00Z'
            }

            workflow_request = {
                "orders_file": "missing.json"
            }

            response = client.post(
                "/api/v1/orders/workflow/execute",
                json=workflow_request
            )

            assert response.status_code == 200  # Workflow handles errors internally
            data = response.json()
            assert data["success"] is False
            assert "error_message" in data

    def test_get_contract_specification(self, client):
        """Test contract specification endpoint"""
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.create_ibkr_contract') as mock_contract:
            mock_contract.return_value = {
                'symbol': 'AAPL',
                'secType': 'STK',
                'exchange': 'SMART',
                'primaryExchange': 'NASDAQ',
                'currency': 'USD',
                'conId': 265598
            }

            response = client.get("/api/v1/orders/contract/AAPL")

            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "AAPL"
            assert data["sec_type"] == "STK"
            assert data["exchange"] == "SMART"
            assert data["currency"] == "USD"

    def test_create_order_specification(self, client):
        """Test order specification endpoint"""
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.create_ibkr_order') as mock_order:
            mock_order.return_value = {
                'action': 'BUY',
                'totalQuantity': 100,
                'orderType': 'MKT',
                'tif': 'GTC',
                'eTradeOnly': False,
                'firmQuoteOnly': False
            }

            response = client.post(
                "/api/v1/orders/order-spec",
                params={
                    "action": "BUY",
                    "quantity": 100,
                    "order_type": "GTC_MKT"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["action"] == "BUY"
            assert data["total_quantity"] == 100
            assert data["order_type"] == "MKT"
            assert data["tif"] == "GTC"

    def test_create_order_specification_invalid_action(self, client):
        """Test order specification with invalid action"""
        response = client.post(
            "/api/v1/orders/order-spec",
            params={
                "action": "INVALID",
                "quantity": 100
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "INVALID_ORDER_ACTION"

    def test_create_order_specification_invalid_quantity(self, client):
        """Test order specification with invalid quantity"""
        response = client.post(
            "/api/v1/orders/order-spec",
            params={
                "action": "BUY",
                "quantity": 0
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "INVALID_ORDER_QUANTITY"


class TestOrderExecutionAPICompatibility:
    """
    Test API compatibility with CLI behavior
    Ensures API endpoints produce identical results to CLI commands
    """

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_api_workflow_matches_cli_step10(self, client):
        """
        Test that API workflow endpoint produces results equivalent to:
        python main.py 10
        """
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.run_execution') as mock_workflow:
            # Mock the exact same result structure that CLI step10_execute_orders() would produce
            cli_equivalent_result = {
                'success': True,
                'execution_summary': {
                    'total_processed': 3,
                    'successful_submissions': 3,
                    'failed_submissions': 0,
                    'success_rate': 1.0
                },
                'order_statuses': {
                    '100': {'status': 'Filled', 'filled': 100, 'remaining': 0, 'avgFillPrice': 180.50},
                    '101': {'status': 'Filled', 'filled': 50, 'remaining': 0, 'avgFillPrice': 2800.00},
                    '102': {'status': 'Filled', 'filled': 200, 'remaining': 0, 'avgFillPrice': 95.00}
                },
                'status_summary': {'Filled': 3},
                'total_filled_shares': 350,
                'pending_orders_count': 0,
                'orders_loaded': 3,
                'workflow_completed_at': '2024-01-15T10:30:00Z'
            }
            mock_workflow.return_value = cli_equivalent_result

            # API call with same default parameters as CLI
            response = client.post(
                "/api/v1/orders/workflow/execute",
                json={
                    "orders_file": "orders.json",
                    "order_type": "GTC_MKT",
                    "delay_between_orders": 1.0
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Verify API response structure matches CLI expectations
            assert data["success"] is True
            assert data["execution_summary"]["success_rate"] == 1.0
            assert data["total_filled_shares"] == 350
            assert data["pending_orders_count"] == 0

    def test_api_error_responses_match_cli_errors(self, client):
        """Test that API error responses match CLI error patterns"""
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.run_execution') as mock_workflow:
            # Mock the same error that CLI would encounter
            mock_workflow.return_value = {
                'success': False,
                'error_message': 'Orders file not found: data/missing_orders.json',
                'execution_summary': None,
                'order_statuses': None,
                'failure_time': '2024-01-15T10:30:00Z'
            }

            response = client.post(
                "/api/v1/orders/workflow/execute",
                json={"orders_file": "missing_orders.json"}
            )

            assert response.status_code == 200  # Workflow handles errors internally
            data = response.json()
            assert data["success"] is False
            assert "Orders file not found" in data["error_message"]

    def test_api_parameter_defaults_match_cli(self, client):
        """Test that API parameter defaults match CLI defaults"""
        with patch('backend.app.services.implementations.order_execution_service.OrderExecutionService.run_execution') as mock_workflow:
            mock_workflow.return_value = {'success': True}

            # Test with minimal parameters (should use same defaults as CLI)
            response = client.post(
                "/api/v1/orders/workflow/execute",
                json={"orders_file": "orders.json"}
            )

            # Verify service was called with CLI-equivalent defaults
            mock_workflow.assert_called_once_with(
                orders_file="orders.json",
                max_orders=None,  # CLI default: no limit
                delay_between_orders=1.0,  # CLI default: 1.0 second
                order_type="GTC_MKT"  # CLI default: GTC_MKT
            )

    def test_api_validation_enforces_cli_constraints(self, client):
        """Test that API validation enforces same constraints as CLI"""
        # Test max_orders validation (must be positive)
        response = client.post(
            "/api/v1/orders/workflow/execute",
            json={
                "orders_file": "orders.json",
                "max_orders": -1
            }
        )
        assert response.status_code == 422

        # Test delay_between_orders validation (must be reasonable)
        response = client.post(
            "/api/v1/orders/workflow/execute",
            json={
                "orders_file": "orders.json",
                "delay_between_orders": 100.0  # Too high
            }
        )
        assert response.status_code == 422

        # Test order_type validation (must be valid enum)
        response = client.post(
            "/api/v1/orders/workflow/execute",
            json={
                "orders_file": "orders.json",
                "order_type": "INVALID_TYPE"
            }
        )
        assert response.status_code == 422


class TestOrderExecutionAPIDocumentation:
    """Test API documentation and OpenAPI compliance"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_openapi_schema_generation(self, client):
        """Test that OpenAPI schema is properly generated"""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert "paths" in schema

        # Verify order execution endpoints are documented
        order_paths = [path for path in schema["paths"].keys() if "/orders/" in path]
        assert len(order_paths) > 0

        # Check specific endpoints
        expected_endpoints = [
            "/api/v1/orders/load",
            "/api/v1/orders/connection/connect",
            "/api/v1/orders/execute",
            "/api/v1/orders/status",
            "/api/v1/orders/workflow/execute"
        ]

        for endpoint in expected_endpoints:
            assert endpoint in schema["paths"], f"Missing endpoint: {endpoint}"

    def test_endpoint_documentation_completeness(self, client):
        """Test that all endpoints have proper documentation"""
        response = client.get("/openapi.json")
        schema = response.json()

        # Check that order execution endpoints have proper documentation
        workflow_endpoint = schema["paths"]["/api/v1/orders/workflow/execute"]["post"]
        assert "summary" in workflow_endpoint
        assert "description" in workflow_endpoint
        assert "Complete order execution workflow" in workflow_endpoint["summary"]

    def test_api_docs_accessibility(self, client):
        """Test that API documentation is accessible"""
        # Test Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200

        # Test ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200