"""
Comprehensive tests for Currency Service (Step 5)
Tests maintain 100% behavioral compatibility with CLI implementation
"""

import pytest
import json
import os
import tempfile
from unittest.mock import patch, mock_open, MagicMock
from fastapi.testclient import TestClient

from backend.app.services.implementations.currency_service import CurrencyService
from backend.app.main import app


class TestCurrencyService:
    """Test Currency Service implementation"""

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
        assert 'USD' in result
        assert 'GBP' in result
        assert 'JPY' in result

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

    @patch('backend.app.services.implementations.legacy.currency.requests.get')
    def test_fetch_exchange_rates_network_error(self, mock_get):
        """Test exchange rate fetching with network error"""
        # Mock network exception
        mock_get.side_effect = Exception("Network timeout")

        # Call service method
        with patch('builtins.print') as mock_print:
            result = self.service.fetch_exchange_rates()

        # Verify empty dict returned on exception
        assert result == {}

        # Verify error console output
        mock_print.assert_called_with("X Error fetching exchange rates: Network timeout")

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

    def test_get_currencies_from_universe_file_not_found(self):
        """Test currency extraction when universe.json doesn't exist"""
        # Mock file not found
        with patch('os.path.exists', return_value=False), \
             patch('builtins.print') as mock_print:

            result = self.service.get_currencies_from_universe()

        # Verify empty set returned
        assert result == set()

        # Verify error console output
        mock_print.assert_called_with("X data/universe.json not found")

    def test_get_currencies_from_universe_json_error(self):
        """Test currency extraction with JSON parsing error"""
        # Mock invalid JSON
        invalid_json = "invalid json content"

        with patch('builtins.open', mock_open(read_data=invalid_json)), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.print') as mock_print:

            result = self.service.get_currencies_from_universe()

        # Verify empty set returned
        assert result == set()

        # Verify error console output (partial match due to JSON error details)
        assert any("X Error reading universe.json:" in str(call) for call in mock_print.call_args_list)

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
        expected_calls = [
            "X Warning: Missing exchange rates for currencies: ",
            "+ Updated 2 stocks in screens",
            "+ Updated 2 stocks in all_stocks",
            "+ Total: 4 stocks updated with EUR exchange rates"
        ]

        # Check that key progress messages were printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("+ Updated" in call and "stocks in screens" in call for call in print_calls)
        assert any("+ Updated" in call and "stocks in all_stocks" in call for call in print_calls)
        assert any("+ Total:" in call and "stocks updated with EUR exchange rates" in call for call in print_calls)

    def test_update_universe_with_exchange_rates_file_not_found(self):
        """Test universe update when file doesn't exist"""
        exchange_rates = {"USD": 1.0500, "EUR": 1.0000}

        with patch('os.path.exists', return_value=False), \
             patch('builtins.print') as mock_print:

            result = self.service.update_universe_with_exchange_rates(exchange_rates)

        # Verify failure result
        assert result is False

        # Verify error console output
        mock_print.assert_called_with("X data/universe.json not found")

    def test_display_exchange_rate_summary(self):
        """Test exchange rate summary display"""
        exchange_rates = {
            "USD": 1.0500,
            "EUR": 1.0000,
            "GBP": 0.8500,
            "JPY": 140.0000
        }

        with patch('builtins.print') as mock_print:
            self.service.display_exchange_rate_summary(exchange_rates)

        # Verify console output structure
        print_calls = [call.args[0] for call in mock_print.call_args_list]

        # Check header
        assert "\n" + "=" * 50 in print_calls
        assert "EXCHANGE RATES TO EUR" in print_calls
        assert "=" * 50 in print_calls

        # Check currency entries (alphabetically sorted)
        assert any("EUR: 1.0000 (base currency)" in call for call in print_calls)
        assert any("GBP: 0.8500 (1 EUR = 0.8500 GBP)" in call for call in print_calls)
        assert any("JPY: 140.0000 (1 EUR = 140.0000 JPY)" in call for call in print_calls)
        assert any("USD: 1.0500 (1 EUR = 1.0500 USD)" in call for call in print_calls)

    @patch('backend.app.services.implementations.legacy.currency.main')
    def test_run_currency_update_success(self, mock_main):
        """Test successful currency update workflow"""
        # Mock successful workflow
        mock_main.return_value = True

        result = self.service.run_currency_update()

        # Verify result
        assert result is True
        mock_main.assert_called_once()

    @patch('backend.app.services.implementations.legacy.currency.main')
    def test_run_currency_update_failure(self, mock_main):
        """Test failed currency update workflow"""
        # Mock failed workflow
        mock_main.return_value = False

        result = self.service.run_currency_update()

        # Verify result
        assert result is False
        mock_main.assert_called_once()


class TestCurrencyAPIEndpoints:
    """Test Currency API endpoints"""

    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)

    @patch('backend.app.services.implementations.legacy.currency.requests.get')
    def test_fetch_exchange_rates_endpoint_success(self, mock_get):
        """Test GET /api/v1/currency/rates endpoint success"""
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

        with patch('builtins.print'):
            response = self.client.get("/api/v1/currency/rates")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["exchange_rates"] is not None
        assert "EUR" in data["exchange_rates"]["rates"]
        assert data["exchange_rates"]["base_currency"] == "EUR"

    @patch('backend.app.services.implementations.legacy.currency.requests.get')
    def test_fetch_exchange_rates_endpoint_failure(self, mock_get):
        """Test GET /api/v1/currency/rates endpoint failure"""
        # Mock API failure
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        with patch('builtins.print'):
            response = self.client.get("/api/v1/currency/rates")

        # Verify error response
        assert response.status_code == 200  # HTTP 200 but success=False in body
        data = response.json()
        assert data["success"] is False
        assert data["error_message"] == "Failed to fetch exchange rates from external API"

    def test_get_currencies_from_universe_endpoint_success(self):
        """Test GET /api/v1/universe/currencies endpoint success"""
        # Mock universe data
        universe_data = {
            "screens": {
                "screen1": {
                    "stocks": [{"ticker": "AAPL", "currency": "USD"}]
                }
            },
            "all_stocks": {
                "SAP": {"ticker": "SAP", "currency": "EUR"}
            }
        }

        mock_json_data = json.dumps(universe_data)
        with patch('builtins.open', mock_open(read_data=mock_json_data)), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.print'):

            response = self.client.get("/api/v1/universe/currencies")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert set(data["currencies"]) == {"EUR", "USD"}
        assert data["currency_count"] == 2

    def test_update_universe_with_exchange_rates_endpoint_success(self):
        """Test POST /api/v1/currency/update-universe endpoint success"""
        # Mock universe data and file operations
        universe_data = {
            "screens": {
                "screen1": {
                    "stocks": [{"ticker": "AAPL", "currency": "USD"}]
                }
            },
            "all_stocks": {
                "SAP": {"ticker": "SAP", "currency": "EUR"}
            }
        }

        exchange_rates = {"USD": 1.0500, "EUR": 1.0000}

        mock_json_data = json.dumps(universe_data)
        with patch('builtins.open', mock_open(read_data=mock_json_data)), \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=universe_data), \
             patch('json.dump'), \
             patch('builtins.print'):

            response = self.client.post(
                "/api/v1/currency/update-universe",
                json=exchange_rates
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch('backend.app.services.implementations.legacy.currency.main')
    def test_run_currency_update_workflow_endpoint_success(self, mock_main):
        """Test POST /api/v1/currency/update endpoint success"""
        # Mock successful workflow
        mock_main.return_value = True

        response = self.client.post("/api/v1/currency/update")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "successfully added" in data["workflow_message"]

    @patch('backend.app.services.implementations.legacy.currency.main')
    def test_run_currency_update_workflow_endpoint_failure(self, mock_main):
        """Test POST /api/v1/currency/update endpoint failure"""
        # Mock failed workflow
        mock_main.return_value = False

        response = self.client.post("/api/v1/currency/update")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "failed" in data["workflow_message"]


class TestCurrencyServiceCLICompatibility:
    """Test CLI vs API behavior compatibility"""

    def setup_method(self):
        """Set up test environment"""
        self.service = CurrencyService()

    def test_identical_return_types(self):
        """Test that service methods return identical types as legacy functions"""
        with patch('backend.app.services.implementations.legacy.currency.requests.get') as mock_get:
            # Mock successful API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'rates': {'USD': 1.05}}
            mock_get.return_value = mock_response

            with patch('builtins.print'):
                result = self.service.fetch_exchange_rates()
                assert isinstance(result, dict)

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='{"screens": {}, "all_stocks": {}}')), \
             patch('builtins.print'):

            result = self.service.get_currencies_from_universe()
            assert isinstance(result, set)

    def test_identical_console_output_patterns(self):
        """Test that console output matches CLI patterns exactly"""
        with patch('backend.app.services.implementations.legacy.currency.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'rates': {'USD': 1.05}}
            mock_get.return_value = mock_response

            with patch('builtins.print') as mock_print:
                self.service.fetch_exchange_rates()

            # Check for exact CLI output pattern
            mock_print.assert_called_with("+ Fetched exchange rates for 2 currencies")

    def test_identical_error_handling(self):
        """Test that error handling matches CLI behavior exactly"""
        # Test file not found scenario
        with patch('os.path.exists', return_value=False), \
             patch('builtins.print') as mock_print:

            result = self.service.get_currencies_from_universe()

        assert result == set()
        mock_print.assert_called_with("X data/universe.json not found")

        # Test API error scenario
        with patch('backend.app.services.implementations.legacy.currency.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            with patch('builtins.print') as mock_print:
                result = self.service.fetch_exchange_rates()

            assert result == {}
            mock_print.assert_called_with("X API returned status 404")


if __name__ == "__main__":
    pytest.main([__file__])