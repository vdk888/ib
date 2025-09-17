#!/usr/bin/env python3
"""
Legacy IBKR wrapper for CLI compatibility
Provides the process_all_universe_stocks function expected by main.py
Calls the original legacy comprehensive_enhanced_search.py to maintain 100% behavioral compatibility
"""

import time
import sys
import os


def process_all_universe_stocks():
    """
    Legacy wrapper function for CLI compatibility
    Calls the original comprehensive_enhanced_search.py implementation directly

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
        # Add the project root to Python path to import legacy modules
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.join(current_dir, '..', '..', '..', '..')
        project_root = os.path.abspath(project_root)

        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        # Import and call the legacy implementation
        from src.comprehensive_enhanced_search import process_all_universe_stocks as legacy_process

        # Execute the legacy search
        stats = legacy_process()

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