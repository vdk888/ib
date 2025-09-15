"""
Tests for the screener service implementation
Ensures 100% behavioral compatibility with legacy implementation
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from typing import Dict, Any

from ..services.implementations.screener_service import ScreenerService
from ..services.implementations.uncle_stock_provider import UncleStockProvider
from ..services.implementations.file_manager import FileManager
from ..core.exceptions import UncleStockInvalidQueryError


class TestScreenerService:
    """Test screener service with focus on legacy compatibility"""

    @pytest.fixture
    def mock_file_manager(self):
        """Mock file manager"""
        mock = Mock(spec=FileManager)
        mock.save_csv_data.return_value = "data/files_exports/test.csv"
        mock.sanitize_filename.return_value = "test_query"
        mock.get_csv_filename.return_value = "test_query_current_screen.csv"
        return mock

    @pytest.fixture
    def mock_uncle_stock_provider(self):
        """Mock Uncle Stock provider"""
        mock = AsyncMock(spec=UncleStockProvider)

        # Mock successful response
        mock_response = {
            'success': True,
            'data': ['AAPL', 'GOOGL', 'MSFT'],
            'raw_response': 'symbol,price\nAAPL,150\nGOOGL,2800\nMSFT,300',
            'csv_file': 'data/files_exports/test_current_screen.csv'
        }
        mock.get_current_stocks.return_value = mock_response

        # Mock configurations
        mock.get_screener_configurations.return_value = {
            "quality_bloom": "quality bloom",
            "TOR_Surplus": "TOR Surplus",
            "Moat_Companies": "Moat Companies"
        }

        return mock

    @pytest.fixture
    def screener_service(self, mock_uncle_stock_provider, mock_file_manager):
        """Create screener service with mocked dependencies"""
        return ScreenerService(
            data_provider=mock_uncle_stock_provider,
            file_manager=mock_file_manager
        )

    @pytest.mark.asyncio
    async def test_fetch_screener_data_success(self, screener_service, mock_uncle_stock_provider):
        """Test successful screener data fetch"""
        # Act
        result = await screener_service.fetch_screener_data("quality_bloom", max_results=100)

        # Assert
        assert result["success"] is True
        assert result["data"] == ['AAPL', 'GOOGL', 'MSFT']
        assert result["screener_id"] == "quality_bloom"
        assert result["screener_name"] == "quality bloom"
        assert "csv_file" in result

        # Verify provider was called correctly
        mock_uncle_stock_provider.get_current_stocks.assert_called_once_with(
            query_name="quality bloom",
            max_results=100
        )

    @pytest.mark.asyncio
    async def test_fetch_screener_data_invalid_screener(self, screener_service):
        """Test fetch with invalid screener ID"""
        # Act & Assert
        with pytest.raises(UncleStockInvalidQueryError) as exc_info:
            await screener_service.fetch_screener_data("invalid_screener")

        assert "Unknown screener ID: invalid_screener" in str(exc_info.value)
        assert "quality_bloom, TOR_Surplus, Moat_Companies" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_all_screener_data(self, screener_service, mock_uncle_stock_provider):
        """Test fetching all screener data"""
        # Setup mock to return different data for each screener
        all_screeners_response = {
            "quality_bloom": {
                'success': True,
                'data': ['AAPL', 'GOOGL'],
                'raw_response': 'test_data',
                'csv_file': 'quality_bloom.csv'
            },
            "TOR_Surplus": {
                'success': True,
                'data': ['MSFT', 'TSLA'],
                'raw_response': 'test_data',
                'csv_file': 'tor_surplus.csv'
            },
            "Moat_Companies": {
                'success': False,
                'data': 'API Error',
                'raw_response': None
            }
        }
        mock_uncle_stock_provider.get_all_screeners.return_value = all_screeners_response

        # Act
        result = await screener_service.fetch_all_screener_data()

        # Assert
        assert len(result) == 3
        assert result["quality_bloom"]["success"] is True
        assert result["quality_bloom"]["data"] == ['AAPL', 'GOOGL']
        assert result["quality_bloom"]["screener_id"] == "quality_bloom"
        assert result["quality_bloom"]["screener_name"] == "quality bloom"

        assert result["TOR_Surplus"]["success"] is True
        assert result["TOR_Surplus"]["data"] == ['MSFT', 'TSLA']

        assert result["Moat_Companies"]["success"] is False
        assert result["Moat_Companies"]["data"] == 'API Error'

    @pytest.mark.asyncio
    async def test_get_available_screeners(self, screener_service):
        """Test getting available screeners"""
        # Act
        result = screener_service.get_available_screeners()

        # Assert
        expected = {
            "quality_bloom": "quality bloom",
            "TOR_Surplus": "TOR Surplus",
            "Moat_Companies": "Moat Companies"
        }
        assert result == expected


class TestLegacyCompatibility:
    """Tests specifically focused on legacy compatibility"""

    @pytest.mark.asyncio
    async def test_return_structure_matches_legacy(self, screener_service, mock_uncle_stock_provider):
        """Test that return structure exactly matches legacy implementation"""
        # Setup mock response matching legacy format exactly
        legacy_response = {
            'success': True,
            'data': ['AAPL', 'GOOGL', 'MSFT'],
            'raw_response': 'symbol,name\nAAPL,Apple Inc\nGOOGL,Alphabet Inc\nMSFT,Microsoft Corp',
            'csv_file': 'data/files_exports/quality_bloom_current_screen.csv'
        }
        mock_uncle_stock_provider.get_current_stocks.return_value = legacy_response

        # Act
        result = await screener_service.fetch_screener_data("quality_bloom")

        # Assert - verify exact structure match
        required_keys = {'success', 'data', 'raw_response', 'csv_file'}
        assert all(key in result for key in required_keys)

        # Enhanced keys should also be present
        assert 'screener_id' in result
        assert 'screener_name' in result

        # Verify data types match legacy
        assert isinstance(result['success'], bool)
        assert isinstance(result['data'], list)
        assert isinstance(result['raw_response'], str)
        assert isinstance(result['csv_file'], str)

    @pytest.mark.asyncio
    async def test_error_format_matches_legacy(self, screener_service, mock_uncle_stock_provider):
        """Test that error format matches legacy implementation"""
        # Setup mock error response
        error_response = {
            'success': False,
            'data': "API returned status 500",
            'raw_response': 'Internal Server Error'
        }
        mock_uncle_stock_provider.get_current_stocks.return_value = error_response

        # Act
        result = await screener_service.fetch_screener_data("quality_bloom")

        # Assert
        assert result['success'] is False
        assert isinstance(result['data'], str)  # Error message as string
        assert 'API returned status 500' in result['data']


class TestFileManagerIntegration:
    """Test file manager integration"""

    def test_sanitize_filename_legacy_compatibility(self):
        """Test filename sanitization matches legacy behavior"""
        file_manager = FileManager()

        # Test cases from legacy implementation
        test_cases = [
            ("quality bloom", "quality_bloom"),
            ("TOR Surplus", "TOR_Surplus"),
            ("test/query with spaces", "test_query_with_spaces"),
            ("simple", "simple")
        ]

        for input_name, expected in test_cases:
            result = file_manager.sanitize_filename(input_name)
            assert result == expected

    def test_csv_filename_generation(self):
        """Test CSV filename generation matches legacy format"""
        file_manager = FileManager()

        # Test current screen file naming
        result = file_manager.get_csv_filename("quality bloom", "current_screen")
        assert result == "quality_bloom_current_screen.csv"

        # Test backtest results file naming
        result = file_manager.get_csv_filename("TOR Surplus", "backtest_results")
        assert result == "TOR_Surplus_backtest_results.csv"