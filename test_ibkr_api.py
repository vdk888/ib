#!/usr/bin/env python3
"""
Test script for IBKR API service
Tests the new timeout values and API service implementation
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.implementations.ibkr_search_service import IBKRSearchService
import json
import time

def test_ibkr_search():
    """Test the IBKR search service with a small sample"""

    # Load universe.json
    with open('data/universe.json', 'r', encoding='utf-8') as f:
        universe_data = json.load(f)

    # Create service instance
    service = IBKRSearchService()

    # Extract unique stocks
    unique_stocks = service.extract_unique_stocks(universe_data)
    print(f"Found {len(unique_stocks)} unique stocks with quantities > 0")

    if len(unique_stocks) == 0:
        print("❌ No stocks with quantities > 0 found. Exiting.")
        return

    # Test with just the first 3 stocks to see the output format
    test_stocks = unique_stocks[:3]
    print(f"\nTesting with first {len(test_stocks)} stocks:")

    for i, stock in enumerate(test_stocks, 1):
        print(f"\n[{i}/{len(test_stocks)}] Stock: {stock['name']} ({stock['ticker']})")
        print(f"  Currency: {stock['currency']}")
        print(f"  ISIN: {stock.get('isin', 'N/A')}")
        print(f"  Quantity: {stock.get('quantity', 0)}")

    print(f"\nStarting IBKR search with 20-second timeouts...")

    # Start timing
    start_time = time.time()

    # Process the test stocks
    stats = service.process_all_universe_stocks()

    # End timing
    end_time = time.time()
    execution_time = end_time - start_time

    print(f"\nTotal execution time: {execution_time:.1f} seconds")
    print(f"Final statistics: {stats}")

    return stats

if __name__ == "__main__":
    print("Testing IBKR Search API Service")
    print("=" * 50)

    try:
        stats = test_ibkr_search()
        print("\nTest completed successfully!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()