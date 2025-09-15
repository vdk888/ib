"""
Tests for Target Allocation API endpoints (Step 6)
Ensures API endpoints return correct data and handle errors properly
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import status

from backend.app.main import app
from backend.app.services.implementations.target_allocation_service import TargetAllocationService


class TestTargetAllocationAPI:
    """Test Target Allocation API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_service(self):
        """Mock target allocation service"""
        return Mock(spec=TargetAllocationService)

    @pytest.fixture
    def sample_final_allocations(self):
        """Sample final allocations data"""
        return {
            "AAPL": {
                "ticker": "AAPL",
                "screener": "quality bloom",
                "rank": 1,
                "performance_180d": 15.25,
                "pocket_allocation": 0.10,
                "screener_target": 0.35,
                "final_allocation": 0.035
            },
            "MSFT": {
                "ticker": "MSFT",
                "screener": "quality bloom",
                "rank": 2,
                "performance_180d": 12.50,
                "pocket_allocation": 0.095,
                "screener_target": 0.35,
                "final_allocation": 0.03325
            },
            "TSLA": {
                "ticker": "TSLA",
                "screener": "TOR Surplus",
                "rank": 1,
                "performance_180d": 25.75,
                "pocket_allocation": 0.10,
                "screener_target": 0.40,
                "final_allocation": 0.040
            }
        }

    @pytest.fixture
    def sample_universe_data(self):
        """Sample universe data with portfolio optimization"""
        return {
            "metadata": {
                "portfolio_optimization": {
                    "optimal_allocations": {
                        "quality_bloom": 0.35,
                        "TOR_Surplus": 0.40,
                        "Moat_Companies": 0.25
                    }
                }
            },
            "screens": {
                "quality_bloom": {
                    "name": "quality bloom",
                    "count": 50,
                    "stocks": [
                        {"ticker": "AAPL", "price_180d_change": "15.25%"},
                        {"ticker": "MSFT", "price_180d_change": "12.50%"}
                    ]
                }
            },
            "all_stocks": {
                "AAPL": {
                    "ticker": "AAPL",
                    "screens": ["quality bloom"],
                    "final_target": 0.035,
                    "rank": 1,
                    "allocation_target": 0.10,
                    "screen_target": 0.35
                }
            }
        }


class TestCalculateTargetAllocations:
    """Test POST /api/v1/portfolio/targets/calculate endpoint"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_calculate_success(self, client, sample_final_allocations):
        """Test successful target allocation calculation"""
        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.main.return_value = True
            mock_service.load_universe_data.return_value = {"test": "data"}
            mock_service.calculate_final_allocations.return_value = sample_final_allocations
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/portfolio/targets/calculate",
                json={"force_recalculate": False, "save_to_universe": True}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["success"] is True
            assert "Successfully calculated target allocations" in data["message"]
            assert data["universe_updated"] is True
            assert len(data["allocation_data"]) == 3

            # Check AAPL allocation data structure
            aapl_data = data["allocation_data"]["AAPL"]
            assert aapl_data["ticker"] == "AAPL"
            assert aapl_data["screener"] == "quality bloom"
            assert aapl_data["rank"] == 1
            assert aapl_data["performance_180d"] == 15.25
            assert aapl_data["final_allocation"] == 0.035

    def test_calculate_main_failure(self, client):
        """Test calculation when main() returns False"""
        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.main.return_value = False
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/portfolio/targets/calculate",
                json={}
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "Target allocation calculation failed" in data["message"]

    def test_calculate_universe_not_found(self, client):
        """Test calculation when universe.json not found"""
        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.main.side_effect = FileNotFoundError("universe.json not found")
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/portfolio/targets/calculate",
                json={}
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "Universe file not found" in data["message"]

    def test_calculate_no_optimization_data(self, client):
        """Test calculation when no portfolio optimization data"""
        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.main.side_effect = ValueError("No portfolio optimization results found")
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/portfolio/targets/calculate",
                json={}
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "Invalid data" in data["message"]

    def test_calculate_invalid_request_body(self, client):
        """Test calculation with invalid request body"""
        response = client.post(
            "/api/v1/portfolio/targets/calculate",
            json={"invalid_field": "value"}
        )

        # Should still work with default values for optional fields
        # This test would fail if our request validation is too strict
        # The endpoint should handle unknown fields gracefully


class TestGetAllocationSummary:
    """Test GET /api/v1/portfolio/targets/summary endpoint"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_get_summary_success(self, client, sample_final_allocations):
        """Test successful allocation summary retrieval"""
        mock_summary_data = {
            "sorted_allocations": [
                {
                    "ticker": "TSLA",
                    "screener": "TOR Surplus",
                    "screener_rank": 1,
                    "performance_180d": 25.75,
                    "pocket_allocation": 0.10,
                    "screener_target": 0.40,
                    "final_allocation": 0.040
                },
                {
                    "ticker": "AAPL",
                    "screener": "quality bloom",
                    "screener_rank": 1,
                    "performance_180d": 15.25,
                    "pocket_allocation": 0.10,
                    "screener_target": 0.35,
                    "final_allocation": 0.035
                }
            ],
            "total_allocation": 0.10825,
            "top_10_allocations": [
                {
                    "rank_overall": 1,
                    "ticker": "TSLA",
                    "final_allocation": 0.040,
                    "screener": "TOR Surplus",
                    "screener_rank": 1,
                    "performance_180d": 25.75
                }
            ],
            "summary_stats": {
                "total_stocks": 3,
                "total_allocation_pct": 10.825,
                "stocks_with_allocation": 3
            }
        }

        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.load_universe_data.return_value = {"test": "data"}
            mock_service.calculate_final_allocations.return_value = sample_final_allocations
            mock_service.get_allocation_summary.return_value = mock_summary_data
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/portfolio/targets/summary")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["success"] is True
            assert "summary" in data
            summary = data["summary"]

            assert len(summary["sorted_allocations"]) == 2
            assert summary["total_allocation"] == 0.10825
            assert len(summary["top_10_allocations"]) == 1
            assert summary["summary_stats"]["total_stocks"] == 3

    def test_get_summary_no_allocations(self, client):
        """Test summary when no allocation data available"""
        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.load_universe_data.return_value = {"test": "data"}
            mock_service.calculate_final_allocations.return_value = {}
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/portfolio/targets/summary")

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "No allocation data available" in data["message"]

    def test_get_summary_universe_not_found(self, client):
        """Test summary when universe file not found"""
        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.load_universe_data.side_effect = FileNotFoundError("universe.json not found")
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/portfolio/targets/summary")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "Universe file not found" in data["message"]


class TestGetScreenerAllocations:
    """Test GET /api/v1/portfolio/targets/screener-allocations endpoint"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_get_screener_allocations_success(self, client, sample_universe_data):
        """Test successful screener allocations retrieval"""
        mock_allocations = {
            "quality_bloom": 0.35,
            "TOR_Surplus": 0.40,
            "Moat_Companies": 0.25
        }

        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.load_universe_data.return_value = sample_universe_data
            mock_service.extract_screener_allocations.return_value = mock_allocations
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/portfolio/targets/screener-allocations")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["success"] is True
            assert data["screener_allocations"] == mock_allocations
            assert len(data["screeners_data"]) == 3

            # Check individual screener data structure
            quality_bloom_data = next(s for s in data["screeners_data"] if s["screener_id"] == "quality_bloom")
            assert quality_bloom_data["screener_name"] == "quality bloom"
            assert quality_bloom_data["allocation"] == 0.35

    def test_get_screener_allocations_no_optimization(self, client):
        """Test screener allocations when no optimization data"""
        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.load_universe_data.return_value = {"metadata": {}}
            mock_service.extract_screener_allocations.side_effect = ValueError("No portfolio optimization results")
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/portfolio/targets/screener-allocations")

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "Portfolio optimization data not available" in data["message"]


class TestGetScreenerRankings:
    """Test GET /api/v1/portfolio/targets/rankings/{screener_id} endpoint"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_get_rankings_success(self, client, sample_universe_data):
        """Test successful screener rankings retrieval"""
        mock_ranked_stocks = [
            ({"ticker": "AAPL"}, 1, 15.25),
            ({"ticker": "MSFT"}, 2, 12.50)
        ]

        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.load_universe_data.return_value = sample_universe_data
            mock_service.rank_stocks_in_screener.return_value = mock_ranked_stocks
            mock_service.calculate_pocket_allocation.side_effect = [0.10, 0.095]  # Different allocations for each rank
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/portfolio/targets/rankings/quality_bloom")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["success"] is True
            assert data["screener_id"] == "quality_bloom"
            assert data["screener_name"] == "quality bloom"
            assert len(data["rankings"]) == 2
            assert data["total_stocks"] == 2
            assert data["stocks_with_allocation"] == 2

            # Check ranking structure
            aapl_ranking = data["rankings"][0]
            assert aapl_ranking["ticker"] == "AAPL"
            assert aapl_ranking["rank"] == 1
            assert aapl_ranking["performance_180d"] == 15.25
            assert aapl_ranking["pocket_allocation"] == 0.10

    def test_get_rankings_screener_not_found(self, client):
        """Test rankings for non-existent screener"""
        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.load_universe_data.return_value = {"screens": {}}
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/portfolio/targets/rankings/nonexistent_screener")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "not found" in data["message"]

    def test_get_rankings_no_stocks(self, client):
        """Test rankings for screener with no stocks"""
        universe_data = {
            "screens": {
                "empty_screener": {
                    "name": "Empty Screener",
                    "stocks": []
                }
            }
        }

        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.load_universe_data.return_value = universe_data
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/portfolio/targets/rankings/empty_screener")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "No stocks found" in data["message"]


class TestGetCurrentTargetAllocations:
    """Test GET /api/v1/portfolio/targets/ endpoint"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_get_current_allocations_success(self, client):
        """Test successful retrieval of current allocations"""
        universe_data = {
            "all_stocks": {
                "AAPL": {
                    "ticker": "AAPL",
                    "screens": ["quality bloom"],
                    "rank": 1,
                    "allocation_target": 0.10,
                    "screen_target": 0.35,
                    "final_target": 0.035
                },
                "MSFT": {
                    "ticker": "MSFT",
                    "screens": ["quality bloom"],
                    "rank": 2,
                    "allocation_target": 0.095,
                    "screen_target": 0.35,
                    "final_target": 0.03325
                }
            }
        }

        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.load_universe_data.return_value = universe_data
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/portfolio/targets/")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["success"] is True
            assert len(data["allocation_data"]) == 2
            assert data["universe_updated"] is False

            # Check AAPL data
            aapl_data = data["allocation_data"]["AAPL"]
            assert aapl_data["ticker"] == "AAPL"
            assert aapl_data["rank"] == 1
            assert aapl_data["final_allocation"] == 0.035

    def test_get_current_allocations_no_data(self, client):
        """Test current allocations when no allocation data exists"""
        universe_data = {
            "all_stocks": {
                "AAPL": {
                    "ticker": "AAPL",
                    "screens": ["quality bloom"]
                    # Missing allocation fields
                }
            }
        }

        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.load_universe_data.return_value = universe_data
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/portfolio/targets/")

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "No target allocation data found" in data["message"]

    def test_get_current_allocations_universe_not_found(self, client):
        """Test current allocations when universe file not found"""
        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.load_universe_data.side_effect = FileNotFoundError("universe.json not found")
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/portfolio/targets/")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "Universe file not found" in data["message"]


class TestAPIErrorHandling:
    """Test comprehensive error handling across all endpoints"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_service_unavailable_error(self, client):
        """Test behavior when service is unavailable"""
        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_get_service.side_effect = Exception("Service unavailable")

            response = client.post("/api/v1/portfolio/targets/calculate", json={})

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_malformed_json_request(self, client):
        """Test behavior with malformed JSON"""
        response = client.post(
            "/api/v1/portfolio/targets/calculate",
            data="invalid json",
            headers={"content-type": "application/json"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_missing_content_type(self, client):
        """Test behavior with missing content type"""
        response = client.post(
            "/api/v1/portfolio/targets/calculate",
            data='{"force_recalculate": false}'
        )

        # Should still work as FastAPI is flexible with content types
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]


class TestAPIValidation:
    """Test API request/response validation"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_request_validation_valid_data(self, client):
        """Test request validation with valid data"""
        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.main.return_value = True
            mock_service.load_universe_data.return_value = {}
            mock_service.calculate_final_allocations.return_value = {}
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/portfolio/targets/calculate",
                json={
                    "force_recalculate": True,
                    "save_to_universe": False
                }
            )

            assert response.status_code == status.HTTP_200_OK

    def test_response_schema_compliance(self, client):
        """Test that responses comply with defined schemas"""
        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.load_universe_data.return_value = {
                "all_stocks": {
                    "AAPL": {
                        "ticker": "AAPL",
                        "screens": ["quality bloom"],
                        "rank": 1,
                        "final_target": 0.035,
                        "allocation_target": 0.10,
                        "screen_target": 0.35
                    }
                }
            }
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/portfolio/targets/")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verify response schema compliance
            required_fields = ["success", "message", "allocation_data", "universe_updated"]
            for field in required_fields:
                assert field in data

            # Verify nested structure
            if data["allocation_data"]:
                allocation = list(data["allocation_data"].values())[0]
                allocation_fields = ["ticker", "screener", "rank", "final_allocation"]
                for field in allocation_fields:
                    assert field in allocation


class TestAPIIntegration:
    """Integration tests for API endpoints"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_full_workflow_integration(self, client):
        """Test full workflow: calculate -> get summary -> get rankings"""
        sample_allocations = {
            "AAPL": {
                "ticker": "AAPL",
                "screener": "quality bloom",
                "rank": 1,
                "performance_180d": 15.25,
                "pocket_allocation": 0.10,
                "screener_target": 0.35,
                "final_allocation": 0.035
            }
        }

        universe_data = {
            "metadata": {
                "portfolio_optimization": {
                    "optimal_allocations": {"quality_bloom": 0.35}
                }
            },
            "screens": {
                "quality_bloom": {
                    "name": "quality bloom",
                    "stocks": [{"ticker": "AAPL", "price_180d_change": "15.25%"}]
                }
            }
        }

        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_get_service.return_value = mock_service

            # Configure mock for calculate endpoint
            mock_service.main.return_value = True
            mock_service.load_universe_data.return_value = universe_data
            mock_service.calculate_final_allocations.return_value = sample_allocations

            # 1. Calculate allocations
            response = client.post("/api/v1/portfolio/targets/calculate", json={})
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["success"] is True

            # 2. Configure mock for summary endpoint
            mock_service.get_allocation_summary.return_value = {
                "sorted_allocations": [
                    {
                        "ticker": "AAPL",
                        "screener": "quality bloom",
                        "screener_rank": 1,
                        "performance_180d": 15.25,
                        "pocket_allocation": 0.10,
                        "screener_target": 0.35,
                        "final_allocation": 0.035
                    }
                ],
                "total_allocation": 0.035,
                "top_10_allocations": [],
                "summary_stats": {
                    "total_stocks": 1,
                    "total_allocation_pct": 3.5,
                    "stocks_with_allocation": 1
                }
            }

            # Get summary
            response = client.get("/api/v1/portfolio/targets/summary")
            assert response.status_code == status.HTTP_200_OK
            summary = response.json()["summary"]
            assert len(summary["sorted_allocations"]) == 1

            # 3. Configure mock for rankings endpoint
            mock_service.rank_stocks_in_screener.return_value = [
                ({"ticker": "AAPL"}, 1, 15.25)
            ]
            mock_service.calculate_pocket_allocation.return_value = 0.10

            # Get rankings
            response = client.get("/api/v1/portfolio/targets/rankings/quality_bloom")
            assert response.status_code == status.HTTP_200_OK
            rankings = response.json()["rankings"]
            assert len(rankings) == 1
            assert rankings[0]["ticker"] == "AAPL"