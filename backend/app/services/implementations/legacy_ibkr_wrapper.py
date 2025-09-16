#!/usr/bin/env python3
"""
Legacy IBKR wrapper for CLI compatibility
Provides the process_all_universe_stocks function expected by main.py
Wraps the new IBKRSearchService to maintain 100% behavioral compatibility
"""

import time
from ..interfaces import IIBKRSearchService
from .ibkr_search_service import IBKRSearchService


def process_all_universe_stocks():
    """
    Legacy wrapper function for CLI compatibility
    Maintains exact same behavior as original comprehensive_enhanced_search.py

    This function is called by main.py step8_ibkr_search() and must return
    statistics in the same format as the original implementation.

    Returns:
        Dict with statistics matching legacy format:
        - total: Total unique stocks processed
        - found_isin: Count found via ISIN search
        - found_ticker: Count found via ticker search
        - found_name: Count found via name search
        - not_found: Count not found in IBKR
        - not_found_stocks: List of stocks not found with details
        - execution_time_seconds: Total execution time
    """
    # Record start time
    start_time = time.time()

    try:
        # Create service instance
        ibkr_service = IBKRSearchService()

        # Execute the search (this calls the exact same logic as legacy)
        stats = ibkr_service.process_all_universe_stocks()

        # Calculate execution time
        execution_time = time.time() - start_time

        # Add execution time to stats for CLI compatibility
        if stats:
            stats['execution_time_seconds'] = execution_time

        return stats

    except Exception as e:
        # If anything fails, let the main.py fallback handle it
        print(f"IBKR wrapper failed: {e}")
        return None


# Export for main.py compatibility
__all__ = ['process_all_universe_stocks']