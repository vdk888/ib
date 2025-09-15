"""
Integration tests for screener API endpoints
Tests the complete API layer for compatibility
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json

from ..main import app
from ..services.implementations.screener_service import ScreenerService

client = TestClient(app)


class TestScreenerEndpoints:
    """Test screener API endpoints"""

    @pytest.fixture
    def mock_screener_service(self):
        """Mock screener service for testing"""
        mock = AsyncMock(spec=ScreenerService)

        # Mock available screeners
        mock.get_available_screeners.return_value = {
            "quality_bloom": "quality bloom",
            "TOR_Surplus": "TOR Surplus",
            "Moat_Companies": "Moat Companies"
        }

        # Mock successful screener data
        mock.fetch_screener_data.return_value = {
            'success': True,
            'data': ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'],
            'raw_response': 'symbol,name\nAAPL,Apple\nGOOGL,Google\nMSFT,Microsoft',
            'csv_file': 'data/files_exports/quality_bloom_current_screen.csv',
            'screener_id': 'quality_bloom',
            'screener_name': 'quality bloom'
        }

        return mock

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "Uncle Stock Portfolio API" in data["message"]
        assert data["version"] == "1.0.0"

    def test_get_available_screeners(self):
        """Test getting available screeners"""
        with patch("backend.app.core.dependencies.get_screener_service") as mock_dep:
            mock_service = AsyncMock()
            mock_service.get_available_screeners.return_value = {
                "quality_bloom": "quality bloom",
                "TOR_Surplus": "TOR Surplus"
            }
            mock_dep.return_value = mock_service

            response = client.get("/api/v1/screeners/available")
            assert response.status_code == 200

            data = response.json()
            assert "screeners" in data
            assert data["total_count"] == 2
            assert "quality_bloom" in data["screeners"]

    def test_get_screener_data_success(self):
        """Test successful screener data fetch"""
        with patch("backend.app.core.dependencies.get_screener_service") as mock_dep:
            mock_service = AsyncMock()
            mock_service.fetch_screener_data.return_value = {
                'success': True,
                'data': ['AAPL', 'GOOGL', 'MSFT'],
                'raw_response': 'test,data',
                'csv_file': 'test.csv',
                'screener_id': 'quality_bloom',
                'screener_name': 'quality bloom'
            }
            mock_dep.return_value = mock_service

            response = client.get("/api/v1/screeners/data/quality_bloom?max_results=100")
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True
            assert data["data"] == ['AAPL', 'GOOGL', 'MSFT']
            assert data["symbol_count"] == 3
            assert data["screener_name"] == "quality bloom"

    def test_get_screener_data_not_found(self):
        """Test screener not found error"""
        with patch("backend.app.core.dependencies.get_screener_service") as mock_dep:
            from ..core.exceptions import UncleStockInvalidQueryError

            mock_service = AsyncMock()
            mock_service.fetch_screener_data.side_effect = UncleStockInvalidQueryError(
                "Unknown screener ID: invalid_screener"
            )
            mock_dep.return_value = mock_service

            response = client.get("/api/v1/screeners/data/invalid_screener")
            assert response.status_code == 404
            assert "Screener not found" in response.json()["detail"]

    def test_get_all_screener_data(self):
        """Test fetching all screener data"""
        with patch("backend.app.core.dependencies.get_screener_service") as mock_dep:
            mock_service = AsyncMock()
            mock_service.fetch_all_screener_data.return_value = {
                "quality_bloom": {
                    'success': True,
                    'data': ['AAPL', 'GOOGL'],
                    'raw_response': 'test_data',
                    'csv_file': 'quality_bloom.csv',
                    'screener_id': 'quality_bloom',
                    'screener_name': 'quality bloom'
                },
                "TOR_Surplus": {
                    'success': False,
                    'data': 'API Error',
                    'raw_response': None,
                    'screener_id': 'TOR_Surplus',
                    'screener_name': 'TOR Surplus'
                }
            }
            mock_dep.return_value = mock_service

            response = client.get("/api/v1/screeners/data")
            assert response.status_code == 200

            data = response.json()
            assert data["total_screeners"] == 2
            assert data["successful_screeners"] == 1
            assert data["total_symbols"] == 2  # Only successful screeners count

            # Check individual screener data
            assert "quality_bloom" in data["screeners"]
            assert data["screeners"]["quality_bloom"]["success"] is True
            assert data["screeners"]["quality_bloom"]["symbol_count"] == 2

    def test_get_screener_history(self):
        """Test fetching screener history"""
        with patch("backend.app.core.dependencies.get_screener_service") as mock_dep:
            mock_service = AsyncMock()
            mock_service.fetch_screener_history.return_value = {
                'success': True,
                'data': {'total_return': '25.5%', 'sharpe_ratio': '1.2'},
                'raw_response': 'total_return,25.5%\nsharpe_ratio,1.2',
                'csv_file': 'quality_bloom_backtest_results.csv',
                'screener_id': 'quality_bloom',
                'screener_name': 'quality bloom'
            }
            mock_dep.return_value = mock_service

            response = client.get("/api/v1/screeners/history/quality_bloom")
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True
            assert isinstance(data["data"], dict)
            assert data["screener_name"] == "quality bloom"

    def test_legacy_endpoints(self):
        """Test legacy compatibility endpoints"""
        with patch("backend.app.core.dependencies.get_screener_service") as mock_dep:
            mock_service = AsyncMock()
            mock_service.fetch_screener_data.return_value = {
                'success': True,
                'data': ['AAPL', 'GOOGL'],
                'raw_response': 'test,data',
                'csv_file': 'test.csv'
            }
            mock_dep.return_value = mock_service

            # Test legacy data endpoint
            response = client.get("/api/v1/screeners/legacy/data/quality_bloom")
            assert response.status_code == 200

            data = response.json()
            # Verify exact legacy structure
            required_keys = {"success", "data", "raw_response", "csv_file"}
            assert all(key in data for key in required_keys)
            assert data["success"] is True
            assert data["data"] == ['AAPL', 'GOOGL']

    def test_api_timeout_handling(self):
        """Test API timeout error handling"""
        with patch("backend.app.core.dependencies.get_screener_service") as mock_dep:
            from ..core.exceptions import UncleStockTimeoutError

            mock_service = AsyncMock()
            mock_service.fetch_screener_data.side_effect = UncleStockTimeoutError(
                "Uncle Stock API request timed out"
            )
            mock_dep.return_value = mock_service

            response = client.get("/api/v1/screeners/data/quality_bloom")
            assert response.status_code == 503
            assert "temporarily unavailable" in response.json()["detail"]

    def test_api_rate_limit_handling(self):
        """Test API rate limit error handling"""
        with patch("backend.app.core.dependencies.get_screener_service") as mock_dep:
            from ..core.exceptions import UncleStockRateLimitError

            mock_service = AsyncMock()
            mock_service.fetch_screener_data.side_effect = UncleStockRateLimitError(
                "Uncle Stock API rate limit exceeded"
            )
            mock_dep.return_value = mock_service

            response = client.get("/api/v1/screeners/data/quality_bloom")
            assert response.status_code == 429
            assert "rate limit exceeded" in response.json()["detail"]


class TestParameterValidation:
    """Test API parameter validation"""

    def test_max_results_validation(self):
        """Test max_results parameter validation"""
        with patch("backend.app.core.dependencies.get_screener_service") as mock_dep:
            mock_service = AsyncMock()
            mock_dep.return_value = mock_service

            # Test upper limit
            response = client.get("/api/v1/screeners/data/quality_bloom?max_results=1001")
            assert response.status_code == 422  # Validation error

            # Test lower limit
            response = client.get("/api/v1/screeners/data/quality_bloom?max_results=0")
            assert response.status_code == 422  # Validation error

            # Test valid value
            mock_service.fetch_screener_data.return_value = {
                'success': True,
                'data': [],
                'raw_response': '',
                'csv_file': ''
            }
            response = client.get("/api/v1/screeners/data/quality_bloom?max_results=500")
            assert response.status_code == 200

    def test_screener_id_path_parameter(self):
        """Test screener_id path parameter handling"""
        with patch("backend.app.core.dependencies.get_screener_service") as mock_dep:
            mock_service = AsyncMock()
            mock_service.fetch_screener_data.return_value = {
                'success': True,
                'data': [],
                'raw_response': '',
                'csv_file': '',
                'screener_id': 'test-screener',
                'screener_name': 'Test Screener'
            }
            mock_dep.return_value = mock_service

            # Test with various screener ID formats
            response = client.get("/api/v1/screeners/data/test-screener-123")
            assert response.status_code == 200

            # Verify the screener_id was passed correctly
            mock_service.fetch_screener_data.assert_called_with(
                screener_id="test-screener-123",
                max_results=200  # default value
            )