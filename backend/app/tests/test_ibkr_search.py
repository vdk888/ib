"""
Tests for IBKR Search Service
Test that implementation exactly replicates legacy behavior
"""

import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from ..services.implementations.ibkr_search_service import IBKRSearchService


class TestIBKRSearchService:
    """Test suite for IBKR Search Service"""

    @pytest.fixture
    def service(self):
        """Create IBKR search service instance"""
        return IBKRSearchService(ibkr_host="127.0.0.1", ibkr_port=4002)

    @pytest.fixture
    def sample_universe_data(self):
        """Sample universe data for testing"""
        return {
            "screens": {
                "quality bloom": {
                    "stocks": [
                        {
                            "ticker": "AAPL",
                            "isin": "US0378331005",
                            "name": "Apple Inc",
                            "currency": "USD",
                            "sector": "Technology",
                            "country": "United States",
                            "quantity": 100
                        },
                        {
                            "ticker": "GOOGL",
                            "isin": "US02079K3059",
                            "name": "Alphabet Inc",
                            "currency": "USD",
                            "sector": "Technology",
                            "country": "United States",
                            "quantity": 0
                        },
                        {
                            "ticker": "TSLA",
                            "isin": "US88160R1014",
                            "name": "Tesla Inc",
                            "currency": "USD",
                            "sector": "Consumer Discretionary",
                            "country": "United States",
                            "quantity": 50
                        }
                    ]
                },
                "TOR Surplus": {
                    "stocks": [
                        {
                            "ticker": "MSFT",
                            "isin": "US5949181045",
                            "name": "Microsoft Corporation",
                            "currency": "USD",
                            "sector": "Technology",
                            "country": "United States",
                            "quantity": 0
                        }
                    ]
                }
            }
        }

    def test_extract_unique_stocks(self, service, sample_universe_data):
        """Test extracting unique stocks from universe data"""
        unique_stocks = service.extract_unique_stocks(sample_universe_data)

        # Should extract 4 unique stocks
        assert len(unique_stocks) == 4

        # Check that quantity is included in the extracted data
        stock_with_quantity = next((s for s in unique_stocks if s['ticker'] == 'AAPL'), None)
        assert stock_with_quantity is not None
        assert stock_with_quantity['quantity'] == 100

        # Check all required fields are present
        for stock in unique_stocks:
            assert 'ticker' in stock
            assert 'name' in stock
            assert 'currency' in stock
            assert 'quantity' in stock

    def test_filter_stocks_by_quantity(self, service, sample_universe_data):
        """Test filtering stocks to only include those with quantities > 0"""
        unique_stocks = service.extract_unique_stocks(sample_universe_data)
        filtered_stocks = service.filter_stocks_by_quantity(unique_stocks)

        # Should only have stocks with quantity > 0
        assert len(filtered_stocks) == 2  # AAPL (100) and TSLA (50)

        tickers = [stock['ticker'] for stock in filtered_stocks]
        assert 'AAPL' in tickers
        assert 'TSLA' in tickers
        assert 'GOOGL' not in tickers  # quantity = 0
        assert 'MSFT' not in tickers   # quantity = 0

        # Verify all filtered stocks have quantity > 0
        for stock in filtered_stocks:
            assert stock['quantity'] > 0

    def test_get_all_ticker_variations(self, service):
        """Test ticker variation generation matches legacy behavior"""
        # Test Japanese stock with .T suffix
        variations = service.get_all_ticker_variations("7203.T")
        assert "7203.T" in variations
        assert "7203" in variations

        # Test London stock with .L suffix
        variations = service.get_all_ticker_variations("VODL.L")
        assert "VODL.L" in variations
        assert "VODL" in variations

        # Test French stock with .PA suffix
        variations = service.get_all_ticker_variations("OR.PA")
        assert "OR.PA" in variations
        assert "OR" in variations

        # Test Greek stock with .AT suffix
        variations = service.get_all_ticker_variations("EEE.AT")
        assert "EEE.AT" in variations
        assert "EEE" in variations
        assert "EEEA" in variations  # Should add A suffix for short Greek stocks

        # Test share class variations
        variations = service.get_all_ticker_variations("ROCK-A.CO")
        assert "ROCK-A.CO" in variations
        assert "ROCKA.CO" in variations
        assert "ROCKA" in variations
        assert "ROCK.A.CO" in variations
        assert "ROCK.A" in variations

    def test_similarity_score(self, service):
        """Test similarity score calculation"""
        # Identical strings
        assert service.similarity_score("Apple Inc", "Apple Inc") == 1.0

        # Very different strings
        score = service.similarity_score("Apple Inc", "Microsoft Corp")
        assert 0.0 <= score <= 1.0
        assert score < 0.5

        # Similar strings
        score = service.similarity_score("Apple Inc", "Apple Incorporated")
        assert score > 0.7

        # Empty strings
        assert service.similarity_score("", "test") == 0.0
        assert service.similarity_score("test", "") == 0.0

    def test_validate_stock_match_ticker_method(self, service):
        """Test stock match validation for ticker search method"""
        universe_stock = {
            "name": "Apple Inc",
            "currency": "USD"
        }

        ibkr_contract = {
            "longName": "Apple Inc",
            "currency": "USD"
        }

        # Should be valid for ticker search with good similarity
        is_valid, reason = service.validate_stock_match(universe_stock, ibkr_contract, "ticker")
        assert is_valid
        assert "similarity" in reason.lower()

        # Should still be valid for ticker search even with poor similarity (currency match)
        ibkr_contract_poor = {
            "longName": "Different Company Name",
            "currency": "USD"
        }
        is_valid, reason = service.validate_stock_match(universe_stock, ibkr_contract_poor, "ticker")
        assert is_valid

        # Should be invalid with currency mismatch
        ibkr_contract_wrong_currency = {
            "longName": "Apple Inc",
            "currency": "EUR"
        }
        is_valid, reason = service.validate_stock_match(universe_stock, ibkr_contract_wrong_currency, "ticker")
        assert not is_valid
        assert "currency mismatch" in reason.lower()

    def test_validate_stock_match_isin_method(self, service):
        """Test stock match validation for ISIN search method"""
        universe_stock = {
            "name": "Apple Inc",
            "currency": "USD"
        }

        # Good ISIN match with high similarity
        ibkr_contract_good = {
            "longName": "Apple Inc",
            "currency": "USD"
        }
        is_valid, reason = service.validate_stock_match(universe_stock, ibkr_contract_good, "isin")
        assert is_valid

        # ISIN match with poor similarity should be rejected
        ibkr_contract_poor = {
            "longName": "Completely Different Company XYZ Corp Ltd",
            "currency": "USD"
        }
        is_valid, reason = service.validate_stock_match(universe_stock, ibkr_contract_poor, "isin")
        assert not is_valid
        assert "poor name similarity" in reason.lower()

    def test_cache_functionality(self, service):
        """Test cache statistics and clearing"""
        # Initial cache should be empty
        stats = service.get_cache_statistics()
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["total_cached_symbols"] == 0

        # Add something to cache manually
        service.cache["test_key"] = ({"symbol": "TEST"}, 0.95)
        service.cache_stats["hits"] = 5
        service.cache_stats["misses"] = 3

        # Check updated stats
        stats = service.get_cache_statistics()
        assert stats["cache_hits"] == 5
        assert stats["cache_misses"] == 3
        assert stats["hit_rate"] == 5/8
        assert stats["total_cached_symbols"] == 1

    @pytest.mark.asyncio
    async def test_clear_cache(self, service):
        """Test cache clearing functionality"""
        # Add something to cache
        service.cache["test"] = ({"symbol": "TEST"}, 0.95)
        service.cache_stats["hits"] = 10

        # Clear cache
        success = await service.clear_cache()
        assert success

        # Verify cache is cleared
        assert len(service.cache) == 0
        assert service.cache_stats["hits"] == 0
        assert service.cache_stats["misses"] == 0

    @pytest.mark.asyncio
    async def test_get_connection_pool_status(self, service):
        """Test connection pool status"""
        status = await service.get_connection_pool_status()

        assert "host" in status
        assert "port" in status
        assert "status" in status
        assert status["host"] == "127.0.0.1"
        assert status["port"] == 4002


class TestQuantityFiltering:
    """Test the new quantity filtering functionality"""

    def test_real_universe_quantity_filtering(self):
        """Test with real universe.json data structure"""
        # Load actual universe.json file if it exists
        universe_path = Path(__file__).parent.parent.parent.parent.parent / 'data' / 'universe.json'

        if universe_path.exists():
            with open(universe_path, 'r', encoding='utf-8') as f:
                universe_data = json.load(f)

            service = IBKRSearchService()

            # Extract all unique stocks
            all_stocks = service.extract_unique_stocks(universe_data)

            # Filter by quantity > 0
            filtered_stocks = service.filter_stocks_by_quantity(all_stocks)

            print(f"Total unique stocks: {len(all_stocks)}")
            print(f"Stocks with quantity > 0: {len(filtered_stocks)}")

            # Verify filtering worked correctly
            for stock in filtered_stocks:
                assert stock.get('quantity', 0) > 0

            # Should have significantly fewer stocks after filtering
            assert len(filtered_stocks) < len(all_stocks)

            # Based on our earlier analysis, should be ~123 stocks
            assert len(filtered_stocks) > 100  # At least 100
            assert len(filtered_stocks) < 150  # Less than 150

        else:
            pytest.skip("universe.json not found for integration test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])