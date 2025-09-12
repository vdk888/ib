#!/usr/bin/env python3
"""
Full coverage test to determine:
1. What % of universe stocks are found on IBKR
2. How many via ISIN vs ticker fallback
3. Which stocks (if any) cannot be found
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
        }
        self.contract_details.append(details)

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        self.search_completed = True

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        pass

def load_all_unique_stocks():
    """Load all unique stocks from universe"""
    try:
        with open('data/universe.json', 'r') as f:
            data = json.load(f)
        
        all_stocks = []
        for screen_name, screen_data in data['screens'].items():
            all_stocks.extend(screen_data['stocks'])
        
        # Remove duplicates based on ISIN or ticker
        seen = set()
        unique_stocks = []
        for stock in all_stocks:
            # Use ISIN as primary identifier, fallback to ticker
            identifier = None
            if stock.get('isin') and stock.get('isin') not in ['null', '', None]:
                identifier = stock['isin']
            elif stock.get('ticker'):
                identifier = stock['ticker']
            
            if identifier and identifier not in seen:
                seen.add(identifier)
                unique_stocks.append(stock)
        
        return unique_stocks
    except Exception as e:
        print(f"Error: {e}")
        return []

def create_contract_from_isin(isin, currency):
    contract = Contract()
    contract.secIdType = "ISIN"
    contract.secId = isin
    contract.secType = "STK"
    contract.currency = currency
    contract.exchange = "SMART"
    return contract

def create_contract_from_ticker(ticker, currency, exchange="SMART"):
    contract = Contract()
    contract.symbol = ticker
    contract.secType = "STK"
    contract.currency = currency
    contract.exchange = exchange
    return contract

def get_best_ticker_variant(ticker):
    """Get the most likely ticker variant to work"""
    if not ticker:
        return None
    
    # Remove exchange suffix (.TO, .L, etc.)
    clean_ticker = re.sub(r'\.[A-Z]+$', '', ticker)
    
    # Handle share class: CCL-A -> CCL.A
    if '-A' in clean_ticker:
        clean_ticker = clean_ticker.replace('-A', '.A')
    
    return clean_ticker

def similarity_score(str1, str2):
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def test_stock(app, stock):
    """Test a single stock, return (found, method, match_score)"""
    
    # METHOD 1: Try ISIN first
    if stock.get('isin') and stock.get('isin') not in ['null', '', None]:
        contract = create_contract_from_isin(stock['isin'], stock['currency'])
        
        app.contract_details = []
        app.search_completed = False
        app.reqContractDetails(app.next_req_id, contract)
        app.next_req_id += 1
        
        # Wait for result
        timeout_start = time.time()
        while not app.search_completed and (time.time() - timeout_start) < 3:
            time.sleep(0.05)
        
        if app.contract_details:
            # Validate match quality
            universe_name = stock['name'].lower()
            universe_currency = stock['currency']
            
            best_score = 0
            for contract in app.contract_details:
                score = 0
                # Name similarity (70%)
                if contract['longName']:
                    name_sim = similarity_score(universe_name, contract['longName'].lower())
                    score += name_sim * 0.7
                # Currency match (30%)
                if contract['currency'] == universe_currency:
                    score += 0.3
                best_score = max(best_score, score)
            
            if best_score > 0.5:  # Good match threshold
                return True, "ISIN", best_score
    
    # METHOD 2: Try ticker fallback
    if stock.get('ticker'):
        clean_ticker = get_best_ticker_variant(stock['ticker'])
        if clean_ticker:
            contract = create_contract_from_ticker(clean_ticker, stock['currency'])
            
            app.contract_details = []
            app.search_completed = False
            app.reqContractDetails(app.next_req_id, contract)
            app.next_req_id += 1
            
            timeout_start = time.time()
            while not app.search_completed and (time.time() - timeout_start) < 3:
                time.sleep(0.05)
            
            if app.contract_details:
                universe_name = stock['name'].lower()
                universe_currency = stock['currency']
                
                best_score = 0
                for contract in app.contract_details:
                    score = 0
                    if contract['longName']:
                        name_sim = similarity_score(universe_name, contract['longName'].lower())
                        score += name_sim * 0.7
                    if contract['currency'] == universe_currency:
                        score += 0.3
                    best_score = max(best_score, score)
                
                if best_score > 0.4:  # Slightly lower threshold for ticker matching
                    return True, "TICKER", best_score
    
    return False, "NONE", 0.0

def run_full_test():
    """Run the full coverage test"""
    universe_stocks = load_all_unique_stocks()
    total_stocks = len(universe_stocks)
    
    print(f"Testing coverage on {total_stocks} unique stocks from universe")
    print("=" * 60)
    
    # Connect to IBKR
    app = IBApi()
    app.connect("127.0.0.1", 4002, clientId=10)
    
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    # Wait for connection
    timeout = 10
    start_time = time.time()
    while not app.connected and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if not app.connected:
        print("Failed to connect to IBKR")
        return
    
    # Test all stocks
    results = {
        'found_isin': [],
        'found_ticker': [], 
        'not_found': []
    }
    
    print(f"Testing stocks... (this may take a while)")
    print(f"Progress: ", end='', flush=True)
    
    for i, stock in enumerate(universe_stocks):
        if i % 50 == 0:
            print(f"{i}", end='.', flush=True)
        
        found, method, score = test_stock(app, stock)
        
        stock_info = {
            'name': stock['name'],
            'ticker': stock.get('ticker', ''),
            'isin': stock.get('isin', ''),
            'currency': stock['currency'],
            'score': score
        }
        
        if found and method == "ISIN":
            results['found_isin'].append(stock_info)
        elif found and method == "TICKER":
            results['found_ticker'].append(stock_info)
        else:
            results['not_found'].append(stock_info)
        
        time.sleep(0.1)  # Brief pause to avoid overwhelming IBKR
    
    app.disconnect()
    
    # Generate comprehensive report
    print(f"\n{total_stocks}")
    print(f"\n{'=' * 60}")
    print(f"FULL COVERAGE TEST RESULTS")
    print(f"{'=' * 60}")
    
    found_isin_count = len(results['found_isin'])
    found_ticker_count = len(results['found_ticker'])
    not_found_count = len(results['not_found'])
    total_found = found_isin_count + found_ticker_count
    
    print(f"Total unique stocks tested: {total_stocks}")
    print(f"Found via ISIN: {found_isin_count} ({found_isin_count/total_stocks:.1%})")
    print(f"Found via ticker fallback: {found_ticker_count} ({found_ticker_count/total_stocks:.1%})")
    print(f"Not found: {not_found_count} ({not_found_count/total_stocks:.1%})")
    print(f"OVERALL COVERAGE: {total_found}/{total_stocks} ({total_found/total_stocks:.1%})")
    
    # Answer the specific question
    if total_found == total_stocks:
        print(f"\n🎯 YES - 100% coverage achieved!")
        print(f"   - {found_isin_count} stocks found via ISIN")
        print(f"   - {found_ticker_count} stocks found via ticker fallback")
    else:
        print(f"\n❌ NO - {not_found_count} stocks cannot be found on IBKR")
    
    # Show breakdown by currency
    currencies = {}
    for category in ['found_isin', 'found_ticker', 'not_found']:
        for stock_info in results[category]:
            curr = stock_info['currency']
            if curr not in currencies:
                currencies[curr] = {'isin': 0, 'ticker': 0, 'not_found': 0}
            
            if category == 'found_isin':
                currencies[curr]['isin'] += 1
            elif category == 'found_ticker':
                currencies[curr]['ticker'] += 1
            else:
                currencies[curr]['not_found'] += 1
    
    print(f"\nBreakdown by currency:")
    for curr in sorted(currencies.keys()):
        stats = currencies[curr]
        total_curr = stats['isin'] + stats['ticker'] + stats['not_found']
        found_curr = stats['isin'] + stats['ticker']
        coverage = found_curr / total_curr if total_curr > 0 else 0
        
        print(f"  {curr}: {found_curr}/{total_curr} ({coverage:.1%}) - ISIN: {stats['isin']}, Ticker: {stats['ticker']}, Missing: {stats['not_found']}")
    
    # Show examples of stocks not found
    if results['not_found']:
        print(f"\nStocks NOT found on IBKR:")
        for i, stock_info in enumerate(results['not_found'][:10]):  # Show first 10
            print(f"  {i+1:2d}. {stock_info['name']} | {stock_info['ticker']} | {stock_info['isin']} | {stock_info['currency']}")
        if len(results['not_found']) > 10:
            print(f"  ... and {len(results['not_found']) - 10} more")
    
    return results

if __name__ == "__main__":
    run_full_test()