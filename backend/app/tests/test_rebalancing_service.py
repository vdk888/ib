#!/usr/bin/env python3
"""
Comprehensive tests for RebalancingService
Tests API vs CLI behavioral compatibility for Step 9: Rebalancing Orders Service
"""
import pytest
import json
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Import the service and interfaces
from backend.app.services.implementations.rebalancing_service import RebalancingService
from backend.app.services.interfaces import IRebalancingService


class TestRebalancingService:
    """Test suite for RebalancingService implementation"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = RebalancingService()
        self.temp_dir = tempfile.mkdtemp()

        # Create mock universe data
        self.mock_universe_data = {
            "metadata": {
                "total_stocks": 10,
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
                        },
                        {
                            "ticker": "GOOGL",
                            "name": "Alphabet Inc",
                            "currency": "USD",
                            "sector": "Technology",
                            "country": "US",
                            "quantity": 50,
                            "screens": ["growth"],
                            "ibkr_details": {
                                "found": True,
                                "symbol": "GOOGL",
                                "exchange": "NASDAQ",
                                "primaryExchange": "NASDAQ",
                                "conId": 208813719
                            }
                        }
                    ]
                },
                "value": {
                    "stocks": [
                        {
                            "ticker": "MSFT",
                            "name": "Microsoft Corp",
                            "currency": "USD",
                            "sector": "Technology",
                            "country": "US",
                            "quantity": 75,
                            "screens": ["value"],
                            "ibkr_details": {
                                "found": True,
                                "symbol": "MSFT",
                                "exchange": "NASDAQ",
                                "primaryExchange": "NASDAQ",
                                "conId": 272093
                            }
                        }
                    ]
                }
            }
        }

        # Mock current IBKR positions
        self.mock_current_positions = {
            "AAPL": 80,  # Need to buy 20 more (target 100)
            "MSFT": 100,  # Need to sell 25 (target 75)
            "NVDA": 50   # Need to sell all 50 (not in targets)
        }

        # Mock contract details
        self.mock_contract_details = {
            "AAPL": {
                "symbol": "AAPL",
                "conId": 265598,
                "exchange": "NASDAQ",
                "primaryExchange": "NASDAQ",
                "currency": "USD",
                "secType": "STK"
            },
            "MSFT": {
                "symbol": "MSFT",
                "conId": 272093,
                "exchange": "NASDAQ",
                "primaryExchange": "NASDAQ",
                "currency": "USD",
                "secType": "STK"
            },
            "NVDA": {
                "symbol": "NVDA",
                "conId": 4815747,
                "exchange": "NASDAQ",
                "primaryExchange": "NASDAQ",
                "currency": "USD",
                "secType": "STK"
            }
        }

    def teardown_method(self):
        """Clean up after tests"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_implements_interface(self):
        """Test that service implements the IRebalancingService interface"""
        assert isinstance(self.service, IRebalancingService)

        # Check all required methods exist
        required_methods = [
            'load_universe_data',
            'calculate_target_quantities',
            'fetch_current_positions',
            'generate_orders',
            'save_orders_json',
            'run_rebalancing'
        ]

        for method in required_methods:
            assert hasattr(self.service, method)
            assert callable(getattr(self.service, method))

    def test_load_universe_data_success(self):
        """Test successful universe data loading"""
        # Create temporary universe file
        universe_file = os.path.join(self.temp_dir, "universe_with_ibkr.json")
        with open(universe_file, 'w') as f:
            json.dump(self.mock_universe_data, f)

        # Test loading
        result = self.service.load_universe_data(universe_file)

        assert result == self.mock_universe_data
        assert result['metadata']['total_stocks'] == 10
        assert 'growth' in result['screens']
        assert 'value' in result['screens']

    def test_load_universe_data_file_not_found(self):
        """Test universe data loading with non-existent file"""
        non_existent_file = "/non/existent/path/universe.json"

        with pytest.raises(FileNotFoundError):
            self.service.load_universe_data(non_existent_file)

    def test_calculate_target_quantities_success(self):
        """Test target quantities calculation"""
        result = self.service.calculate_target_quantities(self.mock_universe_data)

        # Expected targets: AAPL=100 (growth), GOOGL=50 (growth), MSFT=75 (value)
        expected_targets = {
            "AAPL": 100,
            "GOOGL": 50,
            "MSFT": 75
        }

        assert result == expected_targets
        assert len(result) == 3
        assert hasattr(self.service, 'symbol_details')

    def test_calculate_target_quantities_aggregation(self):
        """Test target quantities aggregation across multiple screens"""
        # Create test data where AAPL appears in both screens
        test_data = {
            "screens": {
                "growth": {
                    "stocks": [
                        {
                            "ticker": "AAPL",
                            "quantity": 50,
                            "ibkr_details": {"found": True, "symbol": "AAPL"},
                            "name": "Apple Inc",
                            "currency": "USD",
                            "sector": "Tech",
                            "country": "US",
                            "screens": ["growth"]
                        }
                    ]
                },
                "value": {
                    "stocks": [
                        {
                            "ticker": "AAPL",
                            "quantity": 30,
                            "ibkr_details": {"found": True, "symbol": "AAPL"},
                            "name": "Apple Inc",
                            "currency": "USD",
                            "sector": "Tech",
                            "country": "US",
                            "screens": ["value"]
                        }
                    ]
                }
            }
        }

        result = self.service.calculate_target_quantities(test_data)

        # AAPL should be aggregated: 50 + 30 = 80
        assert result["AAPL"] == 80

    def test_calculate_target_quantities_skips_unfound_stocks(self):
        """Test that stocks without IBKR details are skipped"""
        test_data = {
            "screens": {
                "growth": {
                    "stocks": [
                        {
                            "ticker": "UNKNOWN",
                            "quantity": 100,
                            "ibkr_details": {"found": False},
                            "name": "Unknown Stock",
                            "currency": "USD",
                            "sector": "Unknown",
                            "country": "US",
                            "screens": ["growth"]
                        }
                    ]
                }
            }
        }

        result = self.service.calculate_target_quantities(test_data)

        # Should be empty since stock wasn't found in IBKR
        assert len(result) == 0

    @patch('backend.app.services.implementations.rebalancing_service.IBRebalancerApi')
    def test_fetch_current_positions_success(self, mock_api_class):
        """Test successful current positions fetching from IBKR"""
        # Mock the IBKR API
        mock_api = Mock()
        mock_api.connected = True
        mock_api.account_id = "TEST123"
        mock_api.data_ready = True
        mock_api.current_positions = self.mock_current_positions.copy()
        mock_api.contract_details = self.mock_contract_details.copy()
        mock_api_class.return_value = mock_api

        # Mock connection behavior
        def mock_connect(*args, **kwargs):
            mock_api.connected = True

        def mock_run():
            pass

        mock_api.connect = mock_connect
        mock_api.run = mock_run

        # Test fetching positions
        positions, contract_details = self.service.fetch_current_positions()

        assert positions == self.mock_current_positions
        assert contract_details == self.mock_contract_details

        # Verify API calls were made
        mock_api.connect.assert_called_once()
        mock_api.reqPositions.assert_called_once()
        mock_api.reqAccountUpdates.assert_called()
        mock_api.disconnect.assert_called_once()

    @patch('backend.app.services.implementations.rebalancing_service.IBRebalancerApi')
    def test_fetch_current_positions_connection_failure(self, mock_api_class):
        """Test IBKR connection failure handling"""
        # Mock failed connection
        mock_api = Mock()
        mock_api.connected = False
        mock_api_class.return_value = mock_api

        with pytest.raises(Exception, match="Failed to connect to IB Gateway"):
            self.service.fetch_current_positions()

    def test_generate_orders_buy_sell_logic(self):
        """Test order generation with buy/sell logic"""
        # Setup target quantities and symbol details
        target_quantities = {"AAPL": 100, "MSFT": 75}
        current_positions = {"AAPL": 80, "MSFT": 100, "NVDA": 50}

        symbol_details = {
            "AAPL": {
                "ticker": "AAPL",
                "name": "Apple Inc",
                "currency": "USD",
                "screens": ["growth"],
                "ibkr_details": {
                    "symbol": "AAPL",
                    "exchange": "NASDAQ",
                    "primaryExchange": "NASDAQ",
                    "conId": 265598
                }
            },
            "MSFT": {
                "ticker": "MSFT",
                "name": "Microsoft Corp",
                "currency": "USD",
                "screens": ["value"],
                "ibkr_details": {
                    "symbol": "MSFT",
                    "exchange": "NASDAQ",
                    "primaryExchange": "NASDAQ",
                    "conId": 272093
                }
            }
        }

        orders = self.service.generate_orders(
            target_quantities,
            current_positions,
            symbol_details,
            self.mock_contract_details
        )

        # Should generate 3 orders: BUY AAPL(20), SELL MSFT(25), SELL NVDA(50)
        assert len(orders) == 3

        # Check order details
        order_by_symbol = {order['symbol']: order for order in orders}

        # Check AAPL BUY order
        aapl_order = order_by_symbol['AAPL']
        assert aapl_order['action'] == 'BUY'
        assert aapl_order['quantity'] == 20  # 100 - 80
        assert aapl_order['current_quantity'] == 80
        assert aapl_order['target_quantity'] == 100

        # Check MSFT SELL order
        msft_order = order_by_symbol['MSFT']
        assert msft_order['action'] == 'SELL'
        assert msft_order['quantity'] == 25  # 100 - 75
        assert msft_order['current_quantity'] == 100
        assert msft_order['target_quantity'] == 75

        # Check NVDA SELL order (not in targets)
        nvda_order = order_by_symbol['NVDA']
        assert nvda_order['action'] == 'SELL'
        assert nvda_order['quantity'] == 50  # 50 - 0
        assert nvda_order['current_quantity'] == 50
        assert nvda_order['target_quantity'] == 0

    def test_generate_orders_no_change_needed(self):
        """Test order generation when no changes are needed"""
        target_quantities = {"AAPL": 100}
        current_positions = {"AAPL": 100}  # Already at target
        symbol_details = {"AAPL": self.mock_universe_data['screens']['growth']['stocks'][0]}

        orders = self.service.generate_orders(
            target_quantities,
            current_positions,
            symbol_details,
            self.mock_contract_details
        )

        # Should generate no orders since positions match targets
        assert len(orders) == 0

    def test_generate_orders_sell_first_then_buy_sorting(self):
        """Test that SELL orders come before BUY orders"""
        target_quantities = {"AAPL": 100}  # Need to buy
        current_positions = {"AAPL": 50, "MSFT": 100}  # MSFT needs to be sold

        symbol_details = {
            "AAPL": {
                "ticker": "AAPL",
                "name": "Apple Inc",
                "currency": "USD",
                "screens": ["growth"],
                "ibkr_details": {
                    "symbol": "AAPL",
                    "exchange": "NASDAQ",
                    "primaryExchange": "NASDAQ",
                    "conId": 265598
                }
            }
        }

        orders = self.service.generate_orders(
            target_quantities,
            current_positions,
            symbol_details,
            self.mock_contract_details
        )

        # Should have SELL order first, then BUY order
        assert len(orders) == 2
        assert orders[0]['action'] == 'SELL'  # MSFT sell comes first
        assert orders[0]['symbol'] == 'MSFT'
        assert orders[1]['action'] == 'BUY'   # AAPL buy comes second
        assert orders[1]['symbol'] == 'AAPL'

    def test_save_orders_json_structure(self):
        """Test orders JSON file creation with proper structure"""
        # Create mock orders
        orders = [
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
        ]

        output_file = os.path.join(self.temp_dir, "orders.json")

        self.service.save_orders_json(orders, output_file)

        # Verify file was created
        assert os.path.exists(output_file)

        # Verify file structure
        with open(output_file, 'r') as f:
            data = json.load(f)

        assert 'metadata' in data
        assert 'orders' in data

        # Check metadata
        metadata = data['metadata']
        assert metadata['total_orders'] == 1
        assert metadata['buy_orders'] == 1
        assert metadata['sell_orders'] == 0
        assert metadata['total_buy_quantity'] == 100
        assert metadata['total_sell_quantity'] == 0
        assert 'generated_at' in metadata

        # Check orders
        assert data['orders'] == orders

    @patch.object(RebalancingService, 'fetch_current_positions')
    def test_run_rebalancing_orchestration(self, mock_fetch_positions):
        """Test complete rebalancing orchestration"""
        # Setup mocks
        mock_fetch_positions.return_value = (
            self.mock_current_positions,
            self.mock_contract_details
        )

        # Create universe file
        universe_file = os.path.join(self.temp_dir, "universe_with_ibkr.json")
        with open(universe_file, 'w') as f:
            json.dump(self.mock_universe_data, f)

        # Run rebalancing
        result = self.service.run_rebalancing(universe_file)

        # Verify result structure
        assert 'orders' in result
        assert 'metadata' in result
        assert 'target_quantities' in result
        assert 'current_positions' in result

        # Verify metadata
        metadata = result['metadata']
        assert metadata['total_orders'] > 0
        assert 'buy_orders' in metadata
        assert 'sell_orders' in metadata
        assert 'generated_at' in metadata

        # Verify orders were generated
        orders = result['orders']
        assert len(orders) > 0

        # Verify orders.json file was created
        orders_file = os.path.join(os.path.dirname(universe_file), "orders.json")
        assert os.path.exists(orders_file)

    def test_run_legacy_rebalancer_compatibility(self):
        """Test legacy rebalancer wrapper for CLI compatibility"""
        # Create universe file
        universe_file = os.path.join(self.temp_dir, "universe_with_ibkr.json")
        with open(universe_file, 'w') as f:
            json.dump(self.mock_universe_data, f)

        # Mock the PortfolioRebalancer
        with patch('backend.app.services.implementations.rebalancing_service.PortfolioRebalancer') as mock_rebalancer_class:
            mock_rebalancer = Mock()
            mock_rebalancer_class.return_value = mock_rebalancer

            result = self.service.run_legacy_rebalancer(universe_file)

            # Should create PortfolioRebalancer and call run_rebalancing
            mock_rebalancer_class.assert_called_once_with(universe_file)
            mock_rebalancer.run_rebalancing.assert_called_once()
            assert result is True


class TestRebalancingServiceIntegration:
    """Integration tests for RebalancingService with realistic data"""

    def test_real_universe_structure_compatibility(self):
        """Test with a realistic universe structure"""
        service = RebalancingService()

        # Create realistic universe data
        realistic_universe = {
            "metadata": {
                "total_stocks": 438,
                "unique_stocks": 350,
                "screens": ["growth", "value", "quality"],
                "generated_at": "2024-01-15 10:30:00"
            },
            "screens": {
                "growth": {
                    "stocks": [
                        {
                            "ticker": "AAPL",
                            "isin": "US0378331005",
                            "name": "Apple Inc",
                            "currency": "USD",
                            "sector": "Technology",
                            "country": "United States",
                            "price": 150.25,
                            "quantity": 67,
                            "final_target": 0.034,
                            "rank": 1,
                            "allocation": 0.034,
                            "screens": ["growth"],
                            "ibkr_details": {
                                "found": True,
                                "symbol": "AAPL",
                                "conId": 265598,
                                "exchange": "SMART",
                                "primaryExchange": "NASDAQ",
                                "currency": "USD",
                                "localSymbol": "AAPL",
                                "tradingClass": "AAPL"
                            }
                        }
                    ]
                }
            }
        }

        # Test target calculation
        targets = service.calculate_target_quantities(realistic_universe)
        assert "AAPL" in targets
        assert targets["AAPL"] == 67


if __name__ == "__main__":
    pytest.main([__file__, "-v"])