#!/usr/bin/env python3
"""
Test the improved search logic on previously failed stocks
"""

import json
import sys
import os
from pathlib import Path

# Add src to path to import our search module
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from comprehensive_enhanced_search import IBApi, comprehensive_stock_search
import threading
import time

# Failed stocks from previous run
FAILED_STOCKS = [
    {"name": "Fukushima Industries Corp", "ticker": "6420.T", "currency": "JPY", "country": "Japan", "isin": "JP3864800003"},
    {"name": "Nippon Pillar Packing Co Ltd", "ticker": "6490.T", "currency": "JPY", "country": "Japan", "isin": "JP3672400007"},
    {"name": "T&S inc.", "ticker": "4055.T", "currency": "JPY", "country": "Japan", "isin": "JP3548600006"},
    {"name": "FCE Holdings Inc.", "ticker": "9564.T", "currency": "JPY", "country": "Japan", "isin": "JP3820900009"},
    {"name": "Admicom Oyj", "ticker": "ADMCM.HE", "currency": "EUR", "country": "Finland", "isin": "FI0009006407"},
    {"name": "Firstlogic Inc", "ticker": "6037.T", "currency": "JPY", "country": "Japan", "isin": "JP3822800006"},
    {"name": "Hotelim Société Anonyme", "ticker": "MLHOT.PA", "currency": "EUR", "country": "France", "isin": "FR0010342576"},
    {"name": "Sohgo Security Services Co Ltd", "ticker": "2331.T", "currency": "JPY", "country": "Japan", "isin": "JP3415350001"},
    {"name": "Profile Systems & Software SA", "ticker": "PROF.AT", "currency": "EUR", "country": "Greece", "isin": "GRS423003007"},
    {"name": "Flexopack Societe Anonyme Commercial and Industrial Plastics Company", "ticker": "FLEXO.AT", "currency": "EUR", "country": "Greece", "isin": "GRS001003018"},
    {"name": "ArtSpark Holdings Inc", "ticker": "3663.T", "currency": "JPY", "country": "Japan", "isin": "JP3157200004"},
    {"name": "BeNextYumeshin Group Co", "ticker": "2154.T", "currency": "JPY", "country": "Japan", "isin": "JP3152800002"}
]

def test_failed_stocks():
    """Test the enhanced search on previously failed stocks"""
    
    # Connect to IBKR
    app = IBApi()
    app.connect("127.0.0.1", 4002, clientId=25)
    
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
    print("="*80)
    print("TESTING ENHANCED SEARCH ON PREVIOUSLY FAILED STOCKS")
    print("="*80)
    
    results = {
        'found': [],
        'still_not_found': []
    }
    
    for i, stock in enumerate(FAILED_STOCKS, 1):
        print(f"\n[{i}/{len(FAILED_STOCKS)}] Testing: {stock['name']} ({stock['ticker']})")
        print(f"  Currency: {stock['currency']}, Country: {stock['country']}")
        
        # Search with verbose output
        match, score = comprehensive_stock_search(app, stock, verbose=True)
        
        if match and score > 0.0:
            results['found'].append({
                'stock': stock,
                'match': match,
                'score': score
            })
            print(f"  *** SUCCESS: Found {match['symbol']} - {match['longName'][:50]}... (score: {score:.1%}) ***")
        else:
            results['still_not_found'].append(stock)
            print(f"  *** STILL NOT FOUND ***")
        
        # Delay between searches
        time.sleep(1)
    
    # Disconnect
    app.disconnect()
    
    # Summary
    print("\n" + "="*80)
    print("ENHANCED SEARCH RESULTS SUMMARY")
    print("="*80)
    print(f"Previously failed stocks: {len(FAILED_STOCKS)}")
    print(f"Now found: {len(results['found'])} ({len(results['found'])/len(FAILED_STOCKS)*100:.1f}%)")
    print(f"Still not found: {len(results['still_not_found'])} ({len(results['still_not_found'])/len(FAILED_STOCKS)*100:.1f}%)")
    
    if results['found']:
        print(f"\nNEWLY FOUND STOCKS ({len(results['found'])}):") 
        for result in results['found']:
            stock = result['stock']
            match = result['match']
            print(f"  - {stock['name']} ({stock['ticker']}) -> {match['symbol']}: {match['longName'][:50]}...")
    
    if results['still_not_found']:
        print(f"\nSTILL NOT FOUND ({len(results['still_not_found'])}):")
        for stock in results['still_not_found']:
            print(f"  - {stock['name']} ({stock['ticker']}) - {stock['currency']} - {stock['country']}")
    
    return results

if __name__ == "__main__":
    test_failed_stocks()