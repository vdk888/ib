#!/usr/bin/env python3
"""
Test single stock search with new 20-second timeouts
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.implementations.ibkr_search_service import IBKRSearchService
import json
import time

def test_single_stock():
    """Test IBKR search with one stock to see the new timeout behavior"""

    # Load universe.json
    with open('data/universe.json', 'r', encoding='utf-8') as f:
        universe_data = json.load(f)

    # Create service instance
    service = IBKRSearchService()

    # Extract unique stocks
    unique_stocks = service.extract_unique_stocks(universe_data)
    print(f"Found {len(unique_stocks)} unique stocks with quantities > 0")

    if len(unique_stocks) == 0:
        print("No stocks with quantities > 0 found. Exiting.")
        return

    # Test with just the first stock
    test_stock = unique_stocks[0]
    print(f"\nTesting with: {test_stock['name']} ({test_stock['ticker']})")
    print(f"Currency: {test_stock['currency']}")
    print(f"ISIN: {test_stock.get('isin', 'N/A')}")
    print(f"Quantity: {test_stock.get('quantity', 0)}")

    # Connect to IBKR
    from backend.app.services.implementations.ibkr_search_service import IBApi

    app = IBApi()
    app.connect("127.0.0.1", 4002, clientId=21)  # Use different client ID

    import threading
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()

    timeout = 10
    start_time = time.time()
    while not app.connected and (time.time() - start_time) < timeout:
        time.sleep(0.1)

    if not app.connected:
        print("Failed to connect to IB Gateway")
        return

    print("\nConnected to IB Gateway")
    print("Starting search with 20-second timeouts...")
    print("-" * 50)

    # Start timing
    search_start = time.time()

    # Search for the stock (with verbose output)
    match, score = service.comprehensive_stock_search(app, test_stock, verbose=True)

    # End timing
    search_end = time.time()
    search_time = search_end - search_start

    print("-" * 50)
    print(f"Search completed in {search_time:.1f} seconds")

    if match and score > 0.0:
        print(f"FOUND: {match['symbol']} on {match['exchange']}")
        print(f"Name: {match['longName']}")
        print(f"Score: {score:.1%}")
        print(f"Method: {match.get('search_method', 'unknown')}")
    else:
        print("NOT FOUND")

    # Disconnect
    app.disconnect()

if __name__ == "__main__":
    print("Testing Single Stock Search with 20-second Timeouts")
    print("=" * 60)

    try:
        test_single_stock()
        print("\nTest completed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()