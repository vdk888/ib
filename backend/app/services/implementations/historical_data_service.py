"""
Historical Data Service Implementation
Wraps the legacy history_parser.py functions for API access while maintaining 100% behavioral compatibility
"""
import asyncio
import sys
import os
from typing import Dict, Any
from pathlib import Path

# Configuration imported from proper module path

from ...core.config import settings
from ..interfaces import IHistoricalDataService
from .legacy import history_parser


class HistoricalDataService(IHistoricalDataService):
    """
    Historical Data Service implementation
    Provides API access to historical performance data parsing functionality
    Maintains 100% compatibility with CLI behavior
    """

    def __init__(self):
        """Initialize the service"""
        pass

    async def parse_backtest_csv(
        self,
        csv_path: str,
        debug: bool = False
    ) -> Dict[str, Any]:
        """
        Parse a single backtest results CSV file to extract historical performance metrics

        Wraps history_parser.parse_backtest_csv() with async interface

        Args:
            csv_path: Path to the backtest results CSV file
            debug: Enable debug console output

        Returns:
            Dict containing:
            - metadata: Backtest configuration and period info
            - quarterly_performance: Array of quarterly performance data
            - statistics: Key performance statistics (returns, std dev, Sharpe ratio)
            - error: Error message if parsing failed
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            history_parser.parse_backtest_csv,
            csv_path,
            debug
        )
        return result

    async def get_all_backtest_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Parse all backtest CSV files for configured screeners

        Wraps history_parser.get_all_backtest_data() with async interface

        Returns:
            Dict mapping screener IDs to their parsed performance data
            Each screener entry contains metadata, quarterly_performance, and statistics
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            history_parser.get_all_backtest_data
        )
        return result

    async def update_universe_with_history(self) -> bool:
        """
        Update universe.json with historical performance data in metadata section

        Wraps history_parser.update_universe_with_history() with async interface

        Side Effects:
            - Reads data/universe.json
            - Adds metadata.historical_performance section with:
              * screen_name, backtest_metadata, key_statistics
              * quarterly_summary (total_quarters, avg_quarterly_return, quarterly_std)
              * quarterly_data (complete quarterly performance arrays)
            - Writes updated universe.json back to disk
            - Console output for success/error status

        Returns:
            True if successful, False if failed
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            history_parser.update_universe_with_history
        )
        return result

    async def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get formatted performance summary for all screeners

        Returns structured data equivalent to display_performance_summary() but as JSON
        instead of console output

        Returns:
            Dict containing structured performance data suitable for API responses
        """
        # Get all backtest data
        backtest_data = await self.get_all_backtest_data()

        summary = {
            "title": "Historical Performance Summary",
            "screeners": {}
        }

        for key, data in backtest_data.items():
            screen_name = settings.uncle_stock.uncle_stock_screens[key]
            screener_summary = {
                "screen_name": screen_name,
                "status": "success" if "error" not in data else "error"
            }

            if "error" in data:
                screener_summary["error"] = data["error"]
            else:
                # Extract key metadata
                metadata = data.get("metadata", {})
                screener_summary.update({
                    "backtest_period": {
                        "begin": metadata.get("Begin", "N/A"),
                        "end": metadata.get("End", "N/A")
                    },
                    "rebalance_timing": metadata.get("Rebalance timing", "N/A"),
                    "number_of_stocks": metadata.get("Number of stocks", "N/A")
                })

                # Extract key statistics
                stats = data.get("statistics", {})
                screener_summary["key_statistics"] = {
                    "yearly_return": stats.get("Return_yearly", "N/A"),
                    "yearly_std_dev": stats.get("(Avg of) Period SD_yearly", "N/A"),
                    "sharpe_ratio": stats.get("Sharpe ratio_yearly", "N/A")
                }

                # Extract quarterly summary
                quarterly_data = data.get("quarterly_performance", [])
                screener_summary["quarterly_summary"] = {
                    "total_quarters": len(quarterly_data)
                }

                # Calculate average quarterly return
                if quarterly_data:
                    returns = []
                    for q in quarterly_data:
                        try:
                            ret = q.get("return", "").replace("%", "")
                            if ret:
                                returns.append(float(ret))
                        except (ValueError, AttributeError):
                            pass

                    if returns:
                        avg_return = sum(returns) / len(returns)
                        screener_summary["quarterly_summary"]["avg_quarterly_return"] = f"{avg_return:.2f}%"

            summary["screeners"][key] = screener_summary

        return summary

    async def get_screener_backtest_data(self, screener_id: str) -> Dict[str, Any]:
        """
        Get backtest data for a specific screener

        Args:
            screener_id: Screener identifier from UNCLE_STOCK_SCREENS config

        Returns:
            Dict containing parsed backtest data or error information
        """
        if screener_id not in settings.uncle_stock.uncle_stock_screens:
            return {
                "error": f"Screener ID '{screener_id}' not found in configuration",
                "available_screeners": list(settings.uncle_stock.uncle_stock_screens.keys())
            }

        screen_name = settings.uncle_stock.uncle_stock_screens[screener_id]
        # Convert screen name to filename format (same logic as in get_all_backtest_data)
        safe_name = screen_name.replace(' ', '_').replace('/', '_')
        csv_path = f"data/files_exports/{safe_name}_backtest_results.csv"

        return await self.parse_backtest_csv(csv_path)

    def get_available_screeners(self) -> Dict[str, str]:
        """
        Get available screener configurations

        Returns:
            Dict mapping screener IDs to their display names
        """
        return settings.uncle_stock.uncle_stock_screens.copy()