#!/usr/bin/env python3
"""
Test L'Oréal specifically to debug the issue
"""

import json
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from comprehensive_enhanced_search import *
from pathlib import Path

def test_loreal():
    # Load universe.json
    universe_path = Path(__file__).parent / 'data' / 'universe.json'
    
    with open(universe_path, 'r', encoding='utf-8') as f:
        universe_data = json.load(f)
    
    # Find L'Oréal
    loreal_stock = None
    for screen_name, screen_data in universe_data.get('screens', {}).items():
        for stock in screen_data.get('stocks', []):
            if stock.get('ticker') == 'OR.PA':
                loreal_stock = stock
                break
        if loreal_stock:
            break
    
    if not loreal_stock:
        print("L'Oréal not found in universe.json")
        return
    
    print(f"Testing L'Oréal: {loreal_stock}")
    print(f"ISIN: {loreal_stock.get('isin')}")
    print(f"Currency: {loreal_stock.get('currency')}")
    
    # Connect to IBKR
    app = IBApi()
    app.connect("127.0.0.1", 4002, clientId=30)
    
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    timeout = 10
    start_time = time.time()
    while not app.connected and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if not app.connected:
        print("Failed to connect to IB Gateway")
        return
    
    print("Connected to IB Gateway")
    print("="*50)
    
    # Search with full verbose output
    match, score = comprehensive_stock_search(app, loreal_stock, verbose=True)
    
    print("="*50)
    if match:
        print(f"FINAL RESULT: FOUND - {match['symbol']} on {match['exchange']} (score: {score:.1%})")
    else:
        print(f"FINAL RESULT: NOT FOUND (score: {score:.1%})")
    
    app.disconnect()

if __name__ == "__main__":
    test_loreal()