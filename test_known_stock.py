#!/usr/bin/env python3
"""
Test with a known stock that should be found
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.implementations.ibkr_search_service import IBKRSearchService
import json
import time

def test_known_stock():
    """Test IBKR search with a stock that should be easily found"""

    # Create a test stock that should be found (Apple)
    test_stock = {
        'ticker': 'AAPL',
        'name': 'Apple Inc',
        'currency': 'USD',
        'isin': 'US0378331005',
        'quantity': 100
    }

    print(f"Testing with: {test_stock['name']} ({test_stock['ticker']})")
    print(f"Currency: {test_stock['currency']}")
    print(f"ISIN: {test_stock.get('isin', 'N/A')}")

    # Create service instance
    service = IBKRSearchService()

    # Connect to IBKR
    from backend.app.services.implementations.ibkr_search_service import IBApi

    app = IBApi()
    app.connect("127.0.0.1", 4002, clientId=22)  # Use different client ID

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
        print(f"ConId: {match.get('conId', 'N/A')}")
    else:
        print("NOT FOUND")

    # Disconnect
    app.disconnect()

if __name__ == "__main__":
    print("Testing Known Stock (Apple) with 20-second Timeouts")
    print("=" * 60)

    try:
        test_known_stock()
        print("\nTest completed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()