#!/usr/bin/env python3
"""
Enhanced search test with better ticker variations and name-based fallback search
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
            "longName": contractDetails.longName,
            "currency": contract.currency,
            "exchange": contract.exchange,
            "country": contractDetails.country if hasattr(contractDetails, 'country') else '',
            "contract": contract
        }
        self.contract_details.append(details)

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        self.search_completed = True

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        pass

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

def get_enhanced_ticker_variations(ticker):
    """Enhanced ticker variations including the cases mentioned"""
    variations = [ticker]
    
    # Basic cleanup - remove exchange suffix
    base_ticker = re.sub(r'\.[A-Z]+$', '', ticker)
    if base_ticker != ticker:
        variations.append(base_ticker)
    
    # Handle share class variations
    if '-A' in ticker:
        # ROCK-A.CO -> ROCKA (remove dash and exchange)
        no_dash_no_exchange = re.sub(r'\.[A-Z]+$', '', ticker.replace('-A', 'A'))
        variations.append(no_dash_no_exchange)  # ROCKA
        
        # Also try dot notation: ROCK-A -> ROCK.A
        dot_class = ticker.replace('-A', '.A')
        variations.append(dot_class)
        base_dot = re.sub(r'\.[A-Z]+$', '', dot_class)
        variations.append(base_dot)
        
    if '-B' in ticker:
        # NEWA-B.ST -> NEWA.B (convert dash to dot, remove exchange)
        base_dot = re.sub(r'\.[A-Z]+$', '', ticker.replace('-B', '.B'))
        variations.append(base_dot)  # NEWA.B
        
        # Also try without dash: NEWA-B -> NEWAB
        no_dash_no_exchange = re.sub(r'\.[A-Z]+$', '', ticker.replace('-B', 'B'))
        variations.append(no_dash_no_exchange)
    
    # Remove duplicates while preserving order
    seen = set()
    variations = [x for x in variations if not (x in seen or seen.add(x))]
    
    return variations

def similarity_score(str1, str2):
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def search_by_name_fragment(app, stock):
    """Search using company name fragments for cases like Everplay Group"""
    name = stock['name']
    
    # Try searching with first word of company name
    words = name.split()
    search_terms = []
    
    # Add first word
    if words:
        search_terms.append(words[0])
    
    # Add first two words if available
    if len(words) >= 2:
        search_terms.append(f"{words[0]} {words[1]}")
    
    # Special cases
    if "everplay" in name.lower():
        search_terms.append("EVPL")
    
    all_contracts = []
    
    for term in search_terms:
        if len(term) < 2:
            continue
            
        print(f"    Searching by name: '{term}'")
        
        # Use reqMatchingSymbols for name-based search
        app.contract_details = []
        app.search_completed = False
        
        try:
            app.reqMatchingSymbols(app.next_req_id, term)
            app.next_req_id += 1
            
            timeout_start = time.time()
            while not app.search_completed and (time.time() - timeout_start) < 3:
                time.sleep(0.05)
            
            all_contracts.extend(app.contract_details)
            time.sleep(0.2)
            
        except Exception as e:
            print(f"    Name search failed: {e}")
    
    return all_contracts

def enhanced_stock_search(app, stock):
    """Enhanced search with better ticker variations and name fallback"""
    print(f"Searching: {stock['name']} ({stock.get('ticker', 'N/A')})")
    
    found_contracts = []
    
    # Step 1: Try ISIN first
    if stock.get('isin') and stock.get('isin') not in ['null', '', None]:
        print(f"  Trying ISIN: {stock['isin']}")
        contract = create_contract_from_isin(stock['isin'], stock['currency'])
        
        app.contract_details = []
        app.search_completed = False
        app.reqContractDetails(app.next_req_id, contract)
        app.next_req_id += 1
        
        timeout_start = time.time()
        while not app.search_completed and (time.time() - timeout_start) < 3:
            time.sleep(0.05)
        
        found_contracts.extend(app.contract_details)
        print(f"  ISIN search found {len(app.contract_details)} results")
    
    # Step 2: Try enhanced ticker variations
    if not found_contracts and stock.get('ticker'):
        ticker = stock['ticker']
        currency = stock['currency']
        variations = get_enhanced_ticker_variations(ticker)
        print(f"  Trying ticker variations: {variations}")
        
        # Use only SMART exchange for paper trading (specific exchanges don't work)
        exchanges = ['SMART']
        
        for variant in variations[:6]:  # Try top variations
            for exchange in exchanges[:2]:
                print(f"    Trying: {variant} on {exchange}")
                contract = create_contract_from_ticker(variant, currency, exchange)
                
                app.contract_details = []
                app.search_completed = False
                app.reqContractDetails(app.next_req_id, contract)
                app.next_req_id += 1
                
                timeout_start = time.time()
                while not app.search_completed and (time.time() - timeout_start) < 2:
                    time.sleep(0.05)
                
                found_contracts.extend(app.contract_details)
                time.sleep(0.1)
                
                if found_contracts:
                    print(f"    Found {len(app.contract_details)} contracts with {variant}")
                    break
            if found_contracts:
                break
    
    # Step 3: Try name-based search as final fallback
    if not found_contracts:
        print(f"  Trying name-based search...")
        name_contracts = search_by_name_fragment(app, stock)
        found_contracts.extend(name_contracts)
        print(f"  Name search found {len(name_contracts)} results")
    
    # Match and score results
    if found_contracts:
        best_match = None
        best_score = 0.0
        
        universe_name = stock['name'].lower()
        universe_currency = stock['currency']
        universe_country = stock.get('country', '').lower()
        
        for contract in found_contracts:
            score = 0.0
            
            # Name similarity (60%)
            if contract['longName']:
                name_sim = similarity_score(universe_name, contract['longName'].lower())
                score += name_sim * 0.6
            
            # Currency match (30%)
            if contract['currency'] == universe_currency:
                score += 0.3
            
            # Country match (10%)
            if contract.get('country') and universe_country:
                if contract['country'].lower() == universe_country:
                    score += 0.1
            
            if score > best_score:
                best_score = score
                best_match = contract
                
        return best_match, best_score
    
    return None, 0.0

def test_failing_stocks():
    """Test the specific failing stocks with enhanced search"""
    failing_stocks = [
        {"name": "ROCKWOOL International A/S", "ticker": "ROCK-A.CO", "isin": "DK0010219070", "currency": "DKK", "country": "Denmark"},
        {"name": "Everplay Group PLC", "ticker": "EVPL.L", "isin": "null", "currency": "GBP", "country": "United Kingdom"},
        {"name": "New Wave Group AB (publ)", "ticker": "NEWA-B.ST", "isin": "SE0000426546", "currency": "SEK", "country": "Sweden"},
        {"name": "Gr. Sarantis S.A.", "ticker": "SAR.AT", "isin": "GRS204003008", "currency": "EUR", "country": "Greece"},
        {"name": "ROCKWOOL International A/S", "ticker": "ROCK-B.CO", "isin": "DK0010219153", "currency": "DKK", "country": "Denmark"},
        {"name": "Dewhurst plc", "ticker": "DWHT.L", "isin": "GB0002675048", "currency": "GBP", "country": "United Kingdom"},
        {"name": "Ilyda SA", "ticker": "ILYDA.AT", "isin": "GRS475003018", "currency": "EUR", "country": "Greece"},
        {"name": "Thessaloniki Port Authority SA", "ticker": "OLTH.AT", "isin": "GRS427003009", "currency": "EUR", "country": "Greece"},
        {"name": "Admicom Oyj", "ticker": "ADMCM.HE", "isin": "FI4000251830", "currency": "EUR", "country": "Finland"},
        {"name": "Profile Systems & Software SA", "ticker": "PROF.AT", "isin": "GRS472003011", "currency": "EUR", "country": "Greece"},
        {"name": "Flexopack Societe Anonyme Commercial and Industrial Plastics Company", "ticker": "FLEXO.AT", "isin": "GRS259003002", "currency": "EUR", "country": "Greece"}
    ]
    
    # Connect to IBKR
    app = IBApi()
    app.connect("127.0.0.1", 4002, clientId=12)
    
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    timeout = 10
    start_time = time.time()
    while not app.connected and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if not app.connected:
        print("Failed to connect")
        return
    
    results = {
        'found': [],
        'still_missing': []
    }
    
    for stock in failing_stocks:
        print(f"\n{'='*80}")
        print(f"Testing: {stock['name']}")
        print(f"{'='*80}")
        
        match, score = enhanced_stock_search(app, stock)
        
        if match and score > 0.4:  # Lower threshold for these edge cases
            print(f"\nFOUND! Score: {score:.1%}")
            print(f"  IBKR Symbol: {match['symbol']}")
            print(f"  IBKR Name: {match['longName']}")
            print(f"  Exchange: {match['exchange']}")
            print(f"  Currency: {match['currency']}")
            results['found'].append({
                'stock': stock,
                'match': match,
                'score': score
            })
        else:
            print(f"\nSTILL NOT FOUND (score: {score:.1%})")
            results['still_missing'].append(stock)
        
        time.sleep(0.5)
    
    app.disconnect()
    
    # Summary
    print(f"\n{'='*80}")
    print(f"ENHANCED SEARCH RESULTS")
    print(f"{'='*80}")
    print(f"Originally failing: {len(failing_stocks)}")
    print(f"Now found: {len(results['found'])}")
    print(f"Still missing: {len(results['still_missing'])}")
    
    if results['found']:
        print(f"\nNEWLY FOUND:")
        for item in results['found']:
            stock = item['stock']
            match = item['match']
            print(f"  {stock['name']} -> {match['symbol']} (score: {item['score']:.1%})")
    
    if results['still_missing']:
        print(f"\nSTILL MISSING:")
        for stock in results['still_missing']:
            print(f"  {stock['name']} ({stock['ticker']})")

if __name__ == "__main__":
    test_failing_stocks()