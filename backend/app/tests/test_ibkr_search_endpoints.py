"""
Tests for IBKR Search API endpoints
Tests the REST API layer for the optimized search service
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import json
import time

from backend.app.main import app
from backend.app.api.v1.endpoints.ibkr_search import _running_tasks, get_ibkr_service


class TestIBKRSearchEndpoints:
    """Test IBKR Search API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def sample_stock_request(self):
        """Sample stock search request"""
        return {
            "ticker": "AAPL",
            "isin": "US0378331005",
            "name": "Apple Inc",
            "currency": "USD",
            "sector": "Technology",
            "country": "United States"
        }

    @pytest.fixture
    def sample_multiple_stocks_request(self):
        """Sample multiple stocks search request"""
        return {
            "stocks": [
                {
                    "ticker": "AAPL",
                    "isin": "US0378331005",
                    "name": "Apple Inc",
                    "currency": "USD",
                    "sector": "Technology",
                    "country": "United States"
                },
                {
                    "ticker": "GOOGL",
                    "isin": "US02079K3059",
                    "name": "Alphabet Inc",
                    "currency": "USD",
                    "sector": "Technology",
                    "country": "United States"
                }
            ],
            "max_concurrent": 3,
            "use_cache": True
        }

    @pytest.fixture
    def mock_ibkr_service(self):
        """Mock IBKR service for testing"""
        service = AsyncMock()
        service.search_single_stock.return_value = (
            {
                "symbol": "AAPL",
                "longName": "Apple Inc",
                "currency": "USD",
                "exchange": "NASDAQ",
                "primaryExchange": "NASDAQ",
                "conId": 12345,
                "search_method": "ticker",
                "match_score": 0.95
            },
            0.95
        )
        service.search_multiple_stocks.return_value = {
            "AAPL": (
                {
                    "symbol": "AAPL",
                    "longName": "Apple Inc",
                    "currency": "USD",
                    "exchange": "NASDAQ",
                    "primaryExchange": "NASDAQ",
                    "conId": 12345,
                    "search_method": "ticker",
                    "match_score": 0.95
                },
                0.95
            ),
            "GOOGL": (
                {
                    "symbol": "GOOGL",
                    "longName": "Alphabet Inc",
                    "currency": "USD",
                    "exchange": "NASDAQ",
                    "primaryExchange": "NASDAQ",
                    "conId": 12346,
                    "search_method": "isin",
                    "match_score": 0.98
                },
                0.98
            )
        }
        service.get_cache_statistics.return_value = {
            "cache_hits": 10,
            "cache_misses": 5,
            "hit_rate": 0.67,
            "total_cached_symbols": 8
        }
        service.clear_cache.return_value = True
        service.get_connection_pool_status.return_value = {
            "total_connections": 5,
            "available_connections": 3,
            "max_connections": 5,
            "connections_healthy": 5
        }
        return service

    def test_health_check(self, client):
        """Test API health check"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @patch('backend.app.api.v1.endpoints.ibkr_search.get_ibkr_service')
    def test_search_single_stock_found(self, mock_get_service, client, sample_stock_request, mock_ibkr_service):
        """Test single stock search - stock found"""
        mock_get_service.return_value = mock_ibkr_service

        response = client.post("/api/v1/ibkr/search/stock", json=sample_stock_request)

        assert response.status_code == 200
        data = response.json()

        assert data["ticker"] == "AAPL"
        assert data["found"] is True
        assert data["contract_details"]["symbol"] == "AAPL"
        assert data["contract_details"]["longName"] == "Apple Inc"
        assert data["contract_details"]["search_method"] == "ticker"
        assert data["similarity_score"] == 0.95

    @patch('backend.app.api.v1.endpoints.ibkr_search.get_ibkr_service')
    def test_search_single_stock_not_found(self, mock_get_service, client, sample_stock_request):
        """Test single stock search - stock not found"""
        mock_service = AsyncMock()
        mock_service.search_single_stock.return_value = (None, 0.0)
        mock_get_service.return_value = mock_service

        response = client.post("/api/v1/ibkr/search/stock", json=sample_stock_request)

        assert response.status_code == 200
        data = response.json()

        assert data["ticker"] == "AAPL"
        assert data["found"] is False
        assert data["contract_details"] is None
        assert data["similarity_score"] == 0.0

    @patch('backend.app.api.v1.endpoints.ibkr_search.get_ibkr_service')
    def test_search_single_stock_with_cache_param(self, mock_get_service, client, sample_stock_request, mock_ibkr_service):
        """Test single stock search with cache parameter"""
        mock_get_service.return_value = mock_ibkr_service

        response = client.post("/api/v1/ibkr/search/stock?use_cache=false", json=sample_stock_request)

        assert response.status_code == 200
        # Verify service was called with use_cache=False
        mock_ibkr_service.search_single_stock.assert_called_once()
        args, kwargs = mock_ibkr_service.search_single_stock.call_args
        assert kwargs.get('use_cache') is False

    @patch('backend.app.api.v1.endpoints.ibkr_search.get_ibkr_service')
    def test_search_multiple_stocks(self, mock_get_service, client, sample_multiple_stocks_request, mock_ibkr_service):
        """Test multiple stocks search"""
        mock_get_service.return_value = mock_ibkr_service

        response = client.post("/api/v1/ibkr/search/batch", json=sample_multiple_stocks_request)

        assert response.status_code == 200
        data = response.json()

        assert "AAPL" in data
        assert "GOOGL" in data

        aapl_result = data["AAPL"]
        assert aapl_result["found"] is True
        assert aapl_result["contract_details"]["symbol"] == "AAPL"

        googl_result = data["GOOGL"]
        assert googl_result["found"] is True
        assert googl_result["contract_details"]["symbol"] == "GOOGL"
        assert googl_result["contract_details"]["search_method"] == "isin"

    @patch('backend.app.api.v1.endpoints.ibkr_search.get_ibkr_service')
    def test_start_universe_search(self, mock_get_service, client, mock_ibkr_service):
        """Test starting universe search task"""
        mock_get_service.return_value = mock_ibkr_service

        request_data = {
            "universe_path": "data/universe.json",
            "output_path": "data/universe_with_ibkr.json",
            "max_concurrent": 5,
            "use_cache": True
        }

        response = client.post("/api/v1/ibkr/search/universe", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "task_id" in data
        assert "message" in data
        assert data["message"] == "Universe search started"

        # Check task was added to tracking
        task_id = data["task_id"]
        assert task_id in _running_tasks
        assert _running_tasks[task_id]["status"] == "running"

    def test_get_search_progress_not_found(self, client):
        """Test getting progress for non-existent task"""
        response = client.get("/api/v1/ibkr/search/progress/nonexistent-task")
        assert response.status_code == 404

    def test_get_search_progress_running_task(self, client):
        """Test getting progress for running task"""
        # Add a mock running task
        task_id = "test-task-123"
        _running_tasks[task_id] = {
            "status": "running",
            "progress": {"current": 5, "total": 10, "current_stock": "AAPL", "percentage": 50.0},
            "result": None,
            "error": None,
            "started_at": time.time(),
            "completed_at": None
        }

        response = client.get(f"/api/v1/ibkr/search/progress/{task_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "running"
        assert data["progress"]["current"] == 5
        assert data["progress"]["total"] == 10
        assert data["progress"]["current_stock"] == "AAPL"

        # Cleanup
        del _running_tasks[task_id]

    def test_get_search_results_completed_task(self, client):
        """Test getting results for completed task"""
        # Add a mock completed task
        task_id = "test-task-completed"
        mock_result = {
            "total": 100,
            "found_isin": 80,
            "found_ticker": 15,
            "found_name": 3,
            "not_found": 2,
            "execution_time_seconds": 180.5
        }

        _running_tasks[task_id] = {
            "status": "completed",
            "progress": {"current": 100, "total": 100, "current_stock": "", "percentage": 100.0},
            "result": mock_result,
            "error": None,
            "started_at": time.time() - 200,
            "completed_at": time.time()
        }

        response = client.get(f"/api/v1/ibkr/search/results/{task_id}")
        assert response.status_code == 200

        data = response.json()
        assert data == mock_result

        # Cleanup
        del _running_tasks[task_id]

    def test_get_search_results_running_task(self, client):
        """Test getting results for still running task"""
        task_id = "test-task-running"
        _running_tasks[task_id] = {
            "status": "running",
            "progress": {"current": 5, "total": 10, "current_stock": "AAPL", "percentage": 50.0},
            "result": None,
            "error": None,
            "started_at": time.time(),
            "completed_at": None
        }

        response = client.get(f"/api/v1/ibkr/search/results/{task_id}")
        assert response.status_code == 202

        # Cleanup
        del _running_tasks[task_id]

    def test_get_search_results_failed_task(self, client):
        """Test getting results for failed task"""
        task_id = "test-task-failed"
        _running_tasks[task_id] = {
            "status": "failed",
            "progress": {"current": 5, "total": 10, "current_stock": "AAPL", "percentage": 50.0},
            "result": None,
            "error": "Connection to IBKR failed",
            "started_at": time.time() - 100,
            "completed_at": time.time()
        }

        response = client.get(f"/api/v1/ibkr/search/results/{task_id}")
        assert response.status_code == 500

        # Cleanup
        del _running_tasks[task_id]

    @patch('backend.app.api.v1.endpoints.ibkr_search.get_ibkr_service')
    def test_get_cache_statistics(self, mock_get_service, client, mock_ibkr_service):
        """Test getting cache statistics"""
        mock_get_service.return_value = mock_ibkr_service

        response = client.get("/api/v1/ibkr/cache/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["cache_hits"] == 10
        assert data["cache_misses"] == 5
        assert data["hit_rate"] == 0.67
        assert data["total_cached_symbols"] == 8

    @patch('backend.app.api.v1.endpoints.ibkr_search.get_ibkr_service')
    def test_clear_cache(self, mock_get_service, client, mock_ibkr_service):
        """Test clearing cache"""
        mock_get_service.return_value = mock_ibkr_service

        response = client.delete("/api/v1/ibkr/cache")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "message" in data

    @patch('backend.app.api.v1.endpoints.ibkr_search.get_ibkr_service')
    def test_get_connection_pool_status(self, mock_get_service, client, mock_ibkr_service):
        """Test getting connection pool status"""
        mock_get_service.return_value = mock_ibkr_service

        response = client.get("/api/v1/ibkr/connections/status")
        assert response.status_code == 200

        data = response.json()
        assert data["total_connections"] == 5
        assert data["available_connections"] == 3
        assert data["max_connections"] == 5
        assert data["connections_healthy"] == 5

    @patch('os.path.exists')
    @patch('builtins.open')
    def test_get_universe_with_ibkr(self, mock_open, mock_exists, client):
        """Test getting universe with IBKR data"""
        mock_exists.return_value = True

        mock_universe_data = {
            "metadata": {"created_at": "2023-01-01"},
            "screens": {
                "tech": {
                    "stocks": [
                        {
                            "ticker": "AAPL",
                            "name": "Apple Inc",
                            "ibkr_details": {
                                "found": True,
                                "symbol": "AAPL",
                                "exchange": "NASDAQ"
                            }
                        }
                    ]
                }
            }
        }

        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_universe_data)

        response = client.get("/api/v1/ibkr/universe/with-ibkr")
        assert response.status_code == 200

        data = response.json()
        assert "metadata" in data
        assert "screens" in data

    @patch('os.path.exists')
    def test_get_universe_with_ibkr_not_found(self, mock_exists, client):
        """Test getting universe file that doesn't exist"""
        mock_exists.return_value = False

        response = client.get("/api/v1/ibkr/universe/with-ibkr")
        assert response.status_code == 404

    def test_cleanup_task(self, client):
        """Test cleaning up completed task"""
        # Add a completed task
        task_id = "test-task-cleanup"
        _running_tasks[task_id] = {
            "status": "completed",
            "progress": {"current": 100, "total": 100, "current_stock": "", "percentage": 100.0},
            "result": {"total": 100},
            "error": None,
            "started_at": time.time() - 300,
            "completed_at": time.time() - 100
        }

        response = client.delete(f"/api/v1/ibkr/tasks/{task_id}")
        assert response.status_code == 200

        # Verify task was removed
        assert task_id not in _running_tasks

    def test_cleanup_running_task(self, client):
        """Test trying to cleanup running task"""
        task_id = "test-task-running-cleanup"
        _running_tasks[task_id] = {
            "status": "running",
            "progress": {"current": 5, "total": 10, "current_stock": "AAPL", "percentage": 50.0},
            "result": None,
            "error": None,
            "started_at": time.time(),
            "completed_at": None
        }

        response = client.delete(f"/api/v1/ibkr/tasks/{task_id}")
        assert response.status_code == 400

        # Task should still exist
        assert task_id in _running_tasks

        # Cleanup
        del _running_tasks[task_id]

    def test_list_tasks(self, client):
        """Test listing all tasks"""
        # Add some test tasks
        task1_id = "test-task-1"
        task2_id = "test-task-2"

        _running_tasks[task1_id] = {
            "status": "running",
            "started_at": time.time(),
            "completed_at": None
        }

        _running_tasks[task2_id] = {
            "status": "completed",
            "started_at": time.time() - 300,
            "completed_at": time.time() - 100
        }

        response = client.get("/api/v1/ibkr/tasks")
        assert response.status_code == 200

        data = response.json()
        assert "tasks" in data
        assert len(data["tasks"]) >= 2

        task_ids = [task["task_id"] for task in data["tasks"]]
        assert task1_id in task_ids
        assert task2_id in task_ids

        # Cleanup
        del _running_tasks[task1_id]
        del _running_tasks[task2_id]

    def test_invalid_request_data(self, client):
        """Test handling of invalid request data"""
        # Missing required fields
        invalid_request = {
            "ticker": "AAPL"
            # Missing name and currency
        }

        response = client.post("/api/v1/ibkr/search/stock", json=invalid_request)
        assert response.status_code == 422  # Validation error

    @patch('backend.app.api.v1.endpoints.ibkr_search.get_ibkr_service')
    def test_service_error_handling(self, mock_get_service, client, sample_stock_request):
        """Test handling of service errors"""
        mock_service = AsyncMock()
        mock_service.search_single_stock.side_effect = Exception("IBKR connection failed")
        mock_get_service.return_value = mock_service

        response = client.post("/api/v1/ibkr/search/stock", json=sample_stock_request)
        assert response.status_code == 500

        data = response.json()
        assert "Search failed" in data["detail"]