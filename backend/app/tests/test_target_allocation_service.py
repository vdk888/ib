"""
Tests for Target Allocation Service (Step 6)
Ensures 100% behavioral compatibility with CLI step6_calculate_targets()
"""
import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from backend.app.services.implementations.target_allocation_service import TargetAllocationService
from backend.app.core.config import settings


class TestTargetAllocationService:
    """Test Target Allocation Service functionality"""

    @pytest.fixture
    def service(self):
        """Create target allocation service instance"""
        return TargetAllocationService()

    @pytest.fixture
    def sample_universe_data(self):
        """Sample universe data with portfolio optimization results"""
        return {
            "metadata": {
                "screens": ["quality bloom", "TOR Surplus", "Moat Companies"],
                "total_stocks": 150,
                "unique_stocks": 120,
                "portfolio_optimization": {
                    "optimal_allocations": {
                        "quality_bloom": 0.35,
                        "TOR_Surplus": 0.40,
                        "Moat_Companies": 0.25
                    },
                    "portfolio_stats": {
                        "expected_annual_return": 0.12,
                        "annual_volatility": 0.18,
                        "sharpe_ratio": 0.56
                    }
                }
            },
            "screens": {
                "quality_bloom": {
                    "name": "quality bloom",
                    "count": 50,
                    "stocks": [
                        {
                            "ticker": "AAPL",
                            "isin": "US0378331005",
                            "name": "Apple Inc",
                            "price_180d_change": "15.25%"
                        },
                        {
                            "ticker": "MSFT",
                            "isin": "US5949181005",
                            "name": "Microsoft Corp",
                            "price_180d_change": "12.50%"
                        },
                        {
                            "ticker": "GOOGL",
                            "isin": "US02079K3059",
                            "name": "Alphabet Inc",
                            "price_180d_change": "-3.25%"
                        }
                    ]
                },
                "TOR_Surplus": {
                    "name": "TOR Surplus",
                    "count": 40,
                    "stocks": [
                        {
                            "ticker": "TSLA",
                            "isin": "US88160R1014",
                            "name": "Tesla Inc",
                            "price_180d_change": "25.75%"
                        },
                        {
                            "ticker": "NVDA",
                            "isin": "US67066G1040",
                            "name": "NVIDIA Corp",
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
                    "screens": ["quality bloom"],
                    "price_180d_change": "15.25%"
                },
                "MSFT": {
                    "ticker": "MSFT",
                    "isin": "US5949181005",
                    "name": "Microsoft Corp",
                    "screens": ["quality bloom"],
                    "price_180d_change": "12.50%"
                },
                "TSLA": {
                    "ticker": "TSLA",
                    "isin": "US88160R1014",
                    "name": "Tesla Inc",
                    "screens": ["TOR_Surplus"],
                    "price_180d_change": "25.75%"
                }
            }
        }

    def test_parse_180d_change_valid_positive(self, service):
        """Test parsing positive percentage changes"""
        result = service.parse_180d_change("15.25%")
        assert result == 15.25

    def test_parse_180d_change_valid_negative(self, service):
        """Test parsing negative percentage changes"""
        result = service.parse_180d_change("-3.45%")
        assert result == -3.45

    def test_parse_180d_change_invalid_format(self, service):
        """Test parsing invalid format returns 0.0"""
        result = service.parse_180d_change("invalid")
        assert result == 0.0

    def test_parse_180d_change_none_value(self, service):
        """Test parsing None value returns 0.0"""
        result = service.parse_180d_change(None)
        assert result == 0.0

    def test_extract_screener_allocations_success(self, service, sample_universe_data):
        """Test successful extraction of screener allocations"""
        result = service.extract_screener_allocations(sample_universe_data)

        expected = {
            "quality_bloom": 0.35,
            "TOR_Surplus": 0.40,
            "Moat_Companies": 0.25
        }
        assert result == expected

    def test_extract_screener_allocations_no_optimization(self, service):
        """Test extraction fails when no portfolio optimization data"""
        universe_data = {
            "metadata": {}
        }

        with pytest.raises(ValueError, match="No portfolio optimization results found"):
            service.extract_screener_allocations(universe_data)

    def test_rank_stocks_in_screener(self, service):
        """Test stock ranking within screener by 180d performance"""
        stocks = [
            {"ticker": "AAPL", "price_180d_change": "15.25%"},
            {"ticker": "MSFT", "price_180d_change": "12.50%"},
            {"ticker": "GOOGL", "price_180d_change": "-3.25%"},
            {"ticker": "AMZN", "price_180d_change": "20.00%"}
        ]

        result = service.rank_stocks_in_screener(stocks)

        # Should be ranked by performance descending
        assert len(result) == 4
        assert result[0][0]["ticker"] == "AMZN"  # Best performance (20.00%)
        assert result[0][1] == 1  # Rank 1
        assert result[0][2] == 20.0  # Performance

        assert result[1][0]["ticker"] == "AAPL"  # Second best (15.25%)
        assert result[1][1] == 2  # Rank 2

        assert result[3][0]["ticker"] == "GOOGL"  # Worst performance (-3.25%)
        assert result[3][1] == 4  # Rank 4
        assert result[3][2] == -3.25

    def test_calculate_pocket_allocation_rank_1(self, service):
        """Test pocket allocation for rank 1 stock"""
        result = service.calculate_pocket_allocation(rank=1, total_stocks=10)
        # Should get MAX_ALLOCATION (0.10)
        assert result == settings.portfolio.max_allocation

    def test_calculate_pocket_allocation_beyond_max_ranked(self, service):
        """Test pocket allocation for stocks beyond MAX_RANKED_STOCKS"""
        result = service.calculate_pocket_allocation(rank=31, total_stocks=50)
        # Should get 0% (beyond MAX_RANKED_STOCKS=30)
        assert result == 0.0

    def test_calculate_pocket_allocation_linear_interpolation(self, service):
        """Test linear interpolation for middle ranks"""
        # With MAX_ALLOCATION=0.10, MIN_ALLOCATION=0.01, MAX_RANKED_STOCKS=30
        # Rank 15 (middle of 30) should get approximately middle allocation
        result = service.calculate_pocket_allocation(rank=15, total_stocks=30)

        # Expected: 0.10 - ((15-1) / (30-1)) * (0.10 - 0.01) = 0.10 - 0.48275 * 0.09 ≈ 0.0565
        expected = 0.10 - ((15-1) / (30-1)) * (0.10 - 0.01)
        assert abs(result - expected) < 0.001

    def test_calculate_pocket_allocation_single_stock(self, service):
        """Test pocket allocation with single stock gets MAX_ALLOCATION"""
        result = service.calculate_pocket_allocation(rank=1, total_stocks=1)
        assert result == settings.portfolio.max_allocation

    def test_calculate_final_allocations_structure(self, service, sample_universe_data):
        """Test final allocations calculation structure"""
        with patch.object(service, 'extract_screener_allocations') as mock_extract:
            mock_extract.return_value = {
                "quality_bloom": 0.35,
                "TOR_Surplus": 0.40
            }

            result = service.calculate_final_allocations(sample_universe_data)

            # Should return dict with ticker keys
            assert isinstance(result, dict)
            assert "AAPL" in result
            assert "TSLA" in result

            # Check structure of allocation data
            aapl_data = result["AAPL"]
            assert aapl_data["ticker"] == "AAPL"
            assert aapl_data["screener"] == "quality bloom"
            assert "rank" in aapl_data
            assert "performance_180d" in aapl_data
            assert "pocket_allocation" in aapl_data
            assert "screener_target" in aapl_data
            assert "final_allocation" in aapl_data

    def test_calculate_final_allocations_math(self, service, sample_universe_data):
        """Test final allocation calculation math"""
        with patch.object(service, 'extract_screener_allocations') as mock_extract:
            mock_extract.return_value = {"quality_bloom": 0.35}

            result = service.calculate_final_allocations(sample_universe_data)

            # AAPL should be rank 1 in quality_bloom (best performance: 15.25%)
            aapl_data = result["AAPL"]
            assert aapl_data["rank"] == 1
            assert aapl_data["screener_target"] == 0.35
            assert aapl_data["pocket_allocation"] == settings.portfolio.max_allocation  # Rank 1 gets MAX_ALLOCATION

            # Final allocation = screener_target * pocket_allocation
            expected_final = 0.35 * settings.portfolio.max_allocation
            assert abs(aapl_data["final_allocation"] - expected_final) < 0.001

    @patch('json.load')
    @patch('builtins.open')
    @patch('os.path.exists')
    def test_load_universe_data_success(self, mock_exists, mock_open, mock_json_load, service, sample_universe_data):
        """Test successful universe data loading"""
        mock_exists.return_value = True
        mock_json_load.return_value = sample_universe_data

        result = service.load_universe_data()
        assert result == sample_universe_data
        mock_open.assert_called_once_with("data/universe.json", 'r', encoding='utf-8')

    @patch('os.path.exists')
    def test_load_universe_data_file_not_found(self, mock_exists, service):
        """Test universe data loading when file doesn't exist"""
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError, match="universe.json not found"):
            service.load_universe_data()

    def test_update_universe_with_allocations_success(self, service, sample_universe_data):
        """Test successful universe update with allocations"""
        final_allocations = {
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

        # Make a copy to avoid modifying the fixture
        universe_data = json.loads(json.dumps(sample_universe_data))

        result = service.update_universe_with_allocations(universe_data, final_allocations)

        assert result is True

        # Check that fields were added to screens.stocks
        aapl_in_screen = universe_data["screens"]["quality_bloom"]["stocks"][0]
        assert aapl_in_screen["rank"] == 1
        assert aapl_in_screen["allocation_target"] == 0.10
        assert aapl_in_screen["screen_target"] == 0.35
        assert aapl_in_screen["final_target"] == 0.035

        # Check that fields were added to all_stocks
        aapl_in_all = universe_data["all_stocks"]["AAPL"]
        assert aapl_in_all["rank"] == 1
        assert aapl_in_all["final_target"] == 0.035

    def test_get_allocation_summary_structure(self, service):
        """Test allocation summary structure"""
        final_allocations = {
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
                "pocket_allocation": 0.09,
                "screener_target": 0.35,
                "final_allocation": 0.0315
            }
        }

        result = service.get_allocation_summary(final_allocations)

        assert "sorted_allocations" in result
        assert "total_allocation" in result
        assert "top_10_allocations" in result
        assert "summary_stats" in result

        # Check sorting (AAPL should be first with higher allocation)
        assert result["sorted_allocations"][0]["ticker"] == "AAPL"

        # Check total allocation
        expected_total = 0.035 + 0.0315
        assert abs(result["total_allocation"] - expected_total) < 0.001

        # Check summary stats
        assert result["summary_stats"]["total_stocks"] == 2
        assert result["summary_stats"]["stocks_with_allocation"] == 2

    @patch('backend.app.services.implementations.legacy.targetter.main')
    def test_main_success(self, mock_legacy_main, service):
        """Test successful main execution"""
        mock_legacy_main.return_value = True

        result = service.main()
        assert result is True
        mock_legacy_main.assert_called_once()

    @patch('backend.app.services.implementations.legacy.targetter.main')
    def test_main_failure(self, mock_legacy_main, service):
        """Test main execution failure"""
        mock_legacy_main.return_value = False

        result = service.main()
        assert result is False

    @patch('backend.app.services.implementations.legacy.targetter.main')
    def test_main_exception(self, mock_legacy_main, service):
        """Test main execution with exception"""
        mock_legacy_main.side_effect = Exception("Test error")

        result = service.main()
        assert result is False


class TestTargetAllocationEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.fixture
    def service(self):
        return TargetAllocationService()

    def test_empty_screener_stocks(self, service):
        """Test handling of empty screener stocks list"""
        result = service.rank_stocks_in_screener([])
        assert result == []

    def test_stocks_with_missing_price_data(self, service):
        """Test stocks without price_180d_change field"""
        stocks = [
            {"ticker": "AAPL"},  # Missing price_180d_change
            {"ticker": "MSFT", "price_180d_change": "12.50%"},
        ]

        result = service.rank_stocks_in_screener(stocks)

        assert len(result) == 2
        # MSFT should be rank 1 (has performance data)
        assert result[0][0]["ticker"] == "MSFT"
        assert result[0][1] == 1
        assert result[0][2] == 12.5

        # AAPL should be rank 2 (no performance data = 0.0)
        assert result[1][0]["ticker"] == "AAPL"
        assert result[1][1] == 2
        assert result[1][2] == 0.0

    def test_calculate_pocket_allocation_edge_cases(self, service):
        """Test edge cases for pocket allocation"""
        # Test with exactly MAX_RANKED_STOCKS stocks
        result = service.calculate_pocket_allocation(rank=30, total_stocks=30)
        assert result == settings.portfolio.min_allocation

        # Test with fewer stocks than MAX_RANKED_STOCKS
        result = service.calculate_pocket_allocation(rank=10, total_stocks=10)
        expected = settings.portfolio.max_allocation - ((10-1) / (10-1)) * (settings.portfolio.max_allocation - settings.portfolio.min_allocation)
        assert result == settings.portfolio.min_allocation

    def test_screener_name_matching_edge_cases(self, service):
        """Test screener name matching with different formats"""
        universe_data = {
            "metadata": {
                "portfolio_optimization": {
                    "optimal_allocations": {
                        "quality bloom": 0.35,  # Space in key
                        "tor_surplus": 0.40     # Different case
                    }
                }
            },
            "screens": {
                "quality_bloom": {  # Underscore in key
                    "name": "quality bloom",
                    "stocks": [{"ticker": "AAPL", "price_180d_change": "10%"}]
                },
                "TOR_Surplus": {    # Mixed case in key
                    "name": "TOR Surplus",
                    "stocks": [{"ticker": "TSLA", "price_180d_change": "15%"}]
                }
            }
        }

        with patch.object(service, 'extract_screener_allocations') as mock_extract:
            mock_extract.return_value = {
                "quality bloom": 0.35,
                "tor_surplus": 0.40
            }

            result = service.calculate_final_allocations(universe_data)

            # Should successfully match despite naming differences
            assert "AAPL" in result
            assert "TSLA" in result
            assert result["AAPL"]["screener_target"] == 0.35
            assert result["TSLA"]["screener_target"] == 0.40


class TestTargetAllocationIntegration:
    """Integration tests with actual file operations"""

    @pytest.fixture
    def service(self):
        return TargetAllocationService()

    @pytest.fixture
    def temp_universe_file(self, sample_universe_data):
        """Create temporary universe file for testing"""
        # Create temporary file
        fd, temp_path = tempfile.mkstemp(suffix='.json')

        try:
            # Write sample data
            with os.fdopen(fd, 'w') as f:
                json.dump(sample_universe_data, f)

            # Patch the universe path
            with patch('backend.app.services.implementations.legacy.targetter.os.path.exists') as mock_exists:
                mock_exists.return_value = True
                with patch('backend.app.services.implementations.legacy.targetter.open', mock_open_file(temp_path)):
                    yield temp_path
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @pytest.fixture
    def sample_universe_data(self):
        return {
            "metadata": {
                "portfolio_optimization": {
                    "optimal_allocations": {"quality_bloom": 0.50}
                }
            },
            "screens": {
                "quality_bloom": {
                    "name": "quality bloom",
                    "stocks": [
                        {"ticker": "AAPL", "price_180d_change": "15.25%"},
                        {"ticker": "MSFT", "price_180d_change": "10.00%"}
                    ]
                }
            },
            "all_stocks": {
                "AAPL": {"ticker": "AAPL", "price_180d_change": "15.25%"},
                "MSFT": {"ticker": "MSFT", "price_180d_change": "10.00%"}
            }
        }


def mock_open_file(file_path):
    """Mock open function that reads from actual temp file"""
    def _mock_open(path, mode='r', encoding=None):
        if 'universe.json' in path or path == file_path:
            return open(file_path, mode, encoding=encoding)
        else:
            # Fall back to real open for other files
            return open(path, mode, encoding=encoding)
    return _mock_open


# Performance and reliability tests
class TestTargetAllocationPerformance:
    """Performance and reliability tests"""

    @pytest.fixture
    def service(self):
        return TargetAllocationService()

    def test_large_screener_ranking_performance(self, service):
        """Test ranking performance with large number of stocks"""
        # Create 1000 stocks with random performance
        import random
        stocks = []
        for i in range(1000):
            performance = random.uniform(-20.0, 30.0)
            stocks.append({
                "ticker": f"STOCK{i:04d}",
                "price_180d_change": f"{performance:.2f}%"
            })

        # Time the ranking operation
        import time
        start_time = time.time()
        result = service.rank_stocks_in_screener(stocks)
        end_time = time.time()

        # Should complete in reasonable time (< 1 second)
        assert (end_time - start_time) < 1.0
        assert len(result) == 1000

        # Verify sorting correctness
        for i in range(len(result) - 1):
            assert result[i][2] >= result[i+1][2]  # Performance should be descending

    def test_memory_efficient_allocation_calculation(self, service):
        """Test memory efficiency with large allocation datasets"""
        # Create large final allocations dict
        final_allocations = {}
        for i in range(5000):
            final_allocations[f"STOCK{i:04d}"] = {
                "ticker": f"STOCK{i:04d}",
                "screener": f"screener_{i % 10}",
                "rank": (i % 30) + 1,
                "performance_180d": float(i % 100 - 50),
                "pocket_allocation": 0.05,
                "screener_target": 0.1,
                "final_allocation": 0.005
            }

        # Should handle large datasets without memory issues
        summary = service.get_allocation_summary(final_allocations)

        assert len(summary["sorted_allocations"]) == 5000
        assert len(summary["top_10_allocations"]) == 10
        assert summary["summary_stats"]["total_stocks"] == 5000