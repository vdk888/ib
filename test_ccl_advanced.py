#!/usr/bin/env python3
"""
Advanced test script for CCL Industries with name-based search and broader parameters
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

def similarity_score(str1, str2):
    """Calculate similarity score between two strings"""
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def search_comprehensive(app, stock):
    """Comprehensive search using multiple strategies"""
    ticker = stock['ticker']
    currency = stock['currency']
    all_contracts = []
    
    # Strategy 1: Try ticker variations with different formats
    ticker_variations = [
        ticker,                           # CCL-A.TO
        ticker.replace('-A', 'A'),        # CCLA.TO
        ticker.replace('-A', ''),         # CCL.TO  
        ticker.replace('.TO', ''),        # CCL-A
        ticker.replace('-A.TO', ''),      # CCL
        ticker.replace('-A', 'A').replace('.TO', ''),  # CCLA
    ]
    
    # Remove duplicates while preserving order
    seen = set()
    ticker_variations = [x for x in ticker_variations if not (x in seen or seen.add(x))]
    
    print(f"Ticker variations to try: {ticker_variations}")
    
    # Try different exchanges
    exchanges = ['SMART', 'TSE', 'VENTURE', 'NASDAQ', 'NYSE']
    
    for variant in ticker_variations:
        for exchange in exchanges:
            print(f"  Trying: {variant} on {exchange} ({currency})")
            contract = create_contract_from_ticker(variant, currency, exchange)
            
            app.contract_details = []
            app.search_completed = False
            app.reqContractDetails(app.next_req_id, contract)
            app.next_req_id += 1
            
            # Wait for search to complete
            timeout = 2
            start_time = time.time()
            while not app.search_completed and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            all_contracts.extend(app.contract_details)
            time.sleep(0.3)  # Brief pause between requests
            
            if len(all_contracts) >= 15:  # Limit to prevent too many results
                print(f"  Stopping search - found {len(all_contracts)} contracts")
                break
        if len(all_contracts) >= 15:
            break
    
    # Strategy 2: Try with USD currency as well (dual-listed stocks)
    if currency != 'USD' and len(all_contracts) < 5:
        print(f"\nTrying USD variants as well...")
        for variant in ticker_variations[:3]:  # Try top 3 variants only
            for exchange in ['SMART', 'NASDAQ', 'NYSE']:
                print(f"  Trying: {variant} on {exchange} (USD)")
                contract = create_contract_from_ticker(variant, 'USD', exchange)
                
                app.contract_details = []
                app.search_completed = False
                app.reqContractDetails(app.next_req_id, contract)
                app.next_req_id += 1
                
                timeout = 2
                start_time = time.time()
                while not app.search_completed and (time.time() - start_time) < timeout:
                    time.sleep(0.1)
                
                all_contracts.extend(app.contract_details)
                time.sleep(0.3)
                
                if len(all_contracts) >= 10:
                    break
            if len(all_contracts) >= 10:
                break
    
    return all_contracts

def match_contracts(universe_stock, contracts):
    """Match IBKR contracts with universe stock data with improved scoring"""
    if not contracts:
        return None, 0.0
    
    universe_name = universe_stock['name'].lower()
    universe_currency = universe_stock['currency']
    universe_country = universe_stock.get('country', '').lower()
    
    print(f"\n  Matching against: {universe_stock['name']} ({universe_currency})")
    
    scored_matches = []
    
    for contract in contracts:
        score = 0.0
        reasons = []
        
        # Name similarity (most important - 50% weight)
        ibkr_name = contract['longName'].lower() if contract['longName'] else ''
        name_sim = similarity_score(universe_name, ibkr_name)
        score += name_sim * 0.5
        if name_sim > 0.1:
            reasons.append(f"name_sim:{name_sim:.2f}")
        
        # Currency match (25% weight)
        if contract['currency'] == universe_currency:
            score += 0.25
            reasons.append("currency_match")
        elif contract['currency'] in ['USD', 'CAD'] and universe_currency in ['USD', 'CAD']:
            score += 0.15  # Partial credit for USD/CAD cross-listing
            reasons.append("currency_related")
        
        # Industry match (15% weight) - check if industries are similar
        universe_sector = universe_stock.get('sector', '').lower()
        ibkr_industry = contract.get('industry', '').lower()
        if universe_sector and ibkr_industry:
            industry_sim = similarity_score(universe_sector, ibkr_industry)
            if industry_sim > 0.3:
                score += industry_sim * 0.15
                reasons.append(f"industry_sim:{industry_sim:.2f}")
        
        # Exchange/Country correlation (10% weight)
        exchange_country_map = {
            'TSE': 'canada', 'VENTURE': 'canada',
            'NASDAQ': 'united states', 'NYSE': 'united states',
            'LSE': 'united kingdom', 'LSEETF': 'united kingdom',
            'ASX': 'australia',
            'TSEJ': 'japan',
            'SBF': 'france', 'SBFM': 'france',
            'XETRA': 'germany', 'DTB': 'germany',
        }
        
        exchange_country = exchange_country_map.get(contract['exchange'], '').lower()
        if exchange_country and exchange_country in universe_country:
            score += 0.1
            reasons.append("country_match")
        
        scored_matches.append((contract, score, reasons))
    
    # Sort by score descending
    scored_matches.sort(key=lambda x: x[1], reverse=True)
    
    # Print all matches with scores
    for i, (contract, score, reasons) in enumerate(scored_matches):
        print(f"    {i+1}. {contract['symbol']} ({contract['exchange']}): score={score:.3f}")
        print(f"       Name: {contract['longName']}")
        print(f"       Currency: {contract['currency']}, Industry: {contract.get('industry', 'N/A')}")
        print(f"       Reasons: [{', '.join(reasons)}]")
        print()
    
    if scored_matches:
        best_match, best_score, best_reasons = scored_matches[0]
        return best_match, best_score
    
    return None, 0.0

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
    }
    
    # Initialize API client
    app = IBApi()
    
    # Connect to IB Gateway (paper trading port 4002)
    print("Connecting to IB Gateway...")
    app.connect("127.0.0.1", 4002, clientId=7)
    
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
    print(f"ADVANCED SEARCH: {test_stock['name']}")
    print(f"Ticker: {test_stock['ticker']}")
    print(f"Currency: {test_stock['currency']}")
    print(f"Country: {test_stock['country']}")
    print(f"Sector: {test_stock['sector']}")
    print("="*80)
    
    # Comprehensive search
    found_contracts = search_comprehensive(app, test_stock)
    
    # Match and rank results
    if found_contracts:
        print(f"\nFound {len(found_contracts)} total contracts")
        best_match, best_score = match_contracts(test_stock, found_contracts)
        
        if best_match:
            print(f"\nBEST MATCH (confidence: {best_score:.1%}):")
            print(f"  IBKR Symbol: {best_match['symbol']}")
            print(f"  Exchange: {best_match['exchange']}")
            print(f"  Currency: {best_match['currency']}")
            print(f"  Long Name: {best_match['longName']}")
            print(f"  Industry: {best_match['industry']}")
            print(f"  Category: {best_match['category']}")
            
            if best_score > 0.3:
                print(f"\n✅ CONFIDENT MATCH FOUND!")
            else:
                print(f"\n⚠️  LOW CONFIDENCE - Manual verification recommended")
        else:
            print(f"\nNo matches found")
    else:
        print("\nNo contracts found with any search strategy")
    
    # Disconnect
    app.disconnect()

if __name__ == "__main__":
    main()