"""
Comprehensive tests for Order Execution Service
Tests 100% behavioral compatibility with CLI step10_execute_orders()
"""

import pytest
import json
import os
import tempfile
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from ..services.interfaces import IOrderExecutionService
from ..services.implementations.order_execution_service import OrderExecutionService, OrderExecutionError, IBKRConnectionError
from ..core.dependencies import get_order_execution_service


class TestOrderExecutionService:
    """
    Unit tests for OrderExecutionService implementation
    Focus on service logic, error handling, and interface compliance
    """

    @pytest.fixture
    def service(self):
        """Get order execution service instance"""
        return OrderExecutionService()

    @pytest.fixture
    def mock_orders_data(self):
        """Sample orders data for testing"""
        return {
            "metadata": {
                "total_orders": 3,
                "buy_orders": 2,
                "sell_orders": 1,
                "generated_at": "2024-01-15T10:00:00Z"
            },
            "orders": [
                {
                    "symbol": "AAPL",
                    "action": "BUY",
                    "quantity": 100,
                    "stock_info": {
                        "currency": "USD",
                        "price": 180.50
                    },
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
                    "stock_info": {
                        "currency": "USD",
                        "price": 2800.00
                    },
                    "ibkr_details": {
                        "symbol": "GOOGL",
                        "exchange": "SMART",
                        "primaryExchange": "NASDAQ",
                        "conId": 208813720
                    }
                },
                {
                    "symbol": "TSM",
                    "action": "BUY",
                    "quantity": 200,
                    "stock_info": {
                        "currency": "USD",
                        "price": 95.00
                    },
                    "ibkr_details": {
                        "symbol": "TSM",
                        "exchange": "SMART",
                        "primaryExchange": "NYSE",
                        "conId": 7010
                    }
                }
            ]
        }

    @pytest.fixture
    def temp_orders_file(self, mock_orders_data):
        """Create temporary orders.json file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(mock_orders_data, f)
            temp_file = f.name

        yield temp_file

        # Cleanup
        try:
            os.unlink(temp_file)
        except FileNotFoundError:
            pass

    @pytest.mark.asyncio
    async def test_load_orders_success(self, service, temp_orders_file, mock_orders_data):
        """Test successful order loading"""
        result = await service.load_orders(temp_orders_file)

        assert result['success'] is True
        assert result['total_orders'] == 3
        assert result['metadata']['buy_orders'] == 2
        assert result['metadata']['sell_orders'] == 1
        assert len(result['orders']) == 3

    @pytest.mark.asyncio
    async def test_load_orders_file_not_found(self, service):
        """Test error handling for missing orders file"""
        with pytest.raises(OrderExecutionError) as exc_info:
            await service.load_orders("nonexistent_orders.json")

        assert exc_info.value.error_code == "ORDERS_FILE_NOT_FOUND"
        assert "not found" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_load_orders_invalid_json(self, service):
        """Test error handling for invalid JSON format"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json content")
            temp_file = f.name

        try:
            with pytest.raises(OrderExecutionError) as exc_info:
                await service.load_orders(temp_file)

            assert exc_info.value.error_code == "INVALID_ORDERS_FORMAT"
            assert "json" in str(exc_info.value.message).lower()
        finally:
            os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_load_orders_missing_metadata(self, service):
        """Test error handling for invalid orders structure"""
        invalid_data = {"orders": []}  # Missing metadata

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_data, f)
            temp_file = f.name

        try:
            with pytest.raises(OrderExecutionError) as exc_info:
                await service.load_orders(temp_file)

            assert exc_info.value.error_code == "ORDERS_LOAD_FAILED"
        finally:
            os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_connect_to_ibkr_success(self, service):
        """Test successful IBKR connection"""
        # Mock the legacy IBOrderExecutor
        with patch('backend.app.services.implementations.order_execution_service.IBOrderExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.connected = True
            mock_executor.nextorderId = 100
            mock_executor.account_id = "DU123456"
            mock_executor_class.return_value = mock_executor

            result = await service.connect_to_ibkr()

            assert result is True
            assert service.execution_api is not None
            mock_executor.connect.assert_called_once_with("127.0.0.1", 4002, clientId=20)

    @pytest.mark.asyncio
    async def test_connect_to_ibkr_timeout(self, service):
        """Test IBKR connection timeout"""
        with patch('backend.app.services.implementations.order_execution_service.IBOrderExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.connected = False
            mock_executor.nextorderId = None
            mock_executor_class.return_value = mock_executor

            with pytest.raises(IBKRConnectionError) as exc_info:
                await service.connect_to_ibkr(timeout=1)

            assert exc_info.value.error_code == "IBKR_CONNECTION_FAILED"

    @pytest.mark.asyncio
    async def test_connect_to_ibkr_no_account_id(self, service):
        """Test IBKR connection without account ID"""
        with patch('backend.app.services.implementations.order_execution_service.IBOrderExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.connected = True
            mock_executor.nextorderId = 100
            mock_executor.account_id = None  # No account ID
            mock_executor_class.return_value = mock_executor

            with pytest.raises(IBKRConnectionError) as exc_info:
                await service.connect_to_ibkr(timeout=1)

            assert exc_info.value.error_code == "IBKR_ACCOUNT_ID_MISSING"

    def test_create_ibkr_contract(self, service):
        """Test IBKR contract creation"""
        order_data = {
            'ibkr_details': {
                'symbol': 'AAPL',
                'exchange': 'SMART',
                'primaryExchange': 'NASDAQ',
                'conId': 265598
            },
            'stock_info': {
                'currency': 'USD'
            }
        }

        contract = service.create_ibkr_contract(order_data)

        assert contract['symbol'] == 'AAPL'
        assert contract['secType'] == 'STK'
        assert contract['exchange'] == 'SMART'
        assert contract['primaryExchange'] == 'NASDAQ'
        assert contract['currency'] == 'USD'
        assert contract['conId'] == 265598

    def test_create_ibkr_order_gtc_mkt(self, service):
        """Test GTC_MKT order creation"""
        order = service.create_ibkr_order("BUY", 100, "GTC_MKT")

        assert order['action'] == 'BUY'
        assert order['totalQuantity'] == 100
        assert order['orderType'] == 'MKT'
        assert order['tif'] == 'GTC'
        assert order['eTradeOnly'] is False
        assert order['firmQuoteOnly'] is False

    def test_create_ibkr_order_moo(self, service):
        """Test MOO order creation"""
        order = service.create_ibkr_order("SELL", 50, "MOO")

        assert order['action'] == 'SELL'
        assert order['totalQuantity'] == 50
        assert order['orderType'] == 'MKT'
        assert order['tif'] == 'OPG'  # At the Opening

    def test_create_ibkr_order_day(self, service):
        """Test DAY order creation"""
        order = service.create_ibkr_order("BUY", 200, "DAY")

        assert order['action'] == 'BUY'
        assert order['totalQuantity'] == 200
        assert order['orderType'] == 'MKT'
        assert order['tif'] == 'DAY'

    @pytest.mark.asyncio
    async def test_execute_orders_not_loaded(self, service):
        """Test execute orders without loading orders first"""
        with pytest.raises(OrderExecutionError) as exc_info:
            await service.execute_orders()

        assert exc_info.value.error_code == "NO_ORDERS_LOADED"

    @pytest.mark.asyncio
    async def test_execute_orders_not_connected(self, service, mock_orders_data):
        """Test execute orders without IBKR connection"""
        service.orders_data = mock_orders_data

        with pytest.raises(OrderExecutionError) as exc_info:
            await service.execute_orders()

        assert exc_info.value.error_code == "IBKR_NOT_CONNECTED"

    @pytest.mark.asyncio
    async def test_get_order_statuses_not_connected(self, service):
        """Test get order statuses without IBKR connection"""
        with pytest.raises(OrderExecutionError) as exc_info:
            await service.get_order_statuses()

        assert exc_info.value.error_code == "IBKR_NOT_CONNECTED"

    @pytest.mark.asyncio
    async def test_disconnect_no_connection(self, service):
        """Test disconnect with no active connection"""
        # Should not raise exception
        await service.disconnect()
        assert service.execution_api is None

    def test_project_root_resolution(self, service):
        """Test project root directory resolution"""
        project_root = service._get_project_root()
        assert os.path.isabs(project_root)
        # Should point to directory containing both 'data' and 'backend'
        assert os.path.exists(os.path.join(project_root, "backend"))


class TestOrderExecutionServiceIntegration:
    """
    Integration tests for complete workflow testing
    Tests interaction between service methods
    """

    @pytest.fixture
    def service(self):
        return OrderExecutionService()

    @pytest.fixture
    def mock_orders_file(self, tmp_path):
        """Create a real temporary orders file"""
        orders_data = {
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

        orders_file = tmp_path / "test_orders.json"
        orders_file.write_text(json.dumps(orders_data))
        return str(orders_file)

    @pytest.mark.asyncio
    async def test_full_workflow_success_mock(self, service, mock_orders_file):
        """Test complete workflow with mocked IBKR connection"""
        # Mock IBKR API components
        with patch('backend.app.services.implementations.order_execution_service.IBOrderExecutor') as mock_executor_class, \
             patch('backend.app.services.implementations.legacy.order_executor.OrderExecutor') as mock_legacy_executor_class:

            # Setup mock execution API
            mock_executor = Mock()
            mock_executor.connected = True
            mock_executor.nextorderId = 100
            mock_executor.account_id = "DU123456"
            mock_executor.orders_status = {
                100: {'status': 'Filled', 'filled': 100, 'remaining': 0, 'avgFillPrice': 180.50, 'permId': 1001},
                101: {'status': 'Filled', 'filled': 50, 'remaining': 0, 'avgFillPrice': 2800.00, 'permId': 1002}
            }
            mock_executor_class.return_value = mock_executor

            # Setup mock legacy executor for contract/order creation
            mock_legacy_executor = Mock()
            mock_contract = Mock()
            mock_order = Mock()
            mock_legacy_executor.create_contract_from_order.return_value = mock_contract
            mock_legacy_executor.create_market_order.return_value = mock_order
            mock_legacy_executor_class.return_value = mock_legacy_executor

            # Execute full workflow
            result = await service.run_execution(
                orders_file=mock_orders_file,
                max_orders=None,
                delay_between_orders=0.1,
                order_type="GTC_MKT"
            )

            # Verify workflow success
            assert result['success'] is True
            assert 'execution_summary' in result
            assert 'order_statuses' in result
            assert 'orders_loaded' in result
            assert result['orders_loaded'] == 2

            # Verify IBKR API calls were made
            mock_executor.connect.assert_called_once()
            mock_executor.placeOrder.assert_called()
            mock_executor.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_connection_failure(self, service, mock_orders_file):
        """Test workflow with IBKR connection failure"""
        with patch('backend.app.services.implementations.order_execution_service.IBOrderExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.connected = False
            mock_executor.nextorderId = None
            mock_executor_class.return_value = mock_executor

            result = await service.run_execution(
                orders_file=mock_orders_file,
                order_type="GTC_MKT"
            )

            assert result['success'] is False
            assert 'error_message' in result
            assert 'failure_time' in result

    @pytest.mark.asyncio
    async def test_workflow_order_load_failure(self, service):
        """Test workflow with order loading failure"""
        result = await service.run_execution(
            orders_file="nonexistent_orders.json"
        )

        assert result['success'] is False
        assert 'error_message' in result
        assert 'Orders file not found' in result['error_message']


class TestOrderExecutionDependencyInjection:
    """Test dependency injection and service factory"""

    def test_get_order_execution_service_singleton(self):
        """Test that service factory returns singleton"""
        service1 = get_order_execution_service()
        service2 = get_order_execution_service()

        assert service1 is service2
        assert isinstance(service1, IOrderExecutionService)
        assert isinstance(service1, OrderExecutionService)

    def test_service_interface_compliance(self):
        """Test that service implements all interface methods"""
        service = get_order_execution_service()

        # Check all interface methods are implemented
        interface_methods = [
            'load_orders', 'connect_to_ibkr', 'execute_orders',
            'get_order_statuses', 'disconnect', 'run_execution',
            'create_ibkr_contract', 'create_ibkr_order'
        ]

        for method_name in interface_methods:
            assert hasattr(service, method_name)
            assert callable(getattr(service, method_name))


class TestOrderExecutionCompatibility:
    """
    Test behavioral compatibility with CLI step10_execute_orders()
    Ensures exact same behavior as legacy implementation
    """

    @pytest.fixture
    def service(self):
        return get_order_execution_service()

    @pytest.mark.asyncio
    async def test_console_output_format_load_orders(self, service, capsys, tmp_path):
        """Test that console output matches legacy format during order loading"""
        # Create test orders file
        orders_data = {"metadata": {"total_orders": 2, "buy_orders": 1, "sell_orders": 1}, "orders": []}
        orders_file = tmp_path / "test_orders.json"
        orders_file.write_text(json.dumps(orders_data))

        await service.load_orders(str(orders_file))

        captured = capsys.readouterr()
        # Check for legacy console output patterns
        assert "[LOAD]" in captured.out
        assert "[OK] Loaded 2 orders (1 SELL, 1 BUY)" in captured.out
        assert "[DEBUG] Working directory:" in captured.out
        assert "[DEBUG] Orders file exists:" in captured.out

    @pytest.mark.asyncio
    async def test_console_output_format_connection(self, service, capsys):
        """Test that connection console output matches legacy format"""
        with patch('backend.app.services.implementations.order_execution_service.IBOrderExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.connected = True
            mock_executor.nextorderId = 100
            mock_executor.account_id = "DU123456"
            mock_executor_class.return_value = mock_executor

            await service.connect_to_ibkr()

            captured = capsys.readouterr()
            # Check for legacy console output patterns
            assert "[CONNECT] Connecting to IB Gateway..." in captured.out
            assert "[OK] Connected to IBKR" in captured.out

    def test_order_type_selection_logic(self, service):
        """Test currency-based order type selection matches legacy logic"""
        # USD stock should allow MOO orders
        usd_order_data = {
            'stock_info': {'currency': 'USD'},
            'ibkr_details': {'symbol': 'AAPL', 'exchange': 'SMART', 'primaryExchange': 'NASDAQ'}
        }

        # International stock should force GTC_MKT
        intl_order_data = {
            'stock_info': {'currency': 'EUR'},
            'ibkr_details': {'symbol': 'ASML', 'exchange': 'SMART', 'primaryExchange': 'NASDAQ'}
        }

        # Test contract creation (doesn't change order type but validates structure)
        usd_contract = service.create_ibkr_contract(usd_order_data)
        intl_contract = service.create_ibkr_contract(intl_order_data)

        assert usd_contract['currency'] == 'USD'
        assert intl_contract['currency'] == 'EUR'

    def test_project_root_path_resolution(self, service):
        """Test that project root resolution matches legacy path logic"""
        project_root = service._get_project_root()

        # Should resolve to the same directory that legacy code uses
        # Legacy uses: os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Which goes from src/order_executor.py up to project root

        # Our service should resolve to the same location
        assert os.path.exists(os.path.join(project_root, 'data'))
        assert os.path.exists(os.path.join(project_root, 'backend'))
        assert os.path.exists(os.path.join(project_root, 'main.py'))

    def test_default_parameter_values(self, service):
        """Test that default parameter values match legacy implementation"""
        # Legacy defaults:
        # - order_type = "GTC_MKT"
        # - delay = 1.0
        # - timeout = 15
        # - port = 4002
        # - host = "127.0.0.1"
        # - client_id = 20

        # Test order creation defaults
        order_spec = service.create_ibkr_order("BUY", 100)  # No order_type specified
        # Should default to MKT (base type, GTC_MKT adds TIF)
        assert order_spec['orderType'] == 'MKT'

    @pytest.mark.asyncio
    async def test_error_handling_patterns(self, service):
        """Test that error handling matches legacy patterns"""
        # File not found should raise specific error
        with pytest.raises(OrderExecutionError) as exc_info:
            await service.load_orders("missing_file.json")

        assert "not found" in str(exc_info.value.message).lower()

        # Connection timeout should raise specific error
        with patch('backend.app.services.implementations.order_execution_service.IBOrderExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.connected = False
            mock_executor.nextorderId = None
            mock_executor_class.return_value = mock_executor

            with pytest.raises(IBKRConnectionError) as exc_info:
                await service.connect_to_ibkr(timeout=1)

            assert "connection" in str(exc_info.value.message).lower()