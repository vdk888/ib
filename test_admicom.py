#!/usr/bin/env python3
"""
Test the refined ISIN validation on the Admicom case
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from comprehensive_enhanced_search import IBApi, comprehensive_stock_search
import threading
import time

def test_admicom():
    """Test the Admicom case specifically"""
    
    # The problematic case
    admicom = {
        "name": "Admicom Oyj", 
        "ticker": "ADMCM.HE", 
        "currency": "EUR", 
        "country": "Finland", 
        "isin": "FI0009006407"  # This ISIN seems to be wrong - maps to INCAP OYJ
    }
    
    # Connect to IBKR
    app = IBApi()
    app.connect("127.0.0.1", 4002, clientId=35)
    
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    timeout = 10
    start_time = time.time()
    while not app.connected and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if not app.connected:
        print("Failed to connect to IB Gateway")
        return
    
    print("Testing refined ISIN validation on Admicom case...")
    print("="*60)
    
    # Test the search
    match, score = comprehensive_stock_search(app, admicom, verbose=True)
    
    if match:
        print(f"\n*** RESULT: Found {match['symbol']} - {match['longName']} (score: {score:.1%}) ***")
        print("This should now be REJECTED due to poor name similarity!")
    else:
        print("\n*** RESULT: NOT FOUND ***")
        print("Good! The refined validation correctly rejected the false positive.")
    
    app.disconnect()

if __name__ == "__main__":
    test_admicom()