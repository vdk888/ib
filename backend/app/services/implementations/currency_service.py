"""
Currency Service Implementation
Wraps legacy currency functions to provide API-compatible interface
Maintains 100% behavioral compatibility with CLI implementation
"""

import os
import sys
from typing import Dict, Set

# Add the project root to the Python path to import legacy modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../../../'))
sys.path.insert(0, project_root)

from backend.app.services.interfaces import ICurrencyService
from backend.app.services.implementations.legacy import currency as legacy_currency


class CurrencyService(ICurrencyService):
    """
    Currency Service implementation wrapping legacy currency functions

    This service provides 100% behavioral compatibility with the original CLI implementation
    by directly calling the legacy currency functions and preserving all side effects,
    console output, and file operations exactly as they were in the original system.

    All methods maintain:
    - Identical return types and values
    - Identical console output (+ and X prefixes, formatting)
    - Identical file I/O operations and error handling
    - Identical external API calls and timeout behavior
    """

    def __init__(self):
        """Initialize Currency Service"""
        # No initialization needed - using legacy functions directly
        pass

    def fetch_exchange_rates(self) -> Dict[str, float]:
        """
        Fetch current EUR-based exchange rates from external API

        Wraps legacy_currency.fetch_exchange_rates() with identical behavior:
        - Makes HTTP request to exchangerate-api.com with 10-second timeout
        - Returns dict with currency codes and EUR exchange rates
        - Always includes EUR with rate 1.0 as base currency
        - Console output with + prefix for success, X prefix for errors
        - Returns empty dict on any API failures or network issues

        Returns:
            Dict[str, float]: Currency codes mapped to EUR exchange rates
        """
        return legacy_currency.fetch_exchange_rates()

    def get_currencies_from_universe(self) -> Set[str]:
        """
        Extract all unique currency codes from universe.json file

        Wraps legacy_currency.get_currencies_from_universe() with identical behavior:
        - Reads from "data/universe.json" with UTF-8 encoding
        - Extracts currencies from both "screens" and "all_stocks" sections
        - Returns set of unique currency codes (de-duplicated)
        - Console output with currency count and sorted comma-separated list
        - Returns empty set if file missing or JSON parsing fails

        Returns:
            Set[str]: Unique currency codes found in universe data
        """
        return legacy_currency.get_currencies_from_universe()

    def update_universe_with_exchange_rates(self, exchange_rates: Dict[str, float]) -> bool:
        """
        Update universe.json by adding EUR exchange rates to ALL stock objects

        Wraps legacy_currency.update_universe_with_exchange_rates() with identical behavior:
        - Reads and writes "data/universe.json" with UTF-8 encoding
        - Updates both "screens" and "all_stocks" sections
        - Adds "eur_exchange_rate" field to each stock dictionary
        - Tracks separate counters and displays progress for each section
        - Pretty JSON formatting with 2-space indent, ensure_ascii=False
        - Console output with update counts and missing rate warnings

        Args:
            exchange_rates: Dict with currency codes and their EUR exchange rates

        Returns:
            bool: True if successful file update, False on any errors
        """
        return legacy_currency.update_universe_with_exchange_rates(exchange_rates)

    def display_exchange_rate_summary(self, exchange_rates: Dict[str, float]) -> None:
        """
        Display formatted console table of fetched exchange rates

        Wraps legacy_currency.display_exchange_rate_summary() with identical behavior:
        - Prints "EXCHANGE RATES TO EUR" header with 50 "=" character border
        - Displays currencies alphabetically sorted by currency code
        - Shows rates with 4 decimal precision
        - Special handling: EUR displays as "(base currency)"
        - Rate interpretation: "1 EUR = {rate} {currency}" format

        Args:
            exchange_rates: Dict with currency codes and their EUR exchange rates
        """
        legacy_currency.display_exchange_rate_summary(exchange_rates)

    def run_currency_update(self) -> bool:
        """
        Execute complete 3-step currency update workflow

        Wraps legacy_currency.main() with identical behavior:
        - Step 1: Analyze currencies in universe.json
        - Step 2: Fetch current exchange rates from external API
        - Step 3: Update universe.json with EUR exchange rates
        - Console output: Main header, step progress, rate summary, confirmation
        - Error handling: Early exit on any step failure
        - Top-level exception handler for unexpected errors

        Returns:
            bool: True if entire workflow completed successfully, False on failure
        """
        return legacy_currency.main()