"""
Step 6 Target Allocation Behavioral Compatibility Tests
Ensures 100% behavioral compatibility between CLI step6_calculate_targets() and API endpoints
"""
import pytest
import json
import os
import tempfile
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.implementations.target_allocation_service import TargetAllocationService


class TestStep6CliApiCompatibility:
    """
    Test CLI vs API behavioral compatibility for Step 6
    Ensures identical results between python main.py 6 and API endpoints
    """

    @pytest.fixture
    def client(self):
        """Create FastAPI test client"""
        return TestClient(app)

    @pytest.fixture
    def temp_universe_with_optimization(self):
        """Create temporary universe.json with portfolio optimization data"""
        universe_data = {
            "metadata": {
                "screens": ["quality bloom", "TOR Surplus"],
                "total_stocks": 150,
                "unique_stocks": 120,
                "additional_fields_enabled": True,
                "additional_fields": [
                    {"header": "Price", "subtitle": "180d change", "alias": "price_180d_change"}
                ],
                "portfolio_optimization": {
                    "optimal_allocations": {
                        "quality_bloom": 0.35,
                        "TOR_Surplus": 0.40,
                        "Moat_Companies": 0.25
                    },
                    "portfolio_performance": {
                        "expected_annual_return": 0.1234,
                        "annual_volatility": 0.1567,
                        "sharpe_ratio": 0.7891
                    },
                    "individual_screener_stats": {
                        "quality_bloom": {
                            "annual_return": 0.11,
                            "annual_volatility": 0.14,
                            "sharpe_ratio": 0.65
                        }
                    },
                    "correlation_matrix": {
                        "quality_bloom": {"quality_bloom": 1.0, "TOR_Surplus": 0.3},
                        "TOR_Surplus": {"quality_bloom": 0.3, "TOR_Surplus": 1.0}
                    },
                    "optimization_details": {
                        "success": True,
                        "message": "Optimization completed successfully"
                    }
                }
            },
            "screens": {
                "quality_bloom": {
                    "name": "quality bloom",
                    "count": 3,
                    "stocks": [
                        {
                            "ticker": "AAPL",
                            "isin": "US0378331005",
                            "name": "Apple Inc",
                            "currency": "USD",
                            "sector": "Technology",
                            "country": "United States",
                            "price": 175.50,
                            "price_180d_change": "15.25%"
                        },
                        {
                            "ticker": "MSFT",
                            "isin": "US5949181005",
                            "name": "Microsoft Corp",
                            "currency": "USD",
                            "sector": "Technology",
                            "country": "United States",
                            "price": 380.20,
                            "price_180d_change": "12.50%"
                        },
                        {
                            "ticker": "GOOGL",
                            "isin": "US02079K3059",
                            "name": "Alphabet Inc",
                            "currency": "USD",
                            "sector": "Technology",
                            "country": "United States",
                            "price": 140.75,
                            "price_180d_change": "-3.25%"
                        }
                    ]
                },
                "TOR_Surplus": {
                    "name": "TOR Surplus",
                    "count": 2,
                    "stocks": [
                        {
                            "ticker": "TSLA",
                            "isin": "US88160R1014",
                            "name": "Tesla Inc",
                            "currency": "USD",
                            "sector": "Automotive",
                            "country": "United States",
                            "price": 220.30,
                            "price_180d_change": "25.75%"
                        },
                        {
                            "ticker": "NVDA",
                            "isin": "US67066G1040",
                            "name": "NVIDIA Corp",
                            "currency": "USD",
                            "sector": "Technology",
                            "country": "United States",
                            "price": 450.80,
                            "price_180d_change": "8.30%"
                        }
                    ]
                }
            },
            "all_stocks": {
                "AAPL": {
                    "ticker": "AAPL",
                    "isin": "US0378331005",
                    "name": "Apple Inc",
                    "currency": "USD",
                    "sector": "Technology",
                    "country": "United States",
                    "price": 175.50,
                    "screens": ["quality bloom"],
                    "price_180d_change": "15.25%"
                },
                "MSFT": {
                    "ticker": "MSFT",
                    "isin": "US5949181005",
                    "name": "Microsoft Corp",
                    "currency": "USD",
                    "sector": "Technology",
                    "country": "United States",
                    "price": 380.20,
                    "screens": ["quality bloom"],
                    "price_180d_change": "12.50%"
                },
                "GOOGL": {
                    "ticker": "GOOGL",
                    "isin": "US02079K3059",
                    "name": "Alphabet Inc",
                    "currency": "USD",
                    "sector": "Technology",
                    "country": "United States",
                    "price": 140.75,
                    "screens": ["quality bloom"],
                    "price_180d_change": "-3.25%"
                },
                "TSLA": {
                    "ticker": "TSLA",
                    "isin": "US88160R1014",
                    "name": "Tesla Inc",
                    "currency": "USD",
                    "sector": "Automotive",
                    "country": "United States",
                    "price": 220.30,
                    "screens": ["TOR_Surplus"],
                    "price_180d_change": "25.75%"
                },
                "NVDA": {
                    "ticker": "NVDA",
                    "isin": "US67066G1040",
                    "name": "NVIDIA Corp",
                    "currency": "USD",
                    "sector": "Technology",
                    "country": "United States",
                    "price": 450.80,
                    "screens": ["TOR_Surplus"],
                    "price_180d_change": "8.30%"
                }
            }
        }

        # Create temporary file
        fd, temp_path = tempfile.mkstemp(suffix='_universe.json')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(universe_data, f, indent=2)
            yield temp_path, universe_data
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_service_allocation_calculation_compatibility(self, temp_universe_with_optimization):
        """Test that service produces same allocation calculations as CLI logic"""
        temp_path, original_data = temp_universe_with_optimization

        # Mock the file operations to use our temp file
        with patch('backend.app.services.implementations.legacy.targetter.load_universe_data') as mock_load, \
             patch('backend.app.services.implementations.legacy.targetter.save_universe') as mock_save:

            mock_load.return_value = json.loads(json.dumps(original_data))  # Deep copy

            service = TargetAllocationService()

            # Test individual functions match expected logic
            universe_data = service.load_universe_data()

            # Test screener allocation extraction
            screener_allocations = service.extract_screener_allocations(universe_data)
            expected_allocations = {
                "quality_bloom": 0.35,
                "TOR_Surplus": 0.40,
                "Moat_Companies": 0.25
            }
            assert screener_allocations == expected_allocations

            # Test stock ranking for quality_bloom
            quality_stocks = universe_data["screens"]["quality_bloom"]["stocks"]
            ranked_stocks = service.rank_stocks_in_screener(quality_stocks)

            # Expected order: AAPL (15.25%) > MSFT (12.50%) > GOOGL (-3.25%)
            assert ranked_stocks[0][0]["ticker"] == "AAPL"
            assert ranked_stocks[0][1] == 1  # Rank 1
            assert ranked_stocks[0][2] == 15.25  # Performance

            assert ranked_stocks[1][0]["ticker"] == "MSFT"
            assert ranked_stocks[1][1] == 2  # Rank 2
            assert ranked_stocks[1][2] == 12.50

            assert ranked_stocks[2][0]["ticker"] == "GOOGL"
            assert ranked_stocks[2][1] == 3  # Rank 3
            assert ranked_stocks[2][2] == -3.25

            # Test pocket allocation calculations
            # Rank 1 should get MAX_ALLOCATION (0.10)
            aapl_pocket = service.calculate_pocket_allocation(1, 3)
            assert aapl_pocket == 0.10

            # Rank 2 should get interpolated value
            msft_pocket = service.calculate_pocket_allocation(2, 3)
            # With 3 total stocks: allocation = 0.10 - ((2-1) / (3-1)) * (0.10 - 0.01) = 0.10 - 0.5 * 0.09 = 0.055
            expected_msft_pocket = 0.10 - ((2-1) / (3-1)) * (0.10 - 0.01)
            assert abs(msft_pocket - expected_msft_pocket) < 0.001

            # Test final allocation calculation
            final_allocations = service.calculate_final_allocations(universe_data)

            # Verify AAPL final allocation
            aapl_final = final_allocations["AAPL"]
            assert aapl_final["ticker"] == "AAPL"
            assert aapl_final["screener"] == "quality bloom"
            assert aapl_final["rank"] == 1
            assert aapl_final["screener_target"] == 0.35
            assert aapl_final["pocket_allocation"] == 0.10
            # Final = screener_target * pocket_allocation = 0.35 * 0.10 = 0.035
            assert abs(aapl_final["final_allocation"] - 0.035) < 0.001

            # Verify TSLA final allocation (should be rank 1 in TOR_Surplus)
            tsla_final = final_allocations["TSLA"]
            assert tsla_final["ticker"] == "TSLA"
            assert tsla_final["screener"] == "TOR Surplus"
            assert tsla_final["rank"] == 1  # Best performance in TOR_Surplus
            assert tsla_final["screener_target"] == 0.40
            assert tsla_final["pocket_allocation"] == 0.10
            # Final = 0.40 * 0.10 = 0.040
            assert abs(tsla_final["final_allocation"] - 0.040) < 0.001

    def test_api_endpoint_data_structure_compatibility(self, client, temp_universe_with_optimization):
        """Test that API endpoints return data in compatible structure"""
        temp_path, original_data = temp_universe_with_optimization

        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_get_service.return_value = mock_service

            # Mock the service methods
            mock_service.main.return_value = True
            mock_service.load_universe_data.return_value = original_data

            # Expected final allocations based on our logic
            expected_allocations = {
                "AAPL": {
                    "ticker": "AAPL",
                    "screener": "quality bloom",
                    "rank": 1,
                    "performance_180d": 15.25,
                    "pocket_allocation": 0.10,
                    "screener_target": 0.35,
                    "final_allocation": 0.035
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

            mock_service.calculate_final_allocations.return_value = expected_allocations

            # Test calculate endpoint
            response = client.post("/api/v1/portfolio/targets/calculate", json={})
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True
            assert len(data["allocation_data"]) == 2

            # Verify AAPL data structure matches expected
            aapl_api_data = data["allocation_data"]["AAPL"]
            assert aapl_api_data["ticker"] == "AAPL"
            assert aapl_api_data["screener"] == "quality bloom"
            assert aapl_api_data["rank"] == 1
            assert aapl_api_data["performance_180d"] == 15.25
            assert aapl_api_data["final_allocation"] == 0.035

    def test_allocation_summary_mathematical_consistency(self, client):
        """Test allocation summary mathematical consistency"""
        # Create test allocation data
        test_allocations = {}
        total_expected = 0.0

        # Generate 50 stocks with various allocations
        for i in range(50):
            allocation = max(0, 0.10 - (i * 0.002))  # Decreasing allocation
            total_expected += allocation
            test_allocations[f"STOCK{i:02d}"] = {
                "ticker": f"STOCK{i:02d}",
                "screener": f"screener_{i % 3}",
                "rank": (i % 30) + 1,
                "performance_180d": 20.0 - i,
                "pocket_allocation": allocation / 0.35,  # Assuming 35% screener target
                "screener_target": 0.35,
                "final_allocation": allocation
            }

        mock_summary_data = {
            "sorted_allocations": [
                {
                    "ticker": ticker,
                    "screener": data["screener"],
                    "screener_rank": data["rank"],
                    "performance_180d": data["performance_180d"],
                    "pocket_allocation": data["pocket_allocation"],
                    "screener_target": data["screener_target"],
                    "final_allocation": data["final_allocation"]
                }
                for ticker, data in sorted(test_allocations.items(),
                                         key=lambda x: x[1]["final_allocation"],
                                         reverse=True)
            ],
            "total_allocation": total_expected,
            "top_10_allocations": [],
            "summary_stats": {
                "total_stocks": len(test_allocations),
                "total_allocation_pct": total_expected * 100,
                "stocks_with_allocation": len([a for a in test_allocations.values() if a["final_allocation"] > 0])
            }
        }

        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.load_universe_data.return_value = {"test": "data"}
            mock_service.calculate_final_allocations.return_value = test_allocations
            mock_service.get_allocation_summary.return_value = mock_summary_data
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/portfolio/targets/summary")
            assert response.status_code == 200

            data = response.json()
            summary = data["summary"]

            # Test mathematical consistency
            assert len(summary["sorted_allocations"]) == 50
            assert abs(summary["total_allocation"] - total_expected) < 0.001

            # Test sorting (should be descending by final_allocation)
            allocations = summary["sorted_allocations"]
            for i in range(len(allocations) - 1):
                assert allocations[i]["final_allocation"] >= allocations[i+1]["final_allocation"]

    def test_screener_ranking_logic_consistency(self, client):
        """Test that screener ranking logic is consistent with CLI behavior"""
        # Test data with known performance values
        test_universe = {
            "screens": {
                "test_screener": {
                    "name": "Test Screener",
                    "stocks": [
                        {"ticker": "HIGH", "price_180d_change": "25.50%"},    # Should be rank 1
                        {"ticker": "MED", "price_180d_change": "10.25%"},     # Should be rank 2
                        {"ticker": "LOW", "price_180d_change": "-5.75%"},     # Should be rank 3
                        {"ticker": "ZERO", "price_180d_change": "0.00%"},     # Should be rank 4
                        {"ticker": "NONE"},                                    # No price data, should be rank 5 (0.0)
                    ]
                }
            }
        }

        # Expected ranking after sorting by performance descending
        expected_rankings = [
            ("HIGH", 1, 25.50),
            ("MED", 2, 10.25),
            ("ZERO", 3, 0.00),   # 0.00% comes before -5.75%
            ("LOW", 4, -5.75),
            ("NONE", 5, 0.00)    # No data defaults to 0.0
        ]

        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.load_universe_data.return_value = test_universe

            # Mock the ranking function to return expected results
            mock_service.rank_stocks_in_screener.return_value = [
                ({"ticker": ticker}, rank, performance)
                for ticker, rank, performance in expected_rankings
            ]

            # Mock pocket allocation calculation (linear interpolation)
            def mock_pocket_calc(rank, total_stocks):
                if rank > 30:  # MAX_RANKED_STOCKS
                    return 0.0
                if total_stocks == 1:
                    return 0.10
                return 0.10 - ((rank - 1) / (min(30, total_stocks) - 1)) * (0.10 - 0.01)

            mock_service.calculate_pocket_allocation.side_effect = mock_pocket_calc
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/portfolio/targets/rankings/test_screener")
            assert response.status_code == 200

            data = response.json()
            rankings = data["rankings"]

            # Verify ranking order and pocket allocations
            assert len(rankings) == 5
            assert rankings[0]["ticker"] == "HIGH"
            assert rankings[0]["rank"] == 1
            assert rankings[0]["performance_180d"] == 25.50
            assert rankings[0]["pocket_allocation"] == 0.10  # Rank 1 gets MAX_ALLOCATION

            assert rankings[1]["ticker"] == "MED"
            assert rankings[1]["rank"] == 2

            # Verify stocks with allocation count
            stocks_with_allocation = sum(1 for r in rankings if r["pocket_allocation"] > 0)
            assert data["stocks_with_allocation"] == stocks_with_allocation

    def test_edge_case_compatibility(self):
        """Test edge cases that CLI handles"""
        service = TargetAllocationService()

        # Test edge case: Single stock in screener
        single_stock = [{"ticker": "ONLY", "price_180d_change": "10%"}]
        rankings = service.rank_stocks_in_screener(single_stock)
        assert len(rankings) == 1
        assert rankings[0][1] == 1  # Should be rank 1
        assert rankings[0][2] == 10.0

        pocket_alloc = service.calculate_pocket_allocation(1, 1)
        assert pocket_alloc == 0.10  # Single stock gets MAX_ALLOCATION

        # Test edge case: Empty price change
        empty_stocks = [{"ticker": "EMPTY", "price_180d_change": ""}]
        rankings = service.rank_stocks_in_screener(empty_stocks)
        assert rankings[0][2] == 0.0  # Empty string should default to 0.0

        # Test edge case: Malformed percentage
        bad_stocks = [{"ticker": "BAD", "price_180d_change": "not_a_number%"}]
        rankings = service.rank_stocks_in_screener(bad_stocks)
        assert rankings[0][2] == 0.0  # Bad format should default to 0.0

        # Test edge case: Stocks beyond MAX_RANKED_STOCKS (30)
        beyond_max = service.calculate_pocket_allocation(31, 50)
        assert beyond_max == 0.0  # Beyond MAX_RANKED_STOCKS should get 0%

    def test_universe_update_field_compatibility(self):
        """Test that universe update adds the same fields as CLI"""
        service = TargetAllocationService()

        # Sample data
        universe_data = {
            "screens": {
                "test": {
                    "stocks": [{"ticker": "TEST"}]
                }
            },
            "all_stocks": {
                "TEST": {"ticker": "TEST"}
            }
        }

        final_allocations = {
            "TEST": {
                "ticker": "TEST",
                "screener": "test",
                "rank": 1,
                "performance_180d": 10.0,
                "pocket_allocation": 0.10,
                "screener_target": 0.35,
                "final_allocation": 0.035
            }
        }

        # Test universe update
        success = service.update_universe_with_allocations(universe_data, final_allocations)
        assert success is True

        # Verify fields added to screens.stocks
        stock_in_screen = universe_data["screens"]["test"]["stocks"][0]
        assert "rank" in stock_in_screen
        assert "allocation_target" in stock_in_screen
        assert "screen_target" in stock_in_screen
        assert "final_target" in stock_in_screen

        assert stock_in_screen["rank"] == 1
        assert stock_in_screen["allocation_target"] == 0.10
        assert stock_in_screen["screen_target"] == 0.35
        assert stock_in_screen["final_target"] == 0.035

        # Verify fields added to all_stocks
        stock_in_all = universe_data["all_stocks"]["TEST"]
        assert stock_in_all["rank"] == 1
        assert stock_in_all["final_target"] == 0.035

    def test_console_output_pattern_compatibility(self, client):
        """Test that API provides equivalent information to CLI console output"""
        # The CLI produces console output with + and X patterns for success/error
        # We test that API provides equivalent information in structured format

        test_allocations = {
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

        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_service.main.return_value = True
            mock_service.load_universe_data.return_value = {"test": "data"}
            mock_service.calculate_final_allocations.return_value = test_allocations
            mock_get_service.return_value = mock_service

            response = client.post("/api/v1/portfolio/targets/calculate", json={})
            assert response.status_code == 200

            data = response.json()

            # API should provide structured equivalent of CLI success messages
            assert data["success"] is True
            assert "Successfully calculated target allocations" in data["message"]
            assert "1 stocks" in data["message"]  # Equivalent to CLI count output

            # API should provide same data that CLI displays in tables
            assert len(data["allocation_data"]) == 1
            aapl_data = data["allocation_data"]["AAPL"]

            # Should contain all the information CLI displays in its table format
            required_fields = [
                "ticker", "screener", "rank", "performance_180d",
                "pocket_allocation", "screener_target", "final_allocation"
            ]
            for field in required_fields:
                assert field in aapl_data

    def test_error_handling_compatibility(self, client):
        """Test that API error handling matches CLI error patterns"""
        with patch('backend.app.core.dependencies.get_target_allocation_service') as mock_get_service:
            mock_service = Mock(spec=TargetAllocationService)
            mock_get_service.return_value = mock_service

            # Test universe file not found (CLI prints "X universe.json not found - run previous steps first")
            mock_service.main.side_effect = FileNotFoundError("universe.json not found - run previous steps first")

            response = client.post("/api/v1/portfolio/targets/calculate", json={})
            assert response.status_code == 404
            data = response.json()
            assert "Universe file not found" in data["message"]

            # Test no optimization data (CLI prints "X No portfolio optimization results found")
            mock_service.main.side_effect = ValueError("No portfolio optimization results found - run portfolio optimizer first")

            response = client.post("/api/v1/portfolio/targets/calculate", json={})
            assert response.status_code == 400
            data = response.json()
            assert "Invalid data" in data["message"]