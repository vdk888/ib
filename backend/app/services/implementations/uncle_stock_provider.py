"""
Uncle Stock data provider implementation
Wraps legacy screener functions with exact behavioral compatibility
"""
import asyncio
import logging
from typing import Dict, Any, Optional
import requests
from datetime import datetime

from ..interfaces import IDataProvider
from ...core.config import settings
from ...core.exceptions import (
    UncleStockAPIError,
    UncleStockTimeoutError,
    UncleStockInvalidQueryError,
    UncleStockRateLimitError
)
from .file_manager import FileManager

logger = logging.getLogger(__name__)


class UncleStockProvider(IDataProvider):
    """
    Uncle Stock API provider with 100% legacy compatibility

    This implementation exactly replicates the behavior of the legacy
    screener.py functions while providing an async interface
    """

    def __init__(self, file_manager: Optional[FileManager] = None):
        """
        Initialize Uncle Stock provider

        Args:
            file_manager: File management service (will create default if None)
        """
        self.file_manager = file_manager or FileManager()
        self.base_url = "https://www.unclestock.com"
        self.timeout = settings.uncle_stock.uncle_stock_timeout
        self.user_id = settings.uncle_stock.uncle_stock_user_id
        self.screener_configs = settings.uncle_stock.uncle_stock_screens

        if not self.user_id:
            raise UncleStockInvalidQueryError(
                "Uncle Stock User ID not configured",
                details={"missing_config": "uncle_stock_user_id"}
            )

    async def get_current_stocks(
        self,
        query_name: str,
        max_results: int = 200
    ) -> Dict[str, Any]:
        """
        Fetch current stocks from Uncle Stock screener query

        This is an async wrapper around the legacy get_current_stocks function
        that maintains 100% behavioral compatibility
        """
        if not query_name:
            return {
                'success': False,
                'data': "Query name must be provided",
                'raw_response': None
            }

        # Prepare request parameters (exact legacy format)
        params = {
            'user': self.user_id,
            'query': query_name,
            'results': max_results,
            'owner': self.user_id
        }

        try:
            # Execute HTTP request in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    f"{self.base_url}/csv",
                    params=params,
                    timeout=self.timeout
                )
            )

            if response.status_code == 200:
                return await self._process_current_stocks_response(response, query_name)
            elif response.status_code == 429:
                raise UncleStockRateLimitError(
                    f"Rate limit exceeded for query: {query_name}",
                    details={"query_name": query_name, "status_code": response.status_code}
                )
            else:
                return {
                    'success': False,
                    'data': f"API returned status {response.status_code}",
                    'raw_response': response.text
                }

        except requests.exceptions.Timeout:
            raise UncleStockTimeoutError(
                f"Timeout while fetching current stocks for: {query_name}",
                details={"query_name": query_name, "timeout": self.timeout}
            )
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'data': str(e),
                'raw_response': None
            }

    async def get_screener_history(self, query_name: str) -> Dict[str, Any]:
        """
        Fetch screener backtest history from Uncle Stock

        Async wrapper maintaining 100% legacy compatibility
        """
        if not query_name:
            return {
                'success': False,
                'data': "Query name must be provided",
                'raw_response': None
            }

        # Prepare request parameters (exact legacy format)
        params = {
            'user': self.user_id,
            'query': query_name,
            'owner': self.user_id
        }

        try:
            # Execute HTTP request in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    f"{self.base_url}/backtest-result",
                    params=params,
                    timeout=self.timeout
                )
            )

            if response.status_code == 200:
                return await self._process_history_response(response, query_name)
            elif response.status_code == 429:
                raise UncleStockRateLimitError(
                    f"Rate limit exceeded for history query: {query_name}",
                    details={"query_name": query_name, "status_code": response.status_code}
                )
            else:
                return {
                    'success': False,
                    'data': f"API returned status {response.status_code}",
                    'raw_response': response.text
                }

        except requests.exceptions.Timeout:
            raise UncleStockTimeoutError(
                f"Timeout while fetching history for: {query_name}",
                details={"query_name": query_name, "timeout": self.timeout}
            )
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'data': str(e),
                'raw_response': None
            }

    async def get_all_screeners(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch current stocks from all configured screeners

        Maintains exact legacy behavior including console output
        """
        results = {}

        for key, screen_name in self.screener_configs.items():
            # Print progress message (legacy compatibility)
            print(f"\nFetching stocks for {screen_name}...")

            try:
                result = await self.get_current_stocks(query_name=screen_name)
                results[key] = result

                # Print result summary (legacy compatibility)
                if result['success']:
                    print(f"+ Found {len(result['data'])} stocks for {screen_name}")
                else:
                    print(f"X Error fetching {screen_name}: {result['data']}")

            except Exception as e:
                # Handle individual screener failures gracefully
                error_result = {
                    'success': False,
                    'data': str(e),
                    'raw_response': None
                }
                results[key] = error_result
                print(f"X Error fetching {screen_name}: {str(e)}")

        return results

    async def get_all_screener_histories(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch backtest history from all configured screeners

        Maintains exact legacy behavior including console output
        """
        results = {}

        for key, screen_name in self.screener_configs.items():
            # Print progress message (legacy compatibility)
            print(f"\nFetching history for {screen_name}...")

            try:
                result = await self.get_screener_history(query_name=screen_name)
                results[key] = result

                # Print result summary (legacy compatibility)
                if result['success']:
                    print(f"+ Retrieved history for {screen_name}")
                else:
                    print(f"X Error fetching history for {screen_name}: {result['data']}")

            except Exception as e:
                # Handle individual screener failures gracefully
                error_result = {
                    'success': False,
                    'data': str(e),
                    'raw_response': None
                }
                results[key] = error_result
                print(f"X Error fetching history for {screen_name}: {str(e)}")

        return results

    def get_screener_configurations(self) -> Dict[str, str]:
        """
        Get available screener configurations

        Returns the configured screener mappings
        """
        return self.screener_configs.copy()

    async def _process_current_stocks_response(
        self,
        response: requests.Response,
        query_name: str
    ) -> Dict[str, Any]:
        """
        Process successful current stocks response

        Replicates exact legacy CSV processing and file saving logic
        """
        # Generate filename using legacy format
        filename = self.file_manager.get_csv_filename(query_name, "current_screen")

        # Save CSV file (this handles directory creation and console output)
        csv_file_path = self.file_manager.save_csv_data(
            response.text,
            filename,
            settings.uncle_stock.data_exports_dir
        )

        # Parse CSV to extract symbols (exact legacy logic)
        lines = response.text.split('\n')
        symbols = []

        # Skip metadata and header lines (legacy: not line.startswith('sep='))
        data_lines = [line for line in lines if line and not line.startswith('sep=')]

        if len(data_lines) > 1:
            for line in data_lines[1:]:  # Skip header (exact legacy logic)
                if line.strip():
                    parts = line.split(',')
                    if parts:
                        # Extract symbol from first column (legacy: strip quotes and whitespace)
                        symbol = parts[0].strip('"').strip()
                        if symbol:
                            symbols.append(symbol)

        return {
            'success': True,
            'data': symbols,
            'raw_response': response.text,
            'csv_file': csv_file_path
        }

    async def _process_history_response(
        self,
        response: requests.Response,
        query_name: str
    ) -> Dict[str, Any]:
        """
        Process successful history response

        Replicates exact legacy CSV processing and file saving logic
        """
        # Generate filename using legacy format
        filename = self.file_manager.get_csv_filename(query_name, "backtest_results")

        # Save CSV file
        csv_file_path = self.file_manager.save_csv_data(
            response.text,
            filename,
            settings.uncle_stock.data_exports_dir
        )

        # Parse CSV to structured data (exact legacy logic)
        lines = response.text.split('\n')
        history_data = {}

        for line in lines:
            if line.strip() and ',' in line:
                parts = line.split(',', 1)  # Split on first comma only (legacy logic)
                if len(parts) == 2:
                    key = parts[0].strip('"').strip()
                    value = parts[1].strip('"').strip()
                    if key and value:
                        history_data[key] = value

        return {
            'success': True,
            'data': history_data,
            'raw_response': response.text,
            'csv_file': csv_file_path
        }