"""
Unit tests for Order Status Service (Step 11)
Tests the service implementation against legacy behavior
"""

import pytest
import os
import sys
import json
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, os.path.join(project_root, "backend"))

from app.services.implementations.order_status_service import OrderStatusService
from app.services.interfaces import IOrderStatusService


class TestOrderStatusService:
    """Test Order Status Service implementation"""

    @pytest.fixture
    def sample_orders_data(self):
        """Sample orders.json data for testing"""
        return {
            "metadata": {
                "generated_at": "2024-01-15 14:30:00",
                "total_orders": 3
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
                        "primaryExchange": "NASDAQ",
                        "conId": 265598
                    }
                },
                {
                    "symbol": "DPM",
                    "action": "BUY",
                    "quantity": 50,
                    "stock_info": {
                        "ticker": "DPM",
                        "name": "Dundee Precious Metals Inc",
                        "currency": "CAD"
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
    def sample_ibkr_orders(self):
        """Sample IBKR order data for testing"""
        return {
            123: {
                "symbol": "AAPL",
                "action": "BUY",
                "quantity": 100,
                "status": "FILLED",
                "avgFillPrice": 150.25,
                "filled": 100,
                "remaining": 0,
                "orderType": "MKT"
            },
            124: {
                "symbol": "GOOGL",
                "action": "SELL",
                "quantity": 20,  # Quantity mismatch
                "status": "FILLED",
                "avgFillPrice": 140.50,
                "filled": 20,
                "remaining": 0,
                "orderType": "MKT"
            }
            # DPM missing - simulates order not found in IBKR
        }

    @pytest.fixture
    def sample_positions(self):
        """Sample IBKR positions for testing"""
        return {
            "AAPL": {
                "position": 150,
                "avgCost": 145.50,
                "currency": "USD",
                "exchange": "NASDAQ"
            },
            "GOOGL": {
                "position": 25,
                "avgCost": 140.00,
                "currency": "USD",
                "exchange": "NASDAQ"
            }
        }

    @pytest.fixture
    def service(self, tmp_path):
        """Create OrderStatusService instance for testing"""
        # Create temporary orders file
        orders_file = tmp_path / "test_orders.json"
        return OrderStatusService(str(orders_file))

    def test_service_implements_interface(self, service):
        """Test that service implements IOrderStatusService interface"""
        assert isinstance(service, IOrderStatusService)

        # Test all required methods are present
        assert hasattr(service, 'load_orders_json')
        assert hasattr(service, 'connect_to_ibkr')
        assert hasattr(service, 'fetch_account_data')
        assert hasattr(service, 'analyze_orders')
        assert hasattr(service, 'get_missing_order_analysis')
        assert hasattr(service, 'get_order_status_summary')
        assert hasattr(service, 'get_positions_summary')
        assert hasattr(service, 'run_status_check')
        assert hasattr(service, 'disconnect')
        assert hasattr(service, 'get_verification_results')

    def test_load_orders_json_success(self, service, sample_orders_data, tmp_path):
        """Test successful loading of orders.json file"""
        # Create test orders file
        orders_file = tmp_path / "test_orders.json"
        with open(orders_file, 'w') as f:
            json.dump(sample_orders_data, f)

        service.orders_file = str(orders_file)

        # Mock legacy checker
        mock_checker = Mock()
        mock_checker.load_orders_json.return_value = sample_orders_data

        with patch('app.services.implementations.order_status_service.OrderStatusChecker') as MockChecker:
            MockChecker.return_value = mock_checker

            result = service.load_orders_json()

            assert result == sample_orders_data
            assert service.orders_data == sample_orders_data
            MockChecker.assert_called_once_with(str(orders_file))
            mock_checker.load_orders_json.assert_called_once()

    def test_load_orders_json_file_not_found(self, service):
        """Test loading non-existent orders file raises FileNotFoundError"""
        service.orders_file = "non_existent_file.json"

        mock_checker = Mock()
        mock_checker.load_orders_json.side_effect = FileNotFoundError("File not found")

        with patch('app.services.implementations.order_status_service.OrderStatusChecker') as MockChecker:
            MockChecker.return_value = mock_checker

            with pytest.raises(FileNotFoundError):
                service.load_orders_json()

    def test_connect_to_ibkr_success(self, service):
        """Test successful IBKR connection"""
        mock_checker = Mock()
        mock_checker.connect_to_ibkr.return_value = True

        with patch('app.services.implementations.order_status_service.OrderStatusChecker') as MockChecker:
            MockChecker.return_value = mock_checker

            result = service.connect_to_ibkr()

            assert result is True
            mock_checker.connect_to_ibkr.assert_called_once()

    def test_connect_to_ibkr_failure(self, service):
        """Test failed IBKR connection"""
        mock_checker = Mock()
        mock_checker.connect_to_ibkr.return_value = False

        with patch('app.services.implementations.order_status_service.OrderStatusChecker') as MockChecker:
            MockChecker.return_value = mock_checker

            result = service.connect_to_ibkr()

            assert result is False
            mock_checker.connect_to_ibkr.assert_called_once()

    def test_fetch_account_data(self, service):
        """Test fetching account data from IBKR"""
        mock_checker = Mock()
        service._legacy_checker = mock_checker

        service.fetch_account_data()

        mock_checker.fetch_account_data.assert_called_once()

    def test_fetch_account_data_no_connection(self, service):
        """Test fetch_account_data fails without connection"""
        with pytest.raises(ValueError, match="Must connect to IBKR first"):
            service.fetch_account_data()

    def test_analyze_orders_success(self, service, sample_orders_data, sample_ibkr_orders):
        """Test successful order analysis"""
        service.orders_data = sample_orders_data

        # Mock legacy checker and API
        mock_api = Mock()
        mock_api.open_orders = sample_ibkr_orders
        mock_api.completed_orders = {}

        mock_checker = Mock()
        mock_checker.api = mock_api
        mock_checker.analyze_orders = Mock()  # Mock console output method

        service._legacy_checker = mock_checker

        result = service.analyze_orders()

        # Verify analysis results
        assert isinstance(result, dict)
        assert 'found_in_ibkr' in result
        assert 'missing_from_ibkr' in result
        assert 'quantity_mismatches' in result
        assert 'success_rate' in result
        assert 'total_orders' in result
        assert 'missing_orders' in result
        assert 'analysis_table' in result

        # Check specific counts
        assert result['found_in_ibkr'] == 2  # AAPL and GOOGL found
        assert result['missing_from_ibkr'] == 1  # DPM missing
        assert result['quantity_mismatches'] == 1  # GOOGL quantity mismatch
        assert result['total_orders'] == 3
        assert result['success_rate'] == pytest.approx(66.67, abs=0.1)  # 2/3 found

        # Check missing orders
        assert len(result['missing_orders']) == 1
        assert result['missing_orders'][0]['symbol'] == 'DPM'

        # Check analysis table
        assert len(result['analysis_table']) == 3

        # Verify legacy method was called
        mock_checker.analyze_orders.assert_called_once()

    def test_get_missing_order_analysis(self, service):
        """Test missing order analysis with known failure patterns"""
        missing_orders = [
            {
                "symbol": "AAPL",
                "action": "SELL",
                "quantity": 1,
                "stock_info": {
                    "ticker": "AAPL",
                    "currency": "USD"
                },
                "ibkr_details": {
                    "primaryExchange": "NASDAQ"
                }
            },
            {
                "symbol": "DPM",
                "action": "BUY",
                "quantity": 50,
                "stock_info": {
                    "ticker": "DPM",
                    "currency": "CAD"
                },
                "ibkr_details": {
                    "primaryExchange": "TSE"
                }
            },
            {
                "symbol": "UNKNOWN",
                "action": "BUY",
                "quantity": 100,
                "stock_info": {
                    "ticker": "UNKNOWN",
                    "currency": "EUR"
                },
                "ibkr_details": {
                    "primaryExchange": "XETRA"
                }
            }
        ]

        # Mock legacy method call
        mock_checker = Mock()
        service._legacy_checker = mock_checker

        result = service.get_missing_order_analysis(missing_orders)

        # Verify result structure
        assert isinstance(result, dict)
        assert 'failure_analysis' in result
        assert 'recommendations' in result
        assert 'failure_patterns' in result

        # Check failure analysis
        assert len(result['failure_analysis']) == 3

        # Check known pattern - AAPL
        aapl_analysis = next(f for f in result['failure_analysis'] if f['symbol'] == 'AAPL')
        assert aapl_analysis['reason'] == 'IBKR Account Restriction'
        assert 'direct routing' in aapl_analysis['details'].lower()

        # Check known pattern - DPM
        dpm_analysis = next(f for f in result['failure_analysis'] if f['symbol'] == 'DPM')
        assert dpm_analysis['reason'] == 'Contract Not Supported'
        assert 'TSE' in dpm_analysis['details']

        # Check generic pattern - UNKNOWN (non-USD currency)
        unknown_analysis = next(f for f in result['failure_analysis'] if f['symbol'] == 'UNKNOWN')
        assert unknown_analysis['reason'] == 'Likely International Trading Issue'

        # Check recommendations are present
        assert len(result['recommendations']) > 0

        # Verify legacy method was called
        mock_checker.show_missing_order_analysis.assert_called_once_with(missing_orders)

    def test_get_order_status_summary(self, service, sample_ibkr_orders):
        """Test order status summary generation"""
        mock_api = Mock()
        mock_api.open_orders = sample_ibkr_orders
        mock_api.completed_orders = {}

        mock_checker = Mock()
        mock_checker.api = mock_api
        mock_checker.show_order_status_summary = Mock()  # Mock console output

        service._legacy_checker = mock_checker

        result = service.get_order_status_summary()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'orders_by_status' in result
        assert 'status_counts' in result
        assert 'total_orders' in result
        assert 'order_details' in result

        # Check counts
        assert result['total_orders'] == 2
        assert result['status_counts']['FILLED'] == 2

        # Check order details
        assert len(result['order_details']) == 2

        # Verify legacy method was called
        mock_checker.show_order_status_summary.assert_called_once()

    def test_get_positions_summary(self, service, sample_positions):
        """Test positions summary generation"""
        mock_api = Mock()
        mock_api.positions = sample_positions

        mock_checker = Mock()
        mock_checker.api = mock_api
        mock_checker.show_positions = Mock()  # Mock console output

        service._legacy_checker = mock_checker

        result = service.get_positions_summary()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'positions' in result
        assert 'total_positions' in result
        assert 'market_values' in result
        assert 'total_market_value' in result

        # Check counts and calculations
        assert result['total_positions'] == 2
        assert 'AAPL' in result['positions']
        assert 'GOOGL' in result['positions']

        # Check market value calculations
        aapl_market_value = 150 * 145.50  # position * avg_cost
        googl_market_value = 25 * 140.00
        expected_total = aapl_market_value + googl_market_value

        assert result['market_values']['AAPL'] == aapl_market_value
        assert result['total_market_value'] == expected_total

        # Verify legacy method was called
        mock_checker.show_positions.assert_called_once()

    def test_run_status_check_success(self, service):
        """Test complete status check workflow success"""
        mock_checker = Mock()
        mock_checker.run_status_check.return_value = True

        with patch('app.services.implementations.order_status_service.OrderStatusChecker') as MockChecker:
            MockChecker.return_value = mock_checker

            result = service.run_status_check()

            assert result is True
            mock_checker.run_status_check.assert_called_once()

    def test_run_status_check_failure(self, service):
        """Test status check workflow failure with cleanup"""
        mock_checker = Mock()
        mock_checker.run_status_check.side_effect = Exception("Connection failed")
        mock_checker.disconnect = Mock()

        with patch('app.services.implementations.order_status_service.OrderStatusChecker') as MockChecker:
            MockChecker.return_value = mock_checker

            result = service.run_status_check()

            assert result is False
            mock_checker.run_status_check.assert_called_once()
            mock_checker.disconnect.assert_called_once()

    def test_disconnect(self, service):
        """Test IBKR disconnection"""
        mock_checker = Mock()
        service._legacy_checker = mock_checker

        service.disconnect()

        mock_checker.disconnect.assert_called_once()

    def test_disconnect_no_checker(self, service):
        """Test disconnect when no checker exists"""
        # Should not raise exception
        service.disconnect()

    def test_get_verification_results_complete(self, service, sample_orders_data, sample_ibkr_orders, sample_positions):
        """Test complete verification results generation"""
        service.orders_data = sample_orders_data

        mock_api = Mock()
        mock_api.open_orders = sample_ibkr_orders
        mock_api.completed_orders = {}
        mock_api.positions = sample_positions

        mock_checker = Mock()
        mock_checker.api = mock_api
        mock_checker.analyze_orders = Mock()
        mock_checker.show_order_status_summary = Mock()
        mock_checker.show_positions = Mock()
        mock_checker.show_missing_order_analysis = Mock()

        service._legacy_checker = mock_checker

        result = service.get_verification_results()

        # Verify complete result structure
        assert isinstance(result, dict)
        assert 'comparison_summary' in result
        assert 'order_matches' in result
        assert 'missing_orders' in result
        assert 'recommendations' in result
        assert 'extra_orders' in result
        assert 'positions' in result
        assert 'order_status_breakdown' in result

        # Check comparison summary structure
        summary = result['comparison_summary']
        assert 'found_in_ibkr' in summary
        assert 'missing_from_ibkr' in summary
        assert 'quantity_mismatches' in summary
        assert 'success_rate' in summary
        assert 'total_orders' in summary
        assert 'timestamp' in summary

    def test_get_verification_results_no_connection(self, service):
        """Test verification results fails without connection"""
        with pytest.raises(ValueError, match="Must connect to IBKR and fetch data first"):
            service.get_verification_results()

    def test_path_resolution(self):
        """Test proper path resolution for orders file"""
        # Test relative path
        service = OrderStatusService("orders.json")
        assert "data" in service.orders_file
        assert service.orders_file.endswith("orders.json")

        # Test absolute path
        abs_path = "/absolute/path/orders.json"
        service = OrderStatusService(abs_path)
        assert service.orders_file == abs_path


class TestOrderStatusServiceIntegration:
    """Integration tests for Order Status Service"""

    def test_service_workflow_with_mocked_legacy(self, tmp_path):
        """Test complete service workflow with mocked legacy components"""
        # Create test data
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

        service = OrderStatusService(str(orders_file))

        # Mock the complete workflow
        mock_api = Mock()
        mock_api.open_orders = {
            123: {
                "symbol": "AAPL",
                "action": "BUY",
                "quantity": 100,
                "status": "FILLED",
                "avgFillPrice": 150.0,
                "filled": 100,
                "remaining": 0,
                "orderType": "MKT"
            }
        }
        mock_api.completed_orders = {}
        mock_api.positions = {
            "AAPL": {
                "position": 100,
                "avgCost": 150.0,
                "currency": "USD",
                "exchange": "NASDAQ"
            }
        }

        mock_checker = Mock()
        mock_checker.load_orders_json.return_value = orders_data
        mock_checker.connect_to_ibkr.return_value = True
        mock_checker.api = mock_api
        mock_checker.fetch_account_data = Mock()
        mock_checker.analyze_orders = Mock()
        mock_checker.show_order_status_summary = Mock()
        mock_checker.show_positions = Mock()
        mock_checker.disconnect = Mock()

        with patch('app.services.implementations.order_status_service.OrderStatusChecker') as MockChecker:
            MockChecker.return_value = mock_checker

            # Test the workflow
            service.load_orders_json()
            assert service.connect_to_ibkr()
            service.fetch_account_data()

            # Test analysis
            analysis = service.analyze_orders()
            assert analysis['found_in_ibkr'] == 1
            assert analysis['missing_from_ibkr'] == 0
            assert analysis['success_rate'] == 100.0

            # Test summaries
            status_summary = service.get_order_status_summary()
            assert status_summary['total_orders'] == 1

            positions_summary = service.get_positions_summary()
            assert positions_summary['total_positions'] == 1

            # Test complete verification
            verification = service.get_verification_results()
            assert verification['comparison_summary']['success_rate'] == 100.0

            service.disconnect()

            # Verify all mock calls
            mock_checker.load_orders_json.assert_called()
            mock_checker.connect_to_ibkr.assert_called()
            mock_checker.fetch_account_data.assert_called()
            mock_checker.analyze_orders.assert_called()
            mock_checker.show_order_status_summary.assert_called()
            mock_checker.show_positions.assert_called()
            mock_checker.disconnect.assert_called()