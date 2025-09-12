#!/usr/bin/env python3
"""
Quick coverage analysis with smaller sample and faster execution
"""

import json
import re
from difflib import SequenceMatcher
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import threading
import time

class IBApi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connected = False
        self.contract_details = []
        self.next_req_id = 1
        self.search_completed = False

    def connectAck(self):
        super().connectAck()
        self.connected = True

    def connectionClosed(self):
        super().connectionClosed()
        self.connected = False

    def contractDetails(self, reqId, contractDetails):
        super().contractDetails(reqId, contractDetails)
        contract = contractDetails.contract
        details = {
            "symbol": contract.symbol,
            "exchange": contract.exchange,
            "currency": contract.currency,
            "longName": contractDetails.longName,
            "industry": contractDetails.industry,
        }
        self.contract_details.append(details)

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        self.search_completed = True

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        pass  # Suppress errors

def load_sample_stocks():
    """Load a diverse sample of stocks"""
    try:
        with open('data/universe.json', 'r') as f:
            data = json.load(f)
        
        sample_stocks = []
        for screen_name, screen_data in data['screens'].items():
            stocks = screen_data['stocks']
            # Take first 5 stocks from each screen for diverse sample
            sample_stocks.extend(stocks[:5])
            if len(sample_stocks) >= 15:
                break
        
        return sample_stocks[:15]  # Limit to 15 for quick test
    except Exception as e:
        print(f"Error loading data: {e}")
        return []

def create_contract_from_isin(isin, currency="USD"):
    contract = Contract()
    contract.secIdType = "ISIN"
    contract.secId = isin
    contract.secType = "STK"
    contract.currency = currency
    contract.exchange = "SMART"
    return contract

def create_contract_from_ticker(ticker, currency="USD", exchange="SMART"):
    contract = Contract()
    contract.symbol = ticker
    contract.secType = "STK"
    contract.currency = currency
    contract.exchange = exchange
    return contract

def similarity_score(str1, str2):
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def quick_search(app, stock):
    """Quick search - ISIN first, then one ticker attempt"""
    found_contracts = []
    
    # Try ISIN first
    if stock.get('isin') and stock.get('isin') not in ['null', '', None]:
        contract = create_contract_from_isin(stock['isin'], stock['currency'])
        
        app.contract_details = []
        app.search_completed = False
        app.reqContractDetails(app.next_req_id, contract)
        app.next_req_id += 1
        
        timeout_start = time.time()
        while not app.search_completed and (time.time() - timeout_start) < 2:
            time.sleep(0.05)
        
        found_contracts.extend(app.contract_details)
    
    # If no ISIN results, try ticker once
    if not found_contracts and stock.get('ticker'):
        ticker = stock['ticker']
        # Simple ticker cleanup
        clean_ticker = re.sub(r'\.[A-Z]+$', '', ticker)  # Remove exchange suffix
        if '-A' in clean_ticker:
            clean_ticker = clean_ticker.replace('-A', '.A')  # CCL-A -> CCL.A
        
        contract = create_contract_from_ticker(clean_ticker, stock['currency'])
        
        app.contract_details = []
        app.search_completed = False
        app.reqContractDetails(app.next_req_id, contract)
        app.next_req_id += 1
        
        timeout_start = time.time()
        while not app.search_completed and (time.time() - timeout_start) < 2:
            time.sleep(0.05)
        
        found_contracts.extend(app.contract_details)
    
    # Quick matching
    if found_contracts:
        universe_name = stock['name'].lower()
        universe_currency = stock['currency']
        
        best_score = 0
        for contract in found_contracts:
            score = 0
            
            # Name similarity
            if contract['longName']:
                name_sim = similarity_score(universe_name, contract['longName'].lower())
                score += name_sim * 0.6
            
            # Currency match
            if contract['currency'] == universe_currency:
                score += 0.4
            
            if score > best_score:
                best_score = score
        
        return best_score > 0.3
    
    return False

def main():
    sample_stocks = load_sample_stocks()
    if not sample_stocks:
        return
    
    print(f"Quick coverage test on {len(sample_stocks)} stocks")
    print("-" * 50)
    
    # Connect to IBKR
    app = IBApi()
    app.connect("127.0.0.1", 4002, clientId=9)
    
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    # Wait for connection
    timeout = 10
    start_time = time.time()
    while not app.connected and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if not app.connected:
        print("Failed to connect")
        return
    
    # Test each stock
    found_count = 0
    results = []
    
    for i, stock in enumerate(sample_stocks, 1):
        has_isin = stock.get('isin') and stock.get('isin') not in ['null', '', None]
        identifier = stock.get('isin', '') or stock.get('ticker', 'No ID')
        
        print(f"{i:2d}. {stock['name'][:30]:30} ({identifier[:15]:15}) ", end='')
        
        found = quick_search(app, stock)
        
        if found:
            found_count += 1
            print("FOUND")
            status = "FOUND"
        else:
            print("NOT FOUND")
            status = "NOT FOUND"
        
        results.append({
            'name': stock['name'],
            'ticker': stock.get('ticker', ''),
            'isin': stock.get('isin', ''),
            'currency': stock['currency'],
            'has_isin': has_isin,
            'status': status
        })
        
        time.sleep(0.1)  # Brief pause
    
    app.disconnect()
    
    # Summary
    total = len(sample_stocks)
    coverage = found_count / total
    
    print(f"\n{'='*50}")
    print(f"QUICK COVERAGE ANALYSIS")
    print(f"{'='*50}")
    print(f"Total tested: {total}")
    print(f"Found: {found_count}")
    print(f"Coverage: {coverage:.1%}")
    
    # Breakdown
    isin_stocks = [r for r in results if r['has_isin']]
    ticker_only = [r for r in results if not r['has_isin']]
    
    if isin_stocks:
        isin_found = len([r for r in isin_stocks if r['status'] == 'FOUND'])
        print(f"ISIN stocks: {isin_found}/{len(isin_stocks)} ({isin_found/len(isin_stocks):.1%})")
    
    if ticker_only:
        ticker_found = len([r for r in ticker_only if r['status'] == 'FOUND'])
        print(f"Ticker-only: {ticker_found}/{len(ticker_only)} ({ticker_found/len(ticker_only):.1%})")
    
    # Currency breakdown
    currencies = {}
    for result in results:
        curr = result['currency']
        if curr not in currencies:
            currencies[curr] = {'total': 0, 'found': 0}
        currencies[curr]['total'] += 1
        if result['status'] == 'FOUND':
            currencies[curr]['found'] += 1
    
    print(f"\nBy currency:")
    for curr, stats in sorted(currencies.items()):
        if stats['total'] > 0:
            pct = stats['found'] / stats['total']
            print(f"  {curr}: {stats['found']}/{stats['total']} ({pct:.1%})")

if __name__ == "__main__":
    main()