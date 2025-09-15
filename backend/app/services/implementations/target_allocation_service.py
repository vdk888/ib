"""
Target Allocation Service Implementation
Wraps legacy targetter.py functions following Interface-First Design principles
"""
import json
import os
from typing import Dict, List, Any, Tuple, Optional
import sys
import logging

from ..interfaces import ITargetAllocationService
from backend.app.core.config import settings

# Add the root directory to path to access legacy modules
from pathlib import Path
root_dir = Path(settings.data_directory).parent
sys.path.append(str(root_dir))

# Import legacy functions
from backend.app.services.implementations.legacy.targetter import (
    load_universe_data as legacy_load_universe_data,
    extract_screener_allocations as legacy_extract_screener_allocations,
    parse_180d_change as legacy_parse_180d_change,
    rank_stocks_in_screener as legacy_rank_stocks_in_screener,
    calculate_pocket_allocation as legacy_calculate_pocket_allocation,
    calculate_final_allocations as legacy_calculate_final_allocations,
    update_universe_with_allocations as legacy_update_universe_with_allocations,
    save_universe as legacy_save_universe,
    display_allocation_summary as legacy_display_allocation_summary,
    main as legacy_main
)

logger = logging.getLogger(__name__)


class TargetAllocationService(ITargetAllocationService):
    """
    Target allocation service wrapping legacy targetter.py functions
    Maintains 100% behavioral compatibility with CLI step6_calculate_targets()
    """

    def __init__(self):
        """Initialize the target allocation service"""
        self.config = settings
        # Change to the root directory for file access compatibility
        self._original_cwd = os.getcwd()
        root_dir = Path(settings.data_directory).parent
        os.chdir(str(root_dir))

    def __del__(self):
        """Restore original working directory"""
        if hasattr(self, '_original_cwd'):
            os.chdir(self._original_cwd)

    def load_universe_data(self) -> Dict[str, Any]:
        """
        Load universe.json data from data/universe.json

        Returns:
            Dict containing complete universe data structure

        Raises:
            FileNotFoundError: If universe.json does not exist
        """
        logger.info("Loading universe data")
        try:
            return legacy_load_universe_data()
        except Exception as e:
            logger.error(f"Failed to load universe data: {e}")
            raise

    def extract_screener_allocations(self, universe_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract screener allocations from portfolio optimization results

        Args:
            universe_data: Complete universe data from load_universe_data()

        Returns:
            Dict with screener keys and their target allocations (as decimals)

        Raises:
            ValueError: If no portfolio optimization results found
        """
        logger.info("Extracting screener allocations from portfolio optimization")
        try:
            return legacy_extract_screener_allocations(universe_data)
        except Exception as e:
            logger.error(f"Failed to extract screener allocations: {e}")
            raise

    def parse_180d_change(self, price_change_str: str) -> float:
        """
        Parse price_180d_change string to float

        Args:
            price_change_str: String like "12.45%" or "-5.23%"

        Returns:
            Float value (e.g., 12.45 or -5.23)
            Returns 0.0 if parsing fails
        """
        return legacy_parse_180d_change(price_change_str)

    def rank_stocks_in_screener(self, stocks: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], int, float]]:
        """
        Rank stocks within a screener by 180d price change performance

        Args:
            stocks: List of stock dictionaries from screener

        Returns:
            List of tuples: (stock_dict, rank, performance_180d)
            Rank 1 = best performing, highest rank number = worst performing
        """
        return legacy_rank_stocks_in_screener(stocks)

    def calculate_pocket_allocation(self, rank: int, total_stocks: int) -> float:
        """
        Calculate pocket allocation within screener based on rank
        Only top MAX_RANKED_STOCKS get allocation: Rank 1 gets MAX_ALLOCATION%, rank MAX_RANKED_STOCKS gets MIN_ALLOCATION%
        Ranks beyond MAX_RANKED_STOCKS get 0%

        Args:
            rank: Stock rank (1 = best)
            total_stocks: Total number of stocks in screener

        Returns:
            Pocket allocation percentage (0.00 to MAX_ALLOCATION)
        """
        return legacy_calculate_pocket_allocation(rank, total_stocks)

    def calculate_final_allocations(self, universe_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate final allocations for all stocks

        Args:
            universe_data: Complete universe data

        Returns:
            Dict with stock tickers as keys and allocation data as values:
            {
                'ticker': {
                    'ticker': str,
                    'screener': str,
                    'rank': int,
                    'performance_180d': float,
                    'pocket_allocation': float,
                    'screener_target': float,
                    'final_allocation': float
                }
            }
        """
        logger.info("Calculating final allocations for all stocks")
        try:
            return legacy_calculate_final_allocations(universe_data)
        except Exception as e:
            logger.error(f"Failed to calculate final allocations: {e}")
            raise

    def update_universe_with_allocations(
        self,
        universe_data: Dict[str, Any],
        final_allocations: Dict[str, Dict[str, Any]]
    ) -> bool:
        """
        Update universe.json with final allocation data

        Args:
            universe_data: Universe data dictionary (modified in-place)
            final_allocations: Final allocation data for each ticker

        Returns:
            bool: True if successful, False otherwise

        Side Effects:
            Modifies universe_data adding: rank, allocation_target, screen_target, final_target
            Updates both screens.stocks and all_stocks sections
        """
        logger.info("Updating universe data with allocation information")
        try:
            return legacy_update_universe_with_allocations(universe_data, final_allocations)
        except Exception as e:
            logger.error(f"Failed to update universe with allocations: {e}")
            return False

    def save_universe(self, universe_data: Dict[str, Any]) -> None:
        """
        Save updated universe data to data/universe.json

        Args:
            universe_data: Complete universe data to save

        Side Effects:
            Writes to "data/universe.json" file with proper formatting
        """
        logger.info("Saving updated universe data")
        try:
            legacy_save_universe(universe_data)
        except Exception as e:
            logger.error(f"Failed to save universe data: {e}")
            raise

    def get_allocation_summary(self, final_allocations: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get allocation summary data (equivalent to display_allocation_summary but returns JSON)

        Args:
            final_allocations: Final allocation data

        Returns:
            Dict containing:
            - sorted_allocations: List of allocation data sorted by final_allocation desc
            - total_allocation: Total allocation percentage
            - top_10_allocations: Top 10 allocations for quick reference
        """
        # Sort by final allocation descending
        sorted_allocations = sorted(final_allocations.items(), key=lambda x: x[1]['final_allocation'], reverse=True)

        # Calculate total allocation
        total_allocation = sum(data['final_allocation'] for data in final_allocations.values())

        # Get top 10 allocations
        top_10_allocations = []
        for i, (ticker, data) in enumerate(sorted_allocations[:10], 1):
            top_10_allocations.append({
                'rank_overall': i,
                'ticker': ticker,
                'final_allocation': data['final_allocation'],
                'screener': data['screener'],
                'screener_rank': data['rank'],
                'performance_180d': data['performance_180d']
            })

        # Build complete sorted allocations list
        formatted_allocations = []
        for ticker, data in sorted_allocations:
            formatted_allocations.append({
                'ticker': ticker,
                'screener': data['screener'],
                'screener_rank': data['rank'],
                'performance_180d': data['performance_180d'],
                'pocket_allocation': data['pocket_allocation'],
                'screener_target': data['screener_target'],
                'final_allocation': data['final_allocation']
            })

        return {
            'sorted_allocations': formatted_allocations,
            'total_allocation': total_allocation,
            'top_10_allocations': top_10_allocations,
            'summary_stats': {
                'total_stocks': len(final_allocations),
                'total_allocation_pct': total_allocation * 100,
                'stocks_with_allocation': len([a for a in final_allocations.values() if a['final_allocation'] > 0])
            }
        }

    def display_allocation_summary(self, final_allocations: Dict[str, Dict[str, Any]]) -> None:
        """
        Display allocation summary to console (for CLI compatibility)

        Args:
            final_allocations: Final allocation data

        Side Effects:
            Prints formatted tables to console
        """
        legacy_display_allocation_summary(final_allocations)

    def main(self) -> bool:
        """
        Main target allocation orchestration function

        Returns:
            bool: True if allocation calculation successful, False otherwise

        Side Effects:
            - Loads universe data
            - Calculates final allocations
            - Displays allocation summary
            - Updates universe.json with allocation data
            - Saves updated universe data
            - Prints progress and results to console
        """
        logger.info("Starting target allocation calculation process")
        try:
            return legacy_main()
        except Exception as e:
            logger.error(f"Target allocation process failed: {e}")
            return False