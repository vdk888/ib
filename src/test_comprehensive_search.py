#!/usr/bin/env python3
"""
Simplified test version of comprehensive_enhanced_search.py
Test with just a few stocks to debug the hanging issue
"""

import json
import re
from difflib import SequenceMatcher
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import threading
import time
import os
from pathlib import Path

class IBApi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connected = False
        self.contract_details = []
        self.matching_symbols = []
        self.next_req_id = 1
        self.search_completed = False
        self.symbol_search_completed = False

    def connectAck(self):
        super().connectAck()
        print("Connected to IB Gateway")
        self.connected = True

    def connectionClosed(self):
        super().connectionClosed()
        print("Connection closed")
        self.connected = False

    def contractDetails(self, reqId, contractDetails):
        super().contractDetails(reqId, contractDetails)
        contract = contractDetails.contract
        details = {
            "symbol": contract.symbol,
            "longName": contractDetails.longName,
            "currency": contract.currency,
            "exchange": contract.exchange,
            "primaryExchange": contract.primaryExchange if contract.primaryExchange else "",
            "conId": contract.conId,
            "contract": contract
        }
        self.contract_details.append(details)
        print(f"  Contract found: {details['symbol']} - {details['longName']}")

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        print(f"  Contract search completed for request {reqId}")
        self.search_completed = True

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158, 2107]:  # Ignore common info messages
            print(f'Error {errorCode}: {errorString}')

def create_contract_from_ticker(ticker, currency, exchange="SMART"):
    contract = Contract()
    contract.symbol = ticker
    contract.secType = "STK"
    contract.currency = currency
    contract.exchange = exchange
    return contract

def test_stock_search(app, stock, verbose=True):
    """Test simplified stock search"""
    if verbose:
        print(f"\nSearching: {stock['name']} ({stock.get('ticker', 'N/A')})")

    # Strategy: Simple ticker search only
    if stock.get('ticker'):
        ticker = stock['ticker']
        currency = stock['currency']

        if verbose:
            print(f"  Trying ticker: {ticker} ({currency})")

        contract = create_contract_from_ticker(ticker, currency, "SMART")

        app.contract_details = []
        app.search_completed = False

        req_id = app.next_req_id
        app.next_req_id += 1

        print(f"  Requesting contract details (ID: {req_id})...")
        app.reqContractDetails(req_id, contract)

        # Wait for search with timeout
        timeout = 10
        start_time = time.time()
        while not app.search_completed and (time.time() - start_time) < timeout:
            time.sleep(0.1)

        if app.search_completed:
            if app.contract_details:
                result = app.contract_details[0]
                result['search_method'] = 'ticker'
                if verbose:
                    print(f"  FOUND: {result['symbol']} on {result['exchange']}")
                return result, 1.0
            else:
                if verbose:
                    print(f"  No contracts returned")
        else:
            if verbose:
                print(f"  Search timed out after {timeout} seconds")

        time.sleep(0.2)  # Small delay between searches

    return None, 0.0

def load_test_stocks():
    """Load a small subset of stocks for testing"""
    script_dir = Path(__file__).parent
    universe_path = script_dir.parent / 'data' / 'universe.json'

    if not universe_path.exists():
        print(f"❌ Error: universe.json not found at {universe_path}")
        return []

    print(f"📖 Loading universe from: {universe_path}")

    with open(universe_path, 'r', encoding='utf-8') as f:
        universe_data = json.load(f)

    # Extract first few stocks for testing
    test_stocks = []

    for screen_name, screen_data in universe_data.get('screens', {}).items():
        for stock in screen_data.get('stocks', [])[:2]:  # Only first 2 stocks per screen
            ticker = stock.get('ticker')
            if ticker and ticker not in [s.get('ticker') for s in test_stocks]:
                test_stocks.append({
                    'ticker': ticker,
                    'isin': stock.get('isin'),
                    'name': stock.get('name'),
                    'currency': stock.get('currency'),
                    'sector': stock.get('sector'),
                    'country': stock.get('country')
                })

                if len(test_stocks) >= 5:  # Limit to 5 stocks total
                    break

        if len(test_stocks) >= 5:
            break

    return test_stocks

def main():
    """Main test function"""
    print("🧪 COMPREHENSIVE SEARCH DEBUG TEST")
    print("=" * 60)

    # Load test stocks
    test_stocks = load_test_stocks()

    if not test_stocks:
        print("❌ No test stocks loaded")
        return

    print(f"📋 Testing with {len(test_stocks)} stocks:")
    for i, stock in enumerate(test_stocks, 1):
        print(f"  {i}. {stock['name']} ({stock['ticker']}) - {stock['currency']}")

    print("\n" + "=" * 60)

    # Connect to IBKR
    print("🔌 Connecting to IBKR...")
    app = IBApi()
    app.connect("127.0.0.1", 4002, clientId=22)

    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()

    # Wait for connection
    timeout = 10
    start_time = time.time()
    while not app.connected and (time.time() - start_time) < timeout:
        time.sleep(0.1)

    if not app.connected:
        print("❌ Failed to connect to IB Gateway")
        return

    # Test each stock
    stats = {'found': 0, 'not_found': 0}

    for i, stock in enumerate(test_stocks, 1):
        print(f"\n[{i}/{len(test_stocks)}]", end=" ")

        try:
            match, score = test_stock_search(app, stock, verbose=True)

            if match and score > 0.0:
                stats['found'] += 1
                print(f"  ✅ SUCCESS")
            else:
                stats['not_found'] += 1
                print(f"  ❌ NOT FOUND")

        except Exception as e:
            print(f"  💥 ERROR: {e}")
            stats['not_found'] += 1

        # Small delay between stocks
        time.sleep(1)

    # Disconnect
    app.disconnect()

    # Print results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    print(f"✅ Found: {stats['found']}")
    print(f"❌ Not Found: {stats['not_found']}")
    print(f"📈 Success Rate: {stats['found']/(stats['found']+stats['not_found'])*100:.1f}%")

if __name__ == "__main__":
    main()