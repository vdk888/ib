"""
Legacy IBKR Search Wrapper
Maintains 100% compatibility with CLI step8_ibkr_search() while using optimized implementation
"""

import asyncio
import logging
from pathlib import Path
from .ibkr_search_service import IBKRSearchService

logger = logging.getLogger(__name__)


class LegacyIBKRWrapper:
    """
    Wrapper to maintain CLI compatibility while using optimized implementation
    """

    def __init__(self):
        self.service = IBKRSearchService(
            max_connections=5,
            cache_enabled=True
        )

    def process_all_universe_stocks(self):
        """
        Legacy function that wraps the optimized async implementation
        Maintains exact CLI behavior and console output
        """
        try:
            # Run the async function in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Configure paths relative to project root (where CLI runs from)
                script_dir = Path(__file__).parent.parent.parent.parent.parent  # Go up to project root
                universe_path = script_dir / 'data' / 'universe.json'
                output_path = script_dir / 'data' / 'universe_with_ibkr.json'

                # Use the optimized async implementation
                stats = loop.run_until_complete(
                    self.service.process_universe_stocks(
                        universe_path=str(universe_path),
                        output_path=str(output_path),
                        max_concurrent=5,
                        use_cache=True
                    )
                )

                # Cleanup connections
                loop.run_until_complete(self.service.cleanup())

                return stats

            finally:
                loop.close()

        except Exception as e:
            logger.error(f"Legacy IBKR search failed: {e}")
            raise


# Create a global instance for legacy compatibility
_legacy_wrapper = None


def get_legacy_wrapper():
    """Get or create legacy wrapper instance"""
    global _legacy_wrapper
    if _legacy_wrapper is None:
        _legacy_wrapper = LegacyIBKRWrapper()
    return _legacy_wrapper


def process_all_universe_stocks():
    """
    Legacy function entry point - maintains exact CLI compatibility
    This function replaces the original in src/comprehensive_enhanced_search.py
    but uses the optimized implementation under the hood
    """
    wrapper = get_legacy_wrapper()
    return wrapper.process_all_universe_stocks()