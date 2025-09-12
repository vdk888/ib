#!/usr/bin/env python3
"""
Test script specifically for CCL Industries stock search
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
            "reqId": reqId,
            "symbol": contract.symbol,
            "secType": contract.secType,
            "exchange": contract.exchange,
            "currency": contract.currency,
            "localSymbol": contract.localSymbol,
            "tradingClass": contract.tradingClass,
            "marketName": contractDetails.marketName,
            "minTick": contractDetails.minTick,
            "longName": contractDetails.longName,
            "industry": contractDetails.industry,
            "category": contractDetails.category,
            "contract": contract
        }
        self.contract_details.append(details)
        print(f"  Found: {contract.symbol} ({contract.localSymbol}) on {contract.exchange}")
        print(f"    Name: {contractDetails.longName}")
        print(f"    Currency: {contract.currency}")
        print(f"    Industry: {contractDetails.industry}")

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        self.search_completed = True
        print(f"  Search completed for reqId: {reqId}")

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158, 2107]:  # Ignore common info messages
            print(f'  Error {errorCode}: {errorString}')

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
    
    # Remove exchange suffix if present (.TO, .AX, .L, etc.)
    base_ticker = re.sub(r'\.[A-Z]+$', '', ticker)
    if base_ticker != ticker:
        variations.append(base_ticker)
    
    # Handle specific patterns
    if '-A' in ticker:
        # Remove -A suffix (class A shares)
        no_class = ticker.replace('-A', '')
        variations.append(no_class)
        # Also try base without exchange suffix
        no_class_base = re.sub(r'\.[A-Z]+$', '', no_class)
        if no_class_base not in variations:
            variations.append(no_class_base)
    
    # Add common exchange mappings
    exchange_mappings = {
        '.TO': ['TSE', 'VENTURE'],  # Toronto Stock Exchange
        '.AX': ['ASX'],             # Australian Securities Exchange
        '.L': ['LSE', 'LSEETF'],    # London Stock Exchange
        '.PA': ['SBF'],             # Euronext Paris
        '.DE': ['XETRA', 'DTB'],    # Frankfurt
        '.CO': ['CSE']              # Copenhagen
    }
    
    return variations

def similarity_score(str1, str2):
    """Calculate similarity score between two strings"""
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def match_contracts(universe_stock, contracts):
    """Match IBKR contracts with universe stock data"""
    if not contracts:
        return None, 0.0
    
    best_match = None
    best_score = 0.0
    
    universe_name = universe_stock['name'].lower()
    universe_currency = universe_stock['currency']
    universe_country = universe_stock.get('country', '').lower()
    
    print(f"\n  Matching against: {universe_stock['name']} ({universe_currency})")
    
    for contract in contracts:
        score = 0.0
        reasons = []
        
        # Name similarity (most important - 60% weight)
        ibkr_name = contract['longName'].lower() if contract['longName'] else ''
        name_sim = similarity_score(universe_name, ibkr_name)
        score += name_sim * 0.6
        if name_sim > 0.1:
            reasons.append(f"name_sim:{name_sim:.2f}")
        
        # Currency match (30% weight)
        if contract['currency'] == universe_currency:
            score += 0.3
            reasons.append("currency_match")
        elif contract['currency'] in ['USD', 'CAD'] and universe_currency in ['USD', 'CAD']:
            # Partial credit for USD/CAD cross-listing
            score += 0.15
            reasons.append("currency_similar")
        
        # Exchange/Country correlation (10% weight)
        exchange_country_map = {
            'TSE': 'canada', 'VENTURE': 'canada',
            'NASDAQ': 'united states', 'NYSE': 'united states',
            'LSE': 'united kingdom', 'LSEETF': 'united kingdom',
            'ASX': 'australia',
            'TSEJ': 'japan', 'TSE': 'japan',
            'SBF': 'france', 'SBFM': 'france',
            'XETRA': 'germany', 'DTB': 'germany',
            'CSE': 'denmark'
        }
        
        exchange_country = exchange_country_map.get(contract['exchange'], '').lower()
        if exchange_country and exchange_country in universe_country:
            score += 0.1
            reasons.append("country_match")
        
        print(f"    {contract['symbol']} ({contract['exchange']}): score={score:.3f} [{', '.join(reasons)}]")
        print(f"      Industry: {contract['industry']}, Category: {contract['category']}")
        
        if score > best_score:
            best_score = score
            best_match = contract
    
    return best_match, best_score

def search_stock_by_ticker(app, stock):
    """Search for stock using ticker variations"""
    ticker = stock['ticker']
    currency = stock['currency']
    variations = get_ticker_variations(ticker)
    
    print(f"\nSearching by ticker variations: {variations}")
    
    all_contracts = []
    
    # Try different exchanges for Canadian stocks
    exchanges = ['SMART', 'TSE', 'VENTURE'] if currency == 'CAD' else ['SMART']
    
    for variant in variations:
        for exchange in exchanges:
            print(f"  Trying ticker: {variant} on {exchange}")
            contract = create_contract_from_ticker(variant, currency, exchange)
            
            app.contract_details = []
            app.search_completed = False
            app.reqContractDetails(app.next_req_id, contract)
            app.next_req_id += 1
            
            # Wait for search to complete
            timeout = 3
            start_time = time.time()
            while not app.search_completed and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            all_contracts.extend(app.contract_details)
            time.sleep(0.5)  # Brief pause between requests
            
            if len(all_contracts) >= 10:  # Limit results
                break
        if len(all_contracts) >= 10:
            break
    
    return all_contracts

def main():
    # CCL Industries test stock
    test_stock = {
        "ticker": "CCL-A.TO",
        "isin": None,
        "name": "CCL Industries Inc.",
        "currency": "CAD",
        "sector": "Industrials",
        "country": "Canada",
        "price": 77.35,
        "price_180d_change": "-0.90%",
    }
    
    # Initialize API client
    app = IBApi()
    
    # Connect to IB Gateway (paper trading port 4002)
    print("Connecting to IB Gateway...")
    app.connect("127.0.0.1", 4002, clientId=6)
    
    # Start message processing in separate thread
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
    
    print(f"\n{'='*80}")
    print(f"TESTING: {test_stock['name']}")
    print(f"Ticker: {test_stock['ticker']}")
    print(f"ISIN: {test_stock.get('isin', 'None')}")
    print(f"Currency: {test_stock['currency']}")
    print(f"Country: {test_stock['country']}")
    print(f"Sector: {test_stock['sector']}")
    print("="*80)
    
    # Search by ticker since no ISIN
    found_contracts = search_stock_by_ticker(app, test_stock)
    
    # Match and rank results
    if found_contracts:
        print(f"\nFound {len(found_contracts)} potential matches:")
        best_match, best_score = match_contracts(test_stock, found_contracts)
        
        if best_match and best_score > 0.3:  # Minimum confidence threshold
            print(f"\nBEST MATCH (confidence: {best_score:.1%}):")
            print(f"  IBKR Symbol: {best_match['symbol']}")
            print(f"  Exchange: {best_match['exchange']}")
            print(f"  Currency: {best_match['currency']}")
            print(f"  Long Name: {best_match['longName']}")
            print(f"  Industry: {best_match['industry']}")
            print(f"  Category: {best_match['category']}")
            
            print(f"\nALL MATCHES:")
            for i, contract in enumerate(found_contracts, 1):
                name_sim = similarity_score(test_stock['name'].lower(), contract['longName'].lower() if contract['longName'] else '')
                print(f"  {i}. {contract['symbol']} ({contract['exchange']}) - {contract['longName']}")
                print(f"     Currency: {contract['currency']}, Name similarity: {name_sim:.2f}")
        else:
            print(f"\nNo confident match found (best score: {best_score:.1%})")
            print("\nAll found contracts:")
            for contract in found_contracts:
                print(f"  {contract['symbol']} ({contract['exchange']}) - {contract['longName']}")
    else:
        print("\nNo contracts found")
    
    # Disconnect
    app.disconnect()

if __name__ == "__main__":
    main()