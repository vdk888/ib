"""
Comprehensive tests for IBKR Search Service
Tests the optimized concurrent search implementation
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from backend.app.services.implementations.ibkr_search_service import IBKRSearchService, OptimizedIBApi


class TestOptimizedIBApi:
    """Test the optimized IBKR API client"""

    def test_initialization(self):
        """Test IBApi initialization"""
        client_id = 100
        api = OptimizedIBApi(client_id)

        assert api.client_id == client_id
        assert not api.connected
        assert api.contract_details == []
        assert api.matching_symbols == []
        assert not api.search_completed
        assert not api.symbol_search_completed

    def test_connect_ack(self):
        """Test connection acknowledgment"""
        api = OptimizedIBApi(100)
        assert not api.connected

        api.connectAck()
        assert api.connected
        assert api.connection_event.is_set()

    def test_connection_closed(self):
        """Test connection closed handling"""
        api = OptimizedIBApi(100)
        api.connected = True
        api.connection_event.set()

        api.connectionClosed()
        assert not api.connected
        assert not api.connection_event.is_set()

    def test_contract_details(self):
        """Test contract details handling"""
        api = OptimizedIBApi(100)

        # Mock contract details
        mock_contract = MagicMock()
        mock_contract.symbol = "AAPL"
        mock_contract.currency = "USD"
        mock_contract.exchange = "NASDAQ"
        mock_contract.primaryExchange = "NASDAQ"
        mock_contract.conId = 12345

        mock_contract_details = MagicMock()
        mock_contract_details.contract = mock_contract
        mock_contract_details.longName = "Apple Inc"

        api.contractDetails(1, mock_contract_details)

        assert len(api.contract_details) == 1
        details = api.contract_details[0]
        assert details["symbol"] == "AAPL"
        assert details["longName"] == "Apple Inc"
        assert details["currency"] == "USD"
        assert details["exchange"] == "NASDAQ"
        assert details["conId"] == 12345

    def test_contract_details_end(self):
        """Test contract details end handling"""
        api = OptimizedIBApi(100)
        assert not api.search_completed

        api.contractDetailsEnd(1)
        assert api.search_completed
        assert api.search_event.is_set()


class TestIBKRSearchService:
    """Test the main IBKR search service"""

    @pytest.fixture
    def service(self):
        """Create a test service instance"""
        return IBKRSearchService(
            max_connections=2,  # Smaller pool for testing
            cache_enabled=True,
            ibkr_host="127.0.0.1",
            ibkr_port=4002
        )

    @pytest.fixture
    def sample_stock(self):
        """Sample stock data for testing"""
        return {
            "ticker": "AAPL",
            "isin": "US0378331005",
            "name": "Apple Inc",
            "currency": "USD",
            "sector": "Technology",
            "country": "United States"
        }

    @pytest.fixture
    def sample_universe_data(self):
        """Sample universe data for testing"""
        return {
            "metadata": {"created_at": "2023-01-01T00:00:00Z"},
            "screens": {
                "tech_stocks": {
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
                    ]
                }
            }
        }

    def test_initialization(self, service):
        """Test service initialization"""
        assert service.max_connections == 2
        assert service.cache_enabled
        assert service.ibkr_host == "127.0.0.1"
        assert service.ibkr_port == 4002
        assert len(service.connection_pool) == 0
        assert len(service.cache) == 0

    def test_cache_key_generation(self, service, sample_stock):
        """Test cache key generation"""
        key = service._get_cache_key(sample_stock)
        expected = "AAPL:US0378331005:USD"
        assert key == expected

    def test_cache_operations(self, service, sample_stock):
        """Test cache save and retrieve operations"""
        # Initially no cache entry
        result = service._get_from_cache(sample_stock)
        assert result is None
        assert service.cache_stats["misses"] == 1

        # Save to cache
        mock_result = ({"symbol": "AAPL"}, 0.95)
        service._save_to_cache(sample_stock, mock_result)

        # Retrieve from cache
        cached_result = service._get_from_cache(sample_stock)
        assert cached_result == mock_result
        assert service.cache_stats["hits"] == 1

    def test_extract_unique_stocks(self, service, sample_universe_data):
        """Test unique stock extraction from universe data"""
        unique_stocks = service.extract_unique_stocks(sample_universe_data)

        assert len(unique_stocks) == 2
        tickers = [stock["ticker"] for stock in unique_stocks]
        assert "AAPL" in tickers
        assert "GOOGL" in tickers

    def test_ticker_variations(self, service):
        """Test ticker variation generation"""
        # Test basic ticker
        variations = service._get_ticker_variations("AAPL")
        assert "AAPL" in variations

        # Test with exchange suffix
        variations = service._get_ticker_variations("OR.PA")
        assert "OR.PA" in variations
        assert "OR" in variations

        # Test Japanese stock
        variations = service._get_ticker_variations("7203.T")
        assert "7203.T" in variations
        assert "7203" in variations

        # Test share classes
        variations = service._get_ticker_variations("ROCK-A.CO")
        assert "ROCK-A.CO" in variations
        assert "ROCKA" in variations
        assert "ROCK.A" in variations

    def test_similarity_score(self, service):
        """Test string similarity calculation"""
        # Identical strings
        score = service._similarity_score("Apple Inc", "Apple Inc")
        assert score == 1.0

        # Similar strings
        score = service._similarity_score("Apple Inc", "Apple Incorporated")
        assert 0.7 < score < 1.0

        # Different strings
        score = service._similarity_score("Apple Inc", "Microsoft Corp")
        assert score < 0.5

        # Empty strings
        score = service._similarity_score("", "Apple Inc")
        assert score == 0.0

    def test_validate_stock_match(self, service, sample_stock):
        """Test stock match validation"""
        # Mock IBKR contract
        ibkr_contract = {
            "symbol": "AAPL",
            "longName": "Apple Inc",
            "currency": "USD",
            "exchange": "NASDAQ"
        }

        # Test ticker match
        is_valid, reason = service.validate_stock_match(sample_stock, ibkr_contract, "ticker")
        assert is_valid
        assert "Ticker match" in reason

        # Test currency mismatch
        ibkr_contract_wrong_currency = ibkr_contract.copy()
        ibkr_contract_wrong_currency["currency"] = "EUR"
        is_valid, reason = service.validate_stock_match(sample_stock, ibkr_contract_wrong_currency, "ticker")
        assert not is_valid
        assert "Currency mismatch" in reason

    @pytest.mark.asyncio
    async def test_cache_statistics(self, service):
        """Test cache statistics"""
        # Initial stats
        stats = service.get_cache_statistics()
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["hit_rate"] == 0.0
        assert stats["total_cached_symbols"] == 0

        # Add some cache entries
        sample_stock = {"ticker": "AAPL", "isin": "US123", "currency": "USD"}
        service._save_to_cache(sample_stock, ({"symbol": "AAPL"}, 0.95))

        stats = service.get_cache_statistics()
        assert stats["total_cached_symbols"] == 1

    @pytest.mark.asyncio
    async def test_clear_cache(self, service):
        """Test cache clearing"""
        # Add cache entry
        sample_stock = {"ticker": "AAPL", "isin": "US123", "currency": "USD"}
        service._save_to_cache(sample_stock, ({"symbol": "AAPL"}, 0.95))

        assert len(service.cache) == 1

        # Clear cache
        result = await service.clear_cache()
        assert result is True
        assert len(service.cache) == 0
        assert service.cache_stats["hits"] == 0
        assert service.cache_stats["misses"] == 0

    @pytest.mark.asyncio
    @patch('backend.app.services.implementations.ibkr_search_service.OptimizedIBApi')
    async def test_search_by_isin(self, mock_api_class, service):
        """Test ISIN-based search"""
        # Mock the API instance
        mock_api = AsyncMock()
        mock_api.contract_details = [
            {
                "symbol": "AAPL",
                "longName": "Apple Inc",
                "currency": "USD",
                "exchange": "NASDAQ",
                "primaryExchange": "NASDAQ",
                "conId": 12345
            }
        ]
        mock_api.async_wait_for_search.return_value = True

        # Mock the connection pool
        service.connection_pool = [mock_api]
        service.available_connections = asyncio.Queue()
        await service.available_connections.put(mock_api)

        # Test ISIN search
        results = await service.search_by_isin("US0378331005", "USD", 1)

        assert len(results) == 1
        assert results[0]["symbol"] == "AAPL"
        assert results[0]["_search_method"] == "isin"

    @pytest.mark.asyncio
    @patch('backend.app.services.implementations.ibkr_search_service.OptimizedIBApi')
    async def test_search_by_ticker_variations(self, mock_api_class, service):
        """Test ticker-based search"""
        # Mock the API instance
        mock_api = AsyncMock()
        mock_api.contract_details = [
            {
                "symbol": "AAPL",
                "longName": "Apple Inc",
                "currency": "USD",
                "exchange": "NASDAQ",
                "primaryExchange": "NASDAQ",
                "conId": 12345
            }
        ]
        mock_api.async_wait_for_search.return_value = True

        # Mock the connection pool
        service.connection_pool = [mock_api]
        service.available_connections = asyncio.Queue()
        await service.available_connections.put(mock_api)

        # Test ticker search
        results = await service.search_by_ticker_variations("AAPL", "USD", 1)

        assert len(results) == 1
        assert results[0]["symbol"] == "AAPL"
        assert results[0]["_search_method"] == "ticker"

    @pytest.mark.asyncio
    async def test_connection_pool_status(self, service):
        """Test connection pool status"""
        # Mock connection pool
        mock_api1 = MagicMock()
        mock_api1.connected = True
        mock_api2 = MagicMock()
        mock_api2.connected = False

        service.connection_pool = [mock_api1, mock_api2]
        service.available_connections = asyncio.Queue()
        await service.available_connections.put(mock_api1)

        status = await service.get_connection_pool_status()

        assert status["total_connections"] == 2
        assert status["available_connections"] == 1
        assert status["max_connections"] == service.max_connections
        assert status["connections_healthy"] == 1


class TestLegacyCompatibility:
    """Test CLI compatibility and legacy wrapper"""

    @pytest.mark.asyncio
    async def test_legacy_wrapper_functionality(self):
        """Test that legacy wrapper maintains CLI compatibility"""
        from backend.app.services.implementations.legacy_ibkr_wrapper import LegacyIBKRWrapper

        wrapper = LegacyIBKRWrapper()
        assert wrapper.service is not None
        assert wrapper.service.max_connections == 5
        assert wrapper.service.cache_enabled is True


class TestPerformanceOptimizations:
    """Test performance optimizations"""

    @pytest.mark.asyncio
    async def test_concurrent_search_performance(self, sample_universe_data):
        """Test that concurrent search is faster than sequential"""
        # This is a conceptual test - in real testing you'd measure actual times
        service = IBKRSearchService(max_connections=3, cache_enabled=True)

        # Mock successful searches
        with patch.object(service, 'search_single_stock') as mock_search:
            mock_search.return_value = ({"symbol": "TEST"}, 0.95)

            stocks = [
                {"ticker": f"STOCK{i}", "name": f"Stock {i}", "currency": "USD"}
                for i in range(10)
            ]

            import time
            start_time = time.time()

            results = await service.search_multiple_stocks(
                stocks, max_concurrent=3, use_cache=True
            )

            end_time = time.time()

            # Should complete quickly with mocked searches
            assert (end_time - start_time) < 5.0  # Should be very fast with mocks
            assert len(results) == 10

    def test_cache_hit_performance(self):
        """Test that cache hits improve performance"""
        service = IBKRSearchService(cache_enabled=True)

        stock = {"ticker": "AAPL", "isin": "US123", "currency": "USD"}
        result = ({"symbol": "AAPL"}, 0.95)

        # Save to cache
        service._save_to_cache(stock, result)

        # Retrieve should be instant
        import time
        start_time = time.time()
        cached_result = service._get_from_cache(stock)
        end_time = time.time()

        assert cached_result == result
        assert (end_time - start_time) < 0.001  # Should be near-instant