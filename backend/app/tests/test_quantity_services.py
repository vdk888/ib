"""
Test suite for Step 7 quantity calculation services
Tests AccountService, QuantityService, and QuantityOrchestratorService
Following fintech testing standards for financial calculations
"""

import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, mock_open
import tempfile
import os

# Test target services
from ..services.implementations.account_service import AccountService
from ..services.implementations.quantity_service import QuantityService
from ..services.implementations.quantity_orchestrator_service import QuantityOrchestratorService


class TestAccountService:
    """Test IBKR account service functionality"""

    @pytest.fixture
    def account_service(self):
        """Create AccountService instance for testing"""
        return AccountService()

    @pytest.fixture
    def mock_ibapi_success(self):
        """Mock successful IBKR API responses"""
        mock_app = Mock()
        mock_app.connected = True
        mock_app.account_id = "DU123456"
        mock_app.account_summary = {
            "NetLiquidation": {
                "value": "10000.50",
                "currency": "EUR"
            }
        }
        mock_app.connect.return_value = None
        mock_app.disconnect.return_value = None
        mock_app.run.return_value = None
        mock_app.reqAccountSummary.return_value = None
        mock_app.cancelAccountSummary.return_value = None
        return mock_app

    @pytest.fixture
    def mock_ibapi_failure(self):
        """Mock failed IBKR API connection"""
        mock_app = Mock()
        mock_app.connected = False
        mock_app.account_id = None
        mock_app.account_summary = {}
        mock_app.connect.return_value = None
        mock_app.disconnect.return_value = None
        mock_app.run.return_value = None
        return mock_app

    @pytest.mark.asyncio
    async def test_get_account_value_success(self, account_service, mock_ibapi_success):
        """Test successful account value fetching"""
        with patch('app.services.implementations.account_service.IBApi', return_value=mock_ibapi_success):
            with patch('time.sleep'):  # Skip sleep delays in tests
                total_value, currency = await account_service.get_account_total_value()

        assert total_value == 10000.50
        assert currency == "EUR"
        mock_ibapi_success.connect.assert_called_once_with("127.0.0.1", 4002, clientId=3)
        mock_ibapi_success.reqAccountSummary.assert_called_once_with(9002, "All", "NetLiquidation")

    @pytest.mark.asyncio
    async def test_get_account_value_connection_failure(self, account_service, mock_ibapi_failure):
        """Test connection failure handling"""
        with patch('app.services.implementations.account_service.IBApi', return_value=mock_ibapi_failure):
            with patch('time.sleep'):
                total_value, currency = await account_service.get_account_total_value()

        assert total_value is None
        assert currency is None

    @pytest.mark.asyncio
    async def test_get_account_value_no_account_id(self, account_service):
        """Test handling when no account ID is received"""
        mock_app = Mock()
        mock_app.connected = True
        mock_app.account_id = None  # No account ID received
        mock_app.account_summary = {}

        with patch('..services.implementations.account_service.IBApi', return_value=mock_app):
            with patch('time.sleep'):
                total_value, currency = await account_service.get_account_total_value()

        assert total_value is None
        assert currency is None

    @pytest.mark.asyncio
    async def test_get_account_value_no_liquidation_data(self, account_service):
        """Test handling when NetLiquidation data is missing"""
        mock_app = Mock()
        mock_app.connected = True
        mock_app.account_id = "DU123456"
        mock_app.account_summary = {}  # No NetLiquidation data
        mock_app.connect.return_value = None
        mock_app.disconnect.return_value = None
        mock_app.run.return_value = None
        mock_app.reqAccountSummary.return_value = None
        mock_app.cancelAccountSummary.return_value = None

        with patch('..services.implementations.account_service.IBApi', return_value=mock_app):
            with patch('time.sleep'):
                total_value, currency = await account_service.get_account_total_value()

        assert total_value is None
        assert currency is None

    @pytest.mark.asyncio
    async def test_test_connection_success(self, account_service, mock_ibapi_success):
        """Test connection testing functionality"""
        with patch('app.services.implementations.account_service.IBApi', return_value=mock_ibapi_success):
            with patch('time.sleep'):
                result = await account_service.test_connection()

        assert result["connected"] is True
        assert result["account_id"] == "DU123456"
        assert result["connection_time"] > 0
        assert result["error_message"] is None

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, account_service, mock_ibapi_failure):
        """Test connection testing with failure"""
        with patch('app.services.implementations.account_service.IBApi', return_value=mock_ibapi_failure):
            with patch('time.sleep'):
                result = await account_service.test_connection()

        assert result["connected"] is False
        assert result["account_id"] is None
        assert result["connection_time"] > 0
        assert result["error_message"] == "Connection timeout"


class TestQuantityService:
    """Test quantity calculation service functionality"""

    @pytest.fixture
    def quantity_service(self):
        """Create QuantityService instance for testing"""
        service = QuantityService()
        # Use a temporary path for testing
        service.universe_path = Path(tempfile.gettempdir()) / "test_universe.json"
        return service

    @pytest.fixture
    def sample_universe_data(self):
        """Sample universe data for testing"""
        return {
            "metadata": {
                "portfolio_optimization": {
                    "optimal_allocations": {
                        "screen1": 0.6,
                        "screen2": 0.4
                    }
                }
            },
            "screens": {
                "screen1": {
                    "stocks": [
                        {
                            "ticker": "AAPL",
                            "price": 150.0,
                            "eur_exchange_rate": 1.1,
                            "currency": "USD",
                            "allocation_target": 0.5
                        },
                        {
                            "ticker": "GOOGL",
                            "price": 2500.0,
                            "eur_exchange_rate": 1.1,
                            "currency": "USD",
                            "allocation_target": 0.3
                        }
                    ]
                },
                "screen2": {
                    "stocks": [
                        {
                            "ticker": "TYO:7203",  # Japanese stock
                            "price": 2000.0,
                            "eur_exchange_rate": 0.0067,  # JPY to EUR
                            "currency": "JPY",
                            "allocation_target": 0.8
                        }
                    ]
                }
            }
        }

    @pytest.fixture
    def sample_stock(self):
        """Sample stock for individual testing"""
        return {
            "ticker": "AAPL",
            "price": 150.0,
            "eur_exchange_rate": 1.1,
            "currency": "USD",
            "allocation_target": 0.5
        }

    def test_calculate_stock_fields_basic(self, quantity_service, sample_stock):
        """Test basic stock field calculations"""
        account_value = 10000.0
        screen_allocation = 0.6

        # Make a copy to avoid modifying the fixture
        stock = sample_stock.copy()

        quantity_service.calculate_stock_fields(stock, account_value, screen_allocation)

        # Verify calculations
        assert "eur_price" in stock
        assert "target_value_eur" in stock
        assert "quantity" in stock
        assert "final_target" in stock

        # Verify specific calculations
        expected_eur_price = 150.0 / 1.1  # price / exchange_rate
        assert abs(stock["eur_price"] - expected_eur_price) < 0.000001

        expected_final_target = 0.5 * 0.6  # allocation_target * screen_allocation
        assert abs(stock["final_target"] - expected_final_target) < 0.000001

        expected_target_value = 10000.0 * expected_final_target
        assert abs(stock["target_value_eur"] - expected_target_value) < 0.01

        expected_quantity = int(round(expected_target_value / expected_eur_price))
        assert stock["quantity"] == expected_quantity

    def test_calculate_stock_fields_japanese_stock(self, quantity_service):
        """Test Japanese stock lot size handling"""
        japanese_stock = {
            "ticker": "TYO:7203",
            "price": 2000.0,
            "eur_exchange_rate": 0.0067,  # JPY to EUR
            "currency": "JPY",
            "allocation_target": 0.8
        }

        account_value = 10000.0
        screen_allocation = 0.4

        with patch('builtins.print') as mock_print:  # Capture console output
            quantity_service.calculate_stock_fields(japanese_stock, account_value, screen_allocation)

        # Japanese stocks should be rounded to 100-share lots
        quantity = japanese_stock["quantity"]
        assert quantity % 100 == 0, f"Japanese stock quantity {quantity} should be multiple of 100"

        # Should have printed adjustment message
        print_calls = [call.args[0] for call in mock_print.call_args_list]
        adjustment_printed = any("Japanese stock" in call and "adjusted quantity" in call for call in print_calls)
        assert adjustment_printed, "Should print Japanese stock adjustment message"

    def test_calculate_stock_fields_minimal_allocation(self, quantity_service, sample_stock):
        """Test handling of very small allocations"""
        stock = sample_stock.copy()
        stock["allocation_target"] = 0.000001  # Very small allocation

        account_value = 10000.0
        screen_allocation = 0.1

        quantity_service.calculate_stock_fields(stock, account_value, screen_allocation)

        # Should flag minimal allocations
        assert stock["final_target"] < 1e-10
        assert "allocation_note" in stock
        assert stock["allocation_note"] == "minimal_allocation"

    def test_calculate_stock_fields_error_handling(self, quantity_service):
        """Test error handling with invalid data"""
        invalid_stock = {
            "ticker": "INVALID",
            "price": "not_a_number",
            "eur_exchange_rate": None,
            "allocation_target": "invalid"
        }

        # Should not raise exception, should set default values
        quantity_service.calculate_stock_fields(invalid_stock, 10000.0, 0.5)

        assert invalid_stock["eur_price"] == 0
        assert invalid_stock["target_value_eur"] == 0
        assert invalid_stock["quantity"] == 0

    def test_calculate_stock_quantities(self, quantity_service, sample_universe_data):
        """Test full universe quantity calculation"""
        account_value = 10000.0

        # Make a deep copy to avoid modifying the fixture
        import copy
        universe_data = copy.deepcopy(sample_universe_data)

        stocks_processed = quantity_service.calculate_stock_quantities(universe_data, account_value)

        assert stocks_processed == 3  # 2 stocks in screen1 + 1 stock in screen2

        # Verify all stocks have calculated fields
        for screen_name, screen_data in universe_data["screens"].items():
            for stock in screen_data["stocks"]:
                assert "eur_price" in stock
                assert "target_value_eur" in stock
                assert "quantity" in stock
                assert "final_target" in stock

    def test_round_account_value_conservatively(self, quantity_service):
        """Test conservative account value rounding"""
        test_cases = [
            (9847.32, 9800.0),
            (10000.00, 10000.0),
            (10099.99, 10000.0),
            (10199.50, 10100.0),
            (99.50, 0.0),  # Less than 100
        ]

        for input_value, expected_output in test_cases:
            result = quantity_service.round_account_value_conservatively(input_value)
            assert result == expected_output, f"Input {input_value} should round to {expected_output}, got {result}"

    def test_update_universe_json(self, quantity_service, sample_universe_data):
        """Test universe.json file update"""
        account_value = 9800.0
        currency = "EUR"

        # Create temporary universe file
        import copy
        universe_data = copy.deepcopy(sample_universe_data)

        with open(quantity_service.universe_path, 'w', encoding='utf-8') as f:
            json.dump(universe_data, f, indent=2)

        try:
            # Test the update
            success = quantity_service.update_universe_json(account_value, currency)
            assert success is True

            # Verify the updated file
            with open(quantity_service.universe_path, 'r', encoding='utf-8') as f:
                updated_data = json.load(f)

            assert "account_total_value" in updated_data
            assert updated_data["account_total_value"]["value"] == account_value
            assert updated_data["account_total_value"]["currency"] == currency
            assert "timestamp" in updated_data["account_total_value"]

            # Verify stocks have calculated quantities
            for screen_name, screen_data in updated_data["screens"].items():
                for stock in screen_data["stocks"]:
                    assert "quantity" in stock

        finally:
            # Cleanup
            if quantity_service.universe_path.exists():
                quantity_service.universe_path.unlink()

    def test_update_universe_json_file_not_found(self, quantity_service):
        """Test handling when universe.json doesn't exist"""
        # Ensure file doesn't exist
        if quantity_service.universe_path.exists():
            quantity_service.universe_path.unlink()

        success = quantity_service.update_universe_json(10000.0, "EUR")
        assert success is False


class TestQuantityOrchestratorService:
    """Test quantity orchestrator service functionality"""

    @pytest.fixture
    def mock_account_service(self):
        """Mock account service"""
        mock_service = AsyncMock()
        mock_service.get_account_total_value.return_value = (10000.50, "EUR")
        return mock_service

    @pytest.fixture
    def mock_quantity_service(self):
        """Mock quantity service"""
        mock_service = Mock()
        mock_service.round_account_value_conservatively.return_value = 10000.0
        mock_service.update_universe_json.return_value = True
        return mock_service

    @pytest.fixture
    def orchestrator_service(self, mock_account_service, mock_quantity_service):
        """Create orchestrator service with mocked dependencies"""
        return QuantityOrchestratorService(mock_account_service, mock_quantity_service)

    @pytest.mark.asyncio
    async def test_main_success(self, orchestrator_service, mock_account_service, mock_quantity_service):
        """Test successful main orchestration"""
        result = await orchestrator_service.main()

        assert result is True
        mock_account_service.get_account_total_value.assert_called_once()
        mock_quantity_service.round_account_value_conservatively.assert_called_once_with(10000.50)
        mock_quantity_service.update_universe_json.assert_called_once_with(10000.0, "EUR")

    @pytest.mark.asyncio
    async def test_main_account_fetch_failure(self, orchestrator_service, mock_account_service, mock_quantity_service):
        """Test main orchestration when account fetch fails"""
        mock_account_service.get_account_total_value.return_value = (None, None)

        result = await orchestrator_service.main()

        assert result is False
        mock_quantity_service.update_universe_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_main_universe_update_failure(self, orchestrator_service, mock_account_service, mock_quantity_service):
        """Test main orchestration when universe update fails"""
        mock_quantity_service.update_universe_json.return_value = False

        result = await orchestrator_service.main()

        assert result is False

    @pytest.mark.asyncio
    async def test_calculate_quantities_only(self, orchestrator_service, mock_quantity_service):
        """Test calculating quantities with provided account value"""
        account_value = 12000.0
        currency = "EUR"

        success, stocks_processed = await orchestrator_service.calculate_quantities_only(account_value, currency)

        assert success is True
        assert stocks_processed == 0  # Current implementation returns 0
        mock_quantity_service.round_account_value_conservatively.assert_called_once_with(account_value)
        mock_quantity_service.update_universe_json.assert_called_once_with(12000.0, currency)

    @pytest.mark.asyncio
    async def test_get_account_info_success(self, orchestrator_service, mock_account_service, mock_quantity_service):
        """Test getting account information"""
        account_info = await orchestrator_service.get_account_info()

        assert account_info["success"] is True
        assert account_info["account_value"] == 10000.50
        assert account_info["currency"] == "EUR"
        assert account_info["rounded_account_value"] == 10000.0
        assert "rounding_note" in account_info

    @pytest.mark.asyncio
    async def test_get_account_info_failure(self, orchestrator_service, mock_account_service):
        """Test getting account information when IBKR fails"""
        mock_account_service.get_account_total_value.return_value = (None, None)

        account_info = await orchestrator_service.get_account_info()

        assert account_info["success"] is False
        assert "error" in account_info


class TestIntegration:
    """Integration tests for the complete quantity calculation pipeline"""

    @pytest.fixture
    def temp_universe_file(self):
        """Create temporary universe file for integration testing"""
        temp_dir = Path(tempfile.gettempdir())
        universe_path = temp_dir / "integration_test_universe.json"

        # Create sample universe data
        universe_data = {
            "metadata": {
                "portfolio_optimization": {
                    "optimal_allocations": {
                        "test_screen": 1.0
                    }
                }
            },
            "screens": {
                "test_screen": {
                    "stocks": [
                        {
                            "ticker": "TEST1",
                            "price": 100.0,
                            "eur_exchange_rate": 1.0,
                            "currency": "EUR",
                            "allocation_target": 0.5
                        },
                        {
                            "ticker": "TEST2",
                            "price": 200.0,
                            "eur_exchange_rate": 1.0,
                            "currency": "EUR",
                            "allocation_target": 0.3
                        }
                    ]
                }
            }
        }

        with open(universe_path, 'w', encoding='utf-8') as f:
            json.dump(universe_data, f, indent=2)

        yield universe_path

        # Cleanup
        if universe_path.exists():
            universe_path.unlink()

    def test_end_to_end_quantity_calculation(self, temp_universe_file):
        """Test complete quantity calculation process end-to-end"""
        # Setup services with test universe path
        quantity_service = QuantityService()
        quantity_service.universe_path = temp_universe_file

        # Mock account service
        mock_account_service = AsyncMock()
        mock_account_service.get_account_total_value.return_value = (10000.0, "EUR")

        # Create orchestrator
        orchestrator = QuantityOrchestratorService(mock_account_service, quantity_service)

        # Run the main process
        import asyncio
        result = asyncio.run(orchestrator.main())

        assert result is True

        # Verify universe was updated correctly
        with open(temp_universe_file, 'r', encoding='utf-8') as f:
            updated_universe = json.load(f)

        # Check account value was added
        assert "account_total_value" in updated_universe
        assert updated_universe["account_total_value"]["value"] == 10000.0
        assert updated_universe["account_total_value"]["currency"] == "EUR"

        # Check stocks have quantity calculations
        for screen_name, screen_data in updated_universe["screens"].items():
            for stock in screen_data["stocks"]:
                assert "eur_price" in stock
                assert "target_value_eur" in stock
                assert "quantity" in stock
                assert "final_target" in stock

                # Verify reasonable values
                assert stock["eur_price"] > 0
                assert stock["target_value_eur"] >= 0
                assert stock["quantity"] >= 0
                assert 0 <= stock["final_target"] <= 1