#!/usr/bin/env python3
"""
Test the exact same cache logic as the legacy implementation
"""

import json
import sys
from pathlib import Path

# Add backend path for database service import (same as legacy)
sys.path.append(str(Path(__file__).parent.parent / 'backend' / 'app'))
from services.database_service import get_database_service

def extract_unique_stocks(universe_data):
    """Extract unique stocks - copy of legacy function"""
    unique_stocks = {}

    # Process all screens
    for screen_name, screen_data in universe_data.get('screens', {}).items():
        for stock in screen_data.get('stocks', []):
            # Use ticker as unique key
            ticker = stock.get('ticker')
            if ticker:
                current_stock = {
                    'ticker': ticker,
                    'isin': stock.get('isin'),
                    'name': stock.get('name'),
                    'currency': stock.get('currency'),
                    'sector': stock.get('sector'),
                    'country': stock.get('country'),
                    'quantity': stock.get('quantity', 0),
                    'final_target': stock.get('final_target', 0)
                }

                # If ticker already exists, pick the one with highest quantity
                if ticker in unique_stocks:
                    existing_quantity = unique_stocks[ticker].get('quantity', 0)
                    current_quantity = current_stock.get('quantity', 0)

                    if (current_quantity > existing_quantity or
                        (current_quantity == existing_quantity and
                         current_stock.get('final_target', 0) > unique_stocks[ticker].get('final_target', 0))):
                        unique_stocks[ticker] = current_stock
                else:
                    unique_stocks[ticker] = current_stock

    # Filter to only include stocks with quantities > 0
    filtered_stocks = [stock for stock in unique_stocks.values() if stock.get('quantity', 0) > 0]
    return filtered_stocks

def test_legacy_cache_lookup():
    """Test exact same cache lookup as legacy"""

    # Load universe.json - same as legacy
    script_dir = Path(__file__).parent
    universe_path = script_dir / 'data' / 'universe.json'

    with open(universe_path, 'r', encoding='utf-8') as f:
        universe_data = json.load(f)

    # Extract unique stocks - same as legacy
    unique_stocks = extract_unique_stocks(universe_data)
    print(f"Found {len(unique_stocks)} unique stocks with quantities > 0")

    # Get database service - same as legacy
    legacy_db_path = script_dir / 'data' / 'ibkr_cache.db'
    print(f"Database path: {legacy_db_path}")

    db_service = get_database_service(str(legacy_db_path))

    # Separate cached and uncached stocks - same as legacy
    print("Checking cache for IBKR details...")
    cached_stocks, uncached_stocks = db_service.get_cached_stocks(unique_stocks)

    print(f"Cache results: {len(cached_stocks)} hits, {len(uncached_stocks)} misses")

    if len(cached_stocks) > 0:
        print("\nCached stocks found:")
        for stock in cached_stocks[:5]:  # Show first 5
            print(f"  - {stock['name']} ({stock['ticker']})")

    if len(uncached_stocks) > 0:
        print(f"\nFirst 5 uncached stocks:")
        for stock in uncached_stocks[:5]:  # Show first 5
            print(f"  - {stock['name']} ({stock['ticker']})")

if __name__ == "__main__":
    test_legacy_cache_lookup()