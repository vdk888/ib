"""
High-level screener service implementation
Orchestrates data fetching operations with legacy compatibility
"""
import logging
from typing import Dict, Any, Optional

from ..interfaces import IScreenerService, IDataProvider
from ...core.config import settings
from ...core.exceptions import UncleStockInvalidQueryError
from .uncle_stock_provider import UncleStockProvider
from .file_manager import FileManager

logger = logging.getLogger(__name__)


class ScreenerService(IScreenerService):
    """
    Screener service orchestrating data fetching operations

    This service provides a high-level interface for screener operations
    while maintaining 100% compatibility with legacy CLI behavior
    """

    def __init__(
        self,
        data_provider: Optional[IDataProvider] = None,
        file_manager: Optional[FileManager] = None
    ):
        """
        Initialize screener service

        Args:
            data_provider: Data provider implementation (defaults to UncleStockProvider)
            file_manager: File manager implementation (defaults to FileManager)
        """
        self.file_manager = file_manager or FileManager()
        self.data_provider = data_provider or UncleStockProvider(self.file_manager)

    async def fetch_screener_data(
        self,
        screener_id: str,
        max_results: int = 200
    ) -> Dict[str, Any]:
        """
        Fetch current data for a specific screener

        Args:
            screener_id: Screener identifier from configuration
            max_results: Maximum number of results to return

        Returns:
            Dict with screener data matching legacy format

        Raises:
            UncleStockInvalidQueryError: If screener_id is not configured
        """
        # Validate screener ID
        screener_configs = self.data_provider.get_screener_configurations()
        if screener_id not in screener_configs:
            available_screeners = ", ".join(screener_configs.keys())
            raise UncleStockInvalidQueryError(
                f"Unknown screener ID: {screener_id}. Available screeners: {available_screeners}",
                details={
                    "screener_id": screener_id,
                    "available_screeners": list(screener_configs.keys())
                }
            )

        # Get query name from configuration
        query_name = screener_configs[screener_id]

        # Fetch data from provider
        result = await self.data_provider.get_current_stocks(
            query_name=query_name,
            max_results=max_results
        )

        # Enhance result with screener metadata
        if isinstance(result, dict):
            result["screener_id"] = screener_id
            result["screener_name"] = query_name

        logger.info(
            f"Fetched screener data for {screener_id}",
            extra={
                "screener_id": screener_id,
                "success": result.get("success", False),
                "symbol_count": len(result.get("data", [])) if result.get("success") else 0
            }
        )

        return result

    async def fetch_screener_history(self, screener_id: str) -> Dict[str, Any]:
        """
        Fetch historical data for a specific screener

        Args:
            screener_id: Screener identifier from configuration

        Returns:
            Dict with screener history matching legacy format

        Raises:
            UncleStockInvalidQueryError: If screener_id is not configured
        """
        # Validate screener ID
        screener_configs = self.data_provider.get_screener_configurations()
        if screener_id not in screener_configs:
            available_screeners = ", ".join(screener_configs.keys())
            raise UncleStockInvalidQueryError(
                f"Unknown screener ID: {screener_id}. Available screeners: {available_screeners}",
                details={
                    "screener_id": screener_id,
                    "available_screeners": list(screener_configs.keys())
                }
            )

        # Get query name from configuration
        query_name = screener_configs[screener_id]

        # Fetch history from provider
        result = await self.data_provider.get_screener_history(query_name=query_name)

        # Enhance result with screener metadata
        if isinstance(result, dict):
            result["screener_id"] = screener_id
            result["screener_name"] = query_name

        logger.info(
            f"Fetched screener history for {screener_id}",
            extra={
                "screener_id": screener_id,
                "success": result.get("success", False)
            }
        )

        return result

    async def fetch_all_screener_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch current data for all screeners

        Returns:
            Dict mapping screener IDs to their data results
        """
        logger.info("Starting batch fetch of all screener data")

        # Delegate to data provider (maintains legacy console output)
        results = await self.data_provider.get_all_screeners()

        # Enhance results with metadata
        for screener_id, result in results.items():
            if isinstance(result, dict):
                result["screener_id"] = screener_id
                screener_configs = self.data_provider.get_screener_configurations()
                result["screener_name"] = screener_configs.get(screener_id, "Unknown")

        # Log summary
        successful_count = sum(1 for r in results.values() if r.get("success", False))
        total_symbols = sum(
            len(r.get("data", []))
            for r in results.values()
            if r.get("success", False) and isinstance(r.get("data"), list)
        )

        logger.info(
            "Completed batch fetch of all screener data",
            extra={
                "total_screeners": len(results),
                "successful_screeners": successful_count,
                "total_symbols": total_symbols
            }
        )

        return results

    async def fetch_all_screener_histories(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch historical data for all screeners

        Returns:
            Dict mapping screener IDs to their history results
        """
        logger.info("Starting batch fetch of all screener histories")

        # Delegate to data provider (maintains legacy console output)
        results = await self.data_provider.get_all_screener_histories()

        # Enhance results with metadata
        for screener_id, result in results.items():
            if isinstance(result, dict):
                result["screener_id"] = screener_id
                screener_configs = self.data_provider.get_screener_configurations()
                result["screener_name"] = screener_configs.get(screener_id, "Unknown")

        # Log summary
        successful_count = sum(1 for r in results.values() if r.get("success", False))

        logger.info(
            "Completed batch fetch of all screener histories",
            extra={
                "total_screeners": len(results),
                "successful_screeners": successful_count
            }
        )

        return results

    def get_available_screeners(self) -> Dict[str, str]:
        """
        Get list of available screeners

        Returns:
            Dict mapping screener IDs to display names
        """
        return self.data_provider.get_screener_configurations()

    async def run_step1_equivalent(self) -> bool:
        """
        Run the equivalent of CLI step1_fetch_data() function

        This method provides the exact same functionality as the legacy
        step1_fetch_data() function for testing compatibility

        Returns:
            True if successful, False otherwise
        """
        print("STEP 1: Fetching data from Uncle Stock API")
        print("=" * 50)

        screener_configs = self.get_available_screeners()
        print(f"Configured screeners: {list(screener_configs.values())}")

        # Fetch current stocks from all screeners
        print("\nFetching current stocks from all screeners...")
        all_stocks = await self.fetch_all_screener_data()

        # Fetch backtest history from all screeners
        print("\nFetching backtest history from all screeners...")
        all_histories = await self.fetch_all_screener_histories()

        # Display summary (exact legacy format)
        print("\n" + "=" * 50)
        print("STEP 1 SUMMARY")
        print("=" * 50)

        total_stocks = 0
        for screener_id, screener_name in screener_configs.items():
            stocks_result = all_stocks.get(screener_id, {})
            history_result = all_histories.get(screener_id, {})

            print(f"\n{screener_name}:")

            if stocks_result.get('success'):
                stock_count = len(stocks_result['data'])
                total_stocks += stock_count
                print(f"  + Stocks: {stock_count} found")
                print(f"    First 5: {stocks_result['data'][:5]}")
                if 'csv_file' in stocks_result:
                    print(f"    CSV: {stocks_result['csv_file']}")
            else:
                print(f"  X Stocks: Failed - {stocks_result.get('data', 'Unknown error')}")

            if history_result.get('success'):
                print(f"  + History: Retrieved")
                if 'csv_file' in history_result:
                    print(f"    CSV: {history_result['csv_file']}")
            else:
                print(f"  X History: Failed - {history_result.get('data', 'Unknown error')}")

        print(f"\nTotal stocks across all screeners: {total_stocks}")
        print("Step 1 complete - CSV files saved to data/files_exports/")

        return True