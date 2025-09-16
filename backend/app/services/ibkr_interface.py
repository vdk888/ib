"""
IBKR Search Service Interface
Optimized for high-performance concurrent search with caching
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Callable


class IIBKRSearchService(ABC):
    """
    Interface for Interactive Brokers stock search service
    Optimized for high-performance concurrent search with caching

    Performance Requirements:
    - Reduce search time from 30+ minutes to under 5 minutes
    - Support concurrent search operations
    - Implement intelligent caching to avoid repeated searches
    - Provide real-time progress tracking for long-running operations
    """

    @abstractmethod
    def search_single_stock(
        self,
        stock: Dict[str, Any],
        use_cache: bool = True
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Search for a single stock using comprehensive multi-strategy approach

        Args:
            stock: Stock dictionary with keys: ticker, isin, name, currency, sector, country
            use_cache: Whether to use cached results if available

        Returns:
            Tuple of (best_match_contract_dict_or_None, similarity_score)
            Contract dict contains: symbol, longName, exchange, primaryExchange, conId,
            currency, search_method, match_score
        """
        pass

    @abstractmethod
    def search_multiple_stocks(
        self,
        stocks: List[Dict[str, Any]],
        max_concurrent: int = 5,
        use_cache: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Tuple[Optional[Dict[str, Any]], float]]:
        """
        Search for multiple stocks concurrently with progress tracking

        Args:
            stocks: List of stock dictionaries
            max_concurrent: Maximum number of concurrent IBKR connections
            use_cache: Whether to use cached results if available
            progress_callback: Optional callback function(current, total, current_stock)

        Returns:
            Dict mapping stock tickers to (match_result, similarity_score) tuples
        """
        pass

    @abstractmethod
    def process_universe_stocks(
        self,
        universe_path: str = 'data/universe.json',
        output_path: str = 'data/universe_with_ibkr.json',
        max_concurrent: int = 5,
        use_cache: bool = True,
        quantity_filter: bool = False
    ) -> Dict[str, Any]:
        """
        Process all unique stocks from universe.json with optimized concurrent search

        Args:
            universe_path: Path to input universe.json file
            output_path: Path to output universe_with_ibkr.json file
            max_concurrent: Maximum number of concurrent IBKR connections
            use_cache: Whether to use cached results

        Returns:
            Statistics dict with keys: total, found_isin, found_ticker, found_name,
            not_found, not_found_stocks, execution_time_seconds

        Side Effects:
            - Reads universe.json
            - Creates/updates universe_with_ibkr.json
            - Updates cache with successful searches
            - Extensive progress logging to console
        """
        pass

    @abstractmethod
    def search_by_isin(
        self,
        isin: str,
        currency: str,
        connection_id: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Search for stock by ISIN using specific IBKR connection

        Args:
            isin: International Securities Identification Number
            currency: Stock currency (EUR, USD, JPY, etc.)
            connection_id: IBKR client connection ID to use

        Returns:
            List of matching contract details dictionaries
        """
        pass

    @abstractmethod
    def search_by_ticker_variations(
        self,
        ticker: str,
        currency: str,
        connection_id: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Search for stock by ticker and all its variations

        Args:
            ticker: Original ticker symbol
            currency: Stock currency
            connection_id: IBKR client connection ID to use

        Returns:
            List of matching contract details dictionaries
        """
        pass

    @abstractmethod
    def search_by_company_name(
        self,
        stock: Dict[str, Any],
        connection_id: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Search for stock by company name parts using reqMatchingSymbols

        Args:
            stock: Stock dictionary with name and currency
            connection_id: IBKR client connection ID to use

        Returns:
            List of matching contract details dictionaries
        """
        pass

    @abstractmethod
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get cache performance statistics

        Returns:
            Dict with keys: cache_hits, cache_misses, hit_rate, total_cached_symbols
        """
        pass

    @abstractmethod
    def clear_cache(self) -> bool:
        """
        Clear all cached search results

        Returns:
            True if cache cleared successfully
        """
        pass

    @abstractmethod
    def extract_unique_stocks(self, universe_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract unique stocks from universe data using ticker as key

        Args:
            universe_data: Universe dictionary from JSON

        Returns:
            List of unique stock dictionaries with standard fields
        """
        pass

    @abstractmethod
    def validate_stock_match(
        self,
        universe_stock: Dict[str, Any],
        ibkr_contract: Dict[str, Any],
        search_method: str
    ) -> Tuple[bool, str]:
        """
        Validate if IBKR contract matches universe stock

        Args:
            universe_stock: Original stock from universe
            ibkr_contract: IBKR contract details
            search_method: Method used to find match ("isin", "ticker", "name")

        Returns:
            Tuple of (is_valid_match, validation_reason)
        """
        pass

    @abstractmethod
    def get_connection_pool_status(self) -> Dict[str, Any]:
        """
        Get status of IBKR connection pool

        Returns:
            Dict with connection pool statistics and health status
        """
        pass