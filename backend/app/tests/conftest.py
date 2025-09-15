"""
Shared test configuration
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock
from ..main import app
from ..core.config import Settings

@pytest.fixture
def test_client():
    """Test client for FastAPI app"""
    return TestClient(app)

@pytest.fixture
def mock_uncle_stock_api():
    """Mock Uncle Stock API"""
    mock = AsyncMock()
    mock.fetch_screener_data.return_value = {
        "success": True,
        "data": ["AAPL", "GOOGL", "MSFT"],
        "csv_file": "test_screener.csv"
    }
    return mock

@pytest.fixture
def test_settings():
    """Test settings"""
    return Settings(
        uncle_stock_user_id="test_user",
        uncle_stock_timeout=30,
        environment="test"
    )

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()