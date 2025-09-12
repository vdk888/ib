#!/usr/bin/env python3
"""
Comprehensive coverage analysis to test what percentage of universe stocks
can be found on Interactive Brokers using our hybrid search approach
"""

import json
import re
from difflib import SequenceMatcher
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import threading
import time
import random

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
            "category": contractDetails.category,
            "contract": contract
        }
        self.contract_details.append(details)

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        self.search_completed = True

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158, 2107]:
            pass  # Suppress error output for cleaner analysis

def load_universe_stocks():
    """Load all stocks from universe.json"""
    try:
        with open('data/universe.json', 'r') as f:
            data = json.load(f)
        
        all_stocks = []
        for screen_name, screen_data in data['screens'].items():
            all_stocks.extend(screen_data['stocks'])
        
        # Remove duplicates based on ticker or isin
        seen = set()
        unique_stocks = []
        for stock in all_stocks:
            identifier = stock.get('isin') or stock.get('ticker')
            if identifier and identifier not in seen:
                seen.add(identifier)
                unique_stocks.append(stock)
        
        return unique_stocks
    except Exception as e:
        print(f"Error loading universe data: {e}")
        return []

def create_contract_from_isin(isin, currency="USD"):
    """Create a contract using ISIN"""
    contract = Contract()
    contract.secIdType = "ISIN"
    contract.secId = isin
    contract.secType = "STK"
    contract.currency = currency
    contract.exchange = "SMART"
    return contract

def create_contract_from_ticker(ticker, currency="USD", exchange="SMART"):
    """Create a contract using ticker symbol"""
    contract = Contract()
    contract.symbol = ticker
    contract.secType = "STK"
    contract.currency = currency
    contract.exchange = exchange
    return contract

def get_ticker_variations(ticker):
    """Generate possible ticker variations"""
    variations = [ticker]
    
    # Remove exchange suffix
    base_ticker = re.sub(r'\.[A-Z]+$', '', ticker)
    if base_ticker != ticker:
        variations.append(base_ticker)
    
    # Handle share class indicators
    if '-A' in ticker:
        variations.append(ticker.replace('-A', ''))
        variations.append(ticker.replace('-A', '.A'))
        variations.append(ticker.replace('-A', 'A'))
        no_exchange_base = re.sub(r'\.[A-Z]+$', '', ticker)
        if no_exchange_base != ticker:
            variations.append(no_exchange_base.replace('-A', '.A'))
    
    # Remove duplicates
    seen = set()
    variations = [x for x in variations if not (x in seen or seen.add(x))]
    
    return variations

def similarity_score(str1, str2):
    """Calculate similarity score between two strings"""
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def search_stock(app, stock):
    """Search for a single stock using hybrid approach"""
    found_contracts = []
    
    # Strategy 1: Try ISIN if available
    if stock.get('isin') and stock.get('isin') not in ['null', '', None]:
        contract = create_contract_from_isin(stock['isin'], stock['currency'])
        
        app.contract_details = []
        app.search_completed = False
        app.reqContractDetails(app.next_req_id, contract)
        app.next_req_id += 1
        
        timeout = 3
        start_time = time.time()
        while not app.search_completed and (time.time() - start_time) < timeout:
            time.sleep(0.05)
        
        found_contracts.extend(app.contract_details)
    
    # Strategy 2: Try ticker if ISIN failed or not available
    if not found_contracts and stock.get('ticker'):
        ticker = stock['ticker']
        currency = stock['currency']
        variations = get_ticker_variations(ticker)
        
        # Determine exchanges based on currency/ticker
        exchanges = ['SMART']
        if currency == 'CAD' or '.TO' in ticker:
            exchanges.extend(['TSE'])
        elif currency == 'GBP' or '.L' in ticker:
            exchanges.extend(['LSE'])
        elif currency == 'AUD' or '.AX' in ticker:
            exchanges.extend(['ASX'])
        elif currency == 'JPY' or '.T' in ticker:
            exchanges.extend(['TSE'])
        elif currency == 'USD':
            exchanges.extend(['NASDAQ'])
        
        # Try top variations with relevant exchanges
        for variant in variations[:3]:
            for exchange in exchanges[:2]:  # Limit to 2 exchanges
                contract = create_contract_from_ticker(variant, currency, exchange)
                
                app.contract_details = []
                app.search_completed = False
                app.reqContractDetails(app.next_req_id, contract)
                app.next_req_id += 1
                
                timeout = 2
                start_time = time.time()
                while not app.search_completed and (time.time() - start_time) < timeout:
                    time.sleep(0.05)
                
                found_contracts.extend(app.contract_details)
                time.sleep(0.1)  # Brief pause
                
                if found_contracts:  # Stop if we found something
                    break
            if found_contracts:
                break
    
    # Match results
    if found_contracts:
        best_match = None
        best_score = 0.0
        
        universe_name = stock['name'].lower()
        universe_currency = stock['currency']
        
        for contract in found_contracts:
            score = 0.0
            
            # Name similarity (60%)
            ibkr_name = contract['longName'].lower() if contract['longName'] else ''
            name_sim = similarity_score(universe_name, ibkr_name)
            score += name_sim * 0.6
            
            # Currency match (40%)
            if contract['currency'] == universe_currency:
                score += 0.4
            elif contract['currency'] in ['USD', 'CAD'] and universe_currency in ['USD', 'CAD']:
                score += 0.2
            
            if score > best_score:
                best_score = score
                best_match = contract
        
        return best_match, best_score
    
    return None, 0.0

def analyze_coverage(sample_size=50):
    """Analyze coverage on a sample of stocks"""
    universe_stocks = load_universe_stocks()
    if not universe_stocks:
        print("No stocks found in universe data")
        return
    
    # Take a random sample for analysis
    if len(universe_stocks) > sample_size:
        test_stocks = random.sample(universe_stocks, sample_size)
    else:
        test_stocks = universe_stocks
    
    print(f"Analyzing coverage on {len(test_stocks)} stocks...")
    
    # Initialize API client
    app = IBApi()
    app.connect("127.0.0.1", 4002, clientId=8)
    
    # Start message processing
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    # Wait for connection
    timeout = 10
    start_time = time.time()
    while not app.connected and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if not app.connected:
        print("Failed to connect to IB Gateway")
        return
    
    # Test each stock
    results = {
        'found': [],
        'not_found': [],
        'low_confidence': []
    }
    
    for i, stock in enumerate(test_stocks, 1):
        print(f"Testing {i}/{len(test_stocks)}: {stock['name']} ({stock.get('ticker', 'No ticker')})", end='')
        
        match, score = search_stock(app, stock)
        
        if match and score > 0.5:
            results['found'].append({
                'stock': stock,
                'match': match,
                'score': score
            })
            print(f" FOUND ({score:.1%})")
        elif match and score > 0.3:
            results['low_confidence'].append({
                'stock': stock,
                'match': match,
                'score': score
            })
            print(f" LOW CONF ({score:.1%})")
        else:
            results['not_found'].append(stock)
            print(" NOT FOUND")
        
        time.sleep(0.2)  # Brief pause between searches
    
    app.disconnect()
    
    # Generate report
    total = len(test_stocks)
    found = len(results['found'])
    low_conf = len(results['low_confidence'])
    not_found = len(results['not_found'])
    
    print(f"\n{'='*60}")
    print(f"COVERAGE ANALYSIS RESULTS")
    print(f"{'='*60}")
    print(f"Total stocks tested: {total}")
    print(f"Found (high confidence): {found} ({found/total:.1%})")
    print(f"Found (low confidence): {low_conf} ({low_conf/total:.1%})")
    print(f"Not found: {not_found} ({not_found/total:.1%})")
    print(f"Overall coverage: {(found + low_conf)/total:.1%}")
    
    # Breakdown by currency
    currencies = {}
    for category in ['found', 'low_confidence', 'not_found']:
        for item in results[category]:
            stock = item['stock'] if category != 'not_found' else item
            currency = stock['currency']
            if currency not in currencies:
                currencies[currency] = {'found': 0, 'low_conf': 0, 'not_found': 0, 'total': 0}
            currencies[currency][category.replace('low_confidence', 'low_conf')] += 1
            currencies[currency]['total'] += 1
    
    print(f"\nBreakdown by currency:")
    for currency, stats in sorted(currencies.items()):
        coverage = (stats['found'] + stats['low_conf']) / stats['total']
        print(f"  {currency}: {coverage:.1%} ({stats['found']+stats['low_conf']}/{stats['total']})")
    
    # Show some examples of not found stocks
    if results['not_found']:
        print(f"\nExamples of stocks NOT found:")
        for stock in results['not_found'][:5]:
            print(f"  - {stock['name']} ({stock.get('ticker', 'No ticker')}) [{stock['currency']}]")
    
    return results

if __name__ == "__main__":
    # Start with a sample of 50 stocks
    analyze_coverage(50)