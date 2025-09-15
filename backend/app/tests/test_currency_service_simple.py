"""
Simple Currency Service Tests (Step 5)
Tests currency service in isolation without FastAPI app dependencies
"""

import pytest
import json
import tempfile
from unittest.mock import patch, mock_open, MagicMock
import sys
import os

# Add the backend directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_dir, '..'))
project_root = os.path.abspath(os.path.join(current_dir, '../../../..'))
sys.path.insert(0, backend_root)
sys.path.insert(0, project_root)

try:
    from app.services.implementations.currency_service import CurrencyService
except ImportError:
    # Alternative import if running from project root
    from backend.app.services.implementations.currency_service import CurrencyService


class TestCurrencyServiceSimple:
    """Test Currency Service implementation in isolation"""

    def setup_method(self):
        """Set up test environment"""
        self.service = CurrencyService()

    @patch('backend.app.services.implementations.legacy.currency.requests.get')
    def test_fetch_exchange_rates_success(self, mock_get):
        """Test successful exchange rate fetching"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'rates': {
                'USD': 1.0500,
                'GBP': 0.8500,
                'JPY': 140.0000
            }
        }
        mock_get.return_value = mock_response

        # Call service method
        with patch('builtins.print') as mock_print:
            result = self.service.fetch_exchange_rates()

        # Verify result
        assert isinstance(result, dict)
        assert 'EUR' in result
        assert result['EUR'] == 1.0
        assert result['USD'] == 1.0500
        assert result['GBP'] == 0.8500
        assert result['JPY'] == 140.0000

        # Verify console output
        mock_print.assert_called_with("+ Fetched exchange rates for 4 currencies")

    @patch('backend.app.services.implementations.legacy.currency.requests.get')
    def test_fetch_exchange_rates_api_error(self, mock_get):
        """Test exchange rate fetching with API error"""
        # Mock API error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        # Call service method
        with patch('builtins.print') as mock_print:
            result = self.service.fetch_exchange_rates()

        # Verify empty dict returned on error
        assert result == {}

        # Verify error console output
        mock_print.assert_called_with("X API returned status 500")

    def test_get_currencies_from_universe_success(self):
        """Test successful currency extraction from universe.json"""
        # Mock universe.json content
        universe_data = {
            "screens": {
                "screen1": {
                    "stocks": [
                        {"ticker": "AAPL", "currency": "USD"},
                        {"ticker": "GOOGL", "currency": "USD"},
                        {"ticker": "NESN", "currency": "CHF"}
                    ]
                }
            },
            "all_stocks": {
                "TSLA": {"ticker": "TSLA", "currency": "USD"},
                "SAP": {"ticker": "SAP", "currency": "EUR"},
                "ASML": {"ticker": "ASML", "currency": "EUR"}
            }
        }

        # Mock file operations
        mock_json_data = json.dumps(universe_data)
        with patch('builtins.open', mock_open(read_data=mock_json_data)), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.print') as mock_print:

            result = self.service.get_currencies_from_universe()

        # Verify result
        assert isinstance(result, set)
        expected_currencies = {'USD', 'EUR', 'CHF'}
        assert result == expected_currencies

        # Verify console output
        mock_print.assert_called_with("+ Found 3 unique currencies: CHF, EUR, USD")

    def test_update_universe_with_exchange_rates_success(self):
        """Test successful universe.json update with exchange rates"""
        # Mock existing universe data
        universe_data = {
            "screens": {
                "screen1": {
                    "stocks": [
                        {"ticker": "AAPL", "currency": "USD", "price": 150.0},
                        {"ticker": "NESN", "currency": "CHF", "price": 100.0}
                    ]
                }
            },
            "all_stocks": {
                "TSLA": {"ticker": "TSLA", "currency": "USD", "price": 200.0},
                "SAP": {"ticker": "SAP", "currency": "EUR", "price": 50.0}
            }
        }

        exchange_rates = {
            "USD": 1.0500,
            "EUR": 1.0000,
            "CHF": 0.9500
        }

        # Mock file operations
        mock_json_data = json.dumps(universe_data)
        with patch('builtins.open', mock_open(read_data=mock_json_data)) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=universe_data), \
             patch('json.dump') as mock_dump, \
             patch('builtins.print') as mock_print:

            result = self.service.update_universe_with_exchange_rates(exchange_rates)

        # Verify successful result
        assert result is True

        # Verify console output includes progress messages
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("+ Updated" in call and "stocks in screens" in call for call in print_calls)
        assert any("+ Updated" in call and "stocks in all_stocks" in call for call in print_calls)
        assert any("+ Total:" in call and "stocks updated with EUR exchange rates" in call for call in print_calls)

    @patch('backend.app.services.implementations.legacy.currency.main')
    def test_run_currency_update_success(self, mock_main):
        """Test successful currency update workflow"""
        # Mock successful workflow
        mock_main.return_value = True

        result = self.service.run_currency_update()

        # Verify result
        assert result is True
        mock_main.assert_called_once()


def test_cli_compatibility_direct():
    """Test that currency service wraps legacy functions correctly"""
    service = CurrencyService()

    # Test that all required methods exist and are callable
    assert hasattr(service, 'fetch_exchange_rates')
    assert callable(service.fetch_exchange_rates)

    assert hasattr(service, 'get_currencies_from_universe')
    assert callable(service.get_currencies_from_universe)

    assert hasattr(service, 'update_universe_with_exchange_rates')
    assert callable(service.update_universe_with_exchange_rates)

    assert hasattr(service, 'display_exchange_rate_summary')
    assert callable(service.display_exchange_rate_summary)

    assert hasattr(service, 'run_currency_update')
    assert callable(service.run_currency_update)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])