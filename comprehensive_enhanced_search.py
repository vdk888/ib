#!/usr/bin/env python3
"""
Comprehensive enhanced search with multiple strategies to find all available stocks
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
        self.matching_symbols = []
        self.next_req_id = 1
        self.search_completed = False
        self.symbol_search_completed = False

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
            "contract": contract
        }
        self.contract_details.append(details)

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        self.search_completed = True

    def symbolSamples(self, reqId, contractDescriptions):
        super().symbolSamples(reqId, contractDescriptions)
        self.matching_symbols = []
        for desc in contractDescriptions:
            contract = desc.contract
            details = {
                "symbol": contract.symbol,
                "secType": contract.secType,
                "currency": contract.currency,
                "exchange": contract.exchange,
                "description": desc.derivativeSecTypes if hasattr(desc, 'derivativeSecTypes') else ''
            }
            if contract.secType == "STK":  # Only stocks
                self.matching_symbols.append(details)

    def symbolSamplesEnd(self, reqId):
        super().symbolSamplesEnd(reqId)
        self.symbol_search_completed = True

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        pass

def create_contract_from_ticker(ticker, currency, exchange="SMART"):
    contract = Contract()
    contract.symbol = ticker
    contract.secType = "STK"
    contract.currency = currency
    contract.exchange = exchange
    return contract

def create_contract_from_isin(isin, currency):
    contract = Contract()
    contract.secIdType = "ISIN"
    contract.secId = isin
    contract.secType = "STK"
    contract.currency = currency
    contract.exchange = "SMART"
    return contract

def get_all_ticker_variations(ticker):
    """Generate comprehensive ticker variations"""
    variations = [ticker]
    
    # Remove exchange suffix
    base_ticker = re.sub(r'\.[A-Z]+$', '', ticker)
    if base_ticker != ticker:
        variations.append(base_ticker)
    
    # Share class variations
    if '-A' in ticker:
        # ROCK-A.CO -> ROCKA, ROCK.A
        no_dash = ticker.replace('-A', 'A')
        variations.append(no_dash)
        variations.append(re.sub(r'\.[A-Z]+$', '', no_dash))
        
        dot_class = ticker.replace('-A', '.A')
        variations.append(dot_class)
        variations.append(re.sub(r'\.[A-Z]+$', '', dot_class))
        
    if '-B' in ticker:
        # NEWA-B.ST -> NEWA.B, NEWAB
        dot_class = ticker.replace('-B', '.B')
        variations.append(dot_class)
        variations.append(re.sub(r'\.[A-Z]+$', '', dot_class))
        
        no_dash = ticker.replace('-B', 'B')
        variations.append(no_dash)
        variations.append(re.sub(r'\.[A-Z]+$', '', no_dash))
    
    # Greek stocks - try without .AT suffix and with different formats
    if '.AT' in ticker:
        base = ticker.replace('.AT', '')
        variations.append(base)
        # Try common Greek stock formats
        if len(base) <= 6:
            variations.append(base + 'A')  # Some Greek stocks have A suffix
    
    # London stocks - try different formats
    if '.L' in ticker:
        base = ticker.replace('.L', '')
        variations.append(base)
    
    # Remove duplicates
    seen = set()
    variations = [x for x in variations if not (x in seen or seen.add(x))]
    
    return variations

def similarity_score(str1, str2):
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def is_valid_match(universe_stock, ibkr_contract):
    """Strict validation to prevent false positives"""
    universe_name = universe_stock['name'].lower()
    ibkr_name = ibkr_contract['longName'].lower()
    
    # Extract key company identifiers
    universe_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', universe_name))
    ibkr_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', ibkr_name))
    
    # Remove common corporate suffixes that don't help with matching
    ignore_words = {
        'ltd', 'plc', 'inc', 'corp', 'sa', 'ab', 'oyj', 'group', 'international', 
        'company', 'limited', 'corporation', 'societe', 'anonyme', 'systems',
        'software', 'commercial', 'industrial', 'authority', 'public'
    }
    
    universe_key_words = universe_words - ignore_words
    ibkr_key_words = ibkr_words - ignore_words
    
    # Must have currency match
    if ibkr_contract['currency'] != universe_stock['currency']:
        return False, "Currency mismatch"
    
    # Must have significant word overlap OR very high name similarity
    word_overlap = len(universe_key_words & ibkr_key_words)
    name_similarity = similarity_score(universe_name, ibkr_name)
    
    # Strict requirements:
    if name_similarity > 0.8:  # Very high similarity is OK
        return True, f"High similarity: {name_similarity:.2f}"
    elif word_overlap >= 2 and name_similarity > 0.6:  # Good overlap + decent similarity
        return True, f"Word overlap: {word_overlap}, similarity: {name_similarity:.2f}"
    elif word_overlap >= 1 and name_similarity > 0.7:  # Some overlap + high similarity
        return True, f"Some overlap + high similarity: {word_overlap}, {name_similarity:.2f}"
    else:
        return False, f"Insufficient match: overlap={word_overlap}, similarity={name_similarity:.2f}"

def search_by_name_matching(app, stock):
    """Use reqMatchingSymbols to search by company name parts"""
    name = stock['name'].lower()
    search_terms = []
    
    # Extract meaningful words from company name
    words = re.findall(r'\b[a-zA-Z]{3,}\b', stock['name'])  # Words with 3+ letters
    
    # Add individual words
    for word in words[:3]:  # Try first 3 meaningful words
        if word.lower() not in ['ltd', 'plc', 'inc', 'corp', 'sa', 'ab', 'oyj', 'group', 'international']:
            search_terms.append(word)
    
    # Add combinations
    if len(words) >= 2:
        search_terms.append(f"{words[0]} {words[1]}")
    
    # Special cases based on known mappings
    if 'everplay' in name:
        search_terms.extend(['everplay', 'EVPL'])
    if 'sarantis' in name:
        search_terms.extend(['sarantis', 'SAR'])
    if 'dewhurst' in name:
        search_terms.extend(['dewhurst', 'DWHT'])
    if 'ilyda' in name:
        search_terms.extend(['ilyda'])
    if 'thessaloniki' in name or 'port' in name:
        search_terms.extend(['thessaloniki', 'port', 'OLTH'])
    
    all_matches = []
    
    for term in search_terms:
        if len(term) < 2:
            continue
            
        print(f"    Searching name: '{term}'")
        
        try:
            app.matching_symbols = []
            app.symbol_search_completed = False
            app.reqMatchingSymbols(app.next_req_id, term)
            app.next_req_id += 1
            
            timeout_start = time.time()
            while not app.symbol_search_completed and (time.time() - timeout_start) < 5:
                time.sleep(0.05)
            
            # Convert matching symbols to contract details
            for match in app.matching_symbols:
                if match['currency'] == stock['currency']:  # Currency filter
                    # Get full contract details
                    contract = create_contract_from_ticker(match['symbol'], match['currency'], match['exchange'])
                    
                    app.contract_details = []
                    app.search_completed = False
                    app.reqContractDetails(app.next_req_id, contract)
                    app.next_req_id += 1
                    
                    timeout_start = time.time()
                    while not app.search_completed and (time.time() - timeout_start) < 3:
                        time.sleep(0.05)
                    
                    all_matches.extend(app.contract_details)
                    time.sleep(0.1)
            
            time.sleep(0.2)
            
        except Exception as e:
            print(f"    Name search error: {e}")
    
    return all_matches

def comprehensive_stock_search(app, stock):
    """Comprehensive search using multiple strategies"""
    print(f"Searching: {stock['name']} ({stock.get('ticker', 'N/A')})")
    
    all_contracts = []
    
    # Strategy 1: ISIN search
    if stock.get('isin') and stock.get('isin') not in ['null', '', None]:
        print(f"  Strategy 1 - ISIN: {stock['isin']}")
        contract = create_contract_from_isin(stock['isin'], stock['currency'])
        
        app.contract_details = []
        app.search_completed = False
        app.reqContractDetails(app.next_req_id, contract)
        app.next_req_id += 1
        
        timeout_start = time.time()
        while not app.search_completed and (time.time() - timeout_start) < 5:
            time.sleep(0.05)
        
        all_contracts.extend(app.contract_details)
        print(f"    ISIN found: {len(app.contract_details)} results")
    
    # Strategy 2: Ticker variations on SMART exchange
    if stock.get('ticker'):
        print(f"  Strategy 2 - Ticker variations")
        ticker = stock['ticker']
        currency = stock['currency']
        variations = get_all_ticker_variations(ticker)
        print(f"    Variations: {variations}")
        
        for variant in variations:
            print(f"    Trying: {variant} ({currency})")
            contract = create_contract_from_ticker(variant, currency, "SMART")
            
            app.contract_details = []
            app.search_completed = False
            app.reqContractDetails(app.next_req_id, contract)
            app.next_req_id += 1
            
            timeout_start = time.time()
            while not app.search_completed and (time.time() - timeout_start) < 3:
                time.sleep(0.05)
            
            if app.contract_details:
                all_contracts.extend(app.contract_details)
                print(f"      FOUND with {variant}!")
                break  # Found it, move on
            
            time.sleep(0.1)
    
    # Strategy 3: Name-based symbol matching
    if not all_contracts:
        print(f"  Strategy 3 - Name-based search")
        name_matches = search_by_name_matching(app, stock)
        all_contracts.extend(name_matches)
        print(f"    Name search found: {len(name_matches)} results")
    
    # Match and score results with strict validation
    if all_contracts:
        valid_matches = []
        
        print(f"  Evaluating {len(all_contracts)} potential matches with strict validation...")
        
        for contract in all_contracts:
            is_valid, reason = is_valid_match(stock, contract)
            
            if is_valid:
                name_sim = similarity_score(stock['name'].lower(), contract['longName'].lower())
                print(f"    VALID: {contract['symbol']}: {contract['longName'][:40]} -> {reason}")
                valid_matches.append((contract, name_sim))
            else:
                print(f"    REJECTED: {contract['symbol']}: {contract['longName'][:40]} -> {reason}")
        
        if valid_matches:
            # Sort by name similarity and pick the best
            valid_matches.sort(key=lambda x: x[1], reverse=True)
            best_match = valid_matches[0][0]
            best_score = valid_matches[0][1]
        else:
            best_match = None
            best_score = 0.0
        
        return best_match, best_score
    
    return None, 0.0

def test_comprehensive_search():
    """Test comprehensive search on all failing stocks"""
    
    failing_stocks = [
        {"name": "ROCKWOOL International A/S", "ticker": "ROCK-A.CO", "isin": "DK0010219070", "currency": "DKK", "country": "Denmark"},
        {"name": "Thessaloniki Port Authority SA", "ticker": "OLTH.AT", "isin": "GRS427003009", "currency": "EUR", "country": "Greece"},
        {"name": "Admicom Oyj", "ticker": "ADMCM.HE", "isin": "FI4000251830", "currency": "EUR", "country": "Finland"},
        {"name": "Everplay Group PLC", "ticker": "EVPL.L", "isin": "null", "currency": "GBP", "country": "United Kingdom"},
        {"name": "New Wave Group AB (publ)", "ticker": "NEWA-B.ST", "isin": "SE0000426546", "currency": "SEK", "country": "Sweden"},
        {"name": "Gr. Sarantis S.A.", "ticker": "SAR.AT", "isin": "GRS204003008", "currency": "EUR", "country": "Greece"},
        {"name": "ROCKWOOL International A/S", "ticker": "ROCK-B.CO", "isin": "DK0010219153", "currency": "DKK", "country": "Denmark"},
        {"name": "Profile Systems & Software SA", "ticker": "PROF.AT", "isin": "GRS472003011", "currency": "EUR", "country": "Greece"},
        {"name": "Flexopack Societe Anonyme Commercial and Industrial Plastics Company", "ticker": "FLEXO.AT", "isin": "GRS259003002", "currency": "EUR", "country": "Greece"},
        {"name": "Dewhurst plc", "ticker": "DWHT.L", "isin": "GB0002675048", "currency": "GBP", "country": "United Kingdom"},
        {"name": "Ilyda SA", "ticker": "ILYDA.AT", "isin": "GRS475003018", "currency": "EUR", "country": "Greece"}
    ]
    
    # Connect to IBKR
    app = IBApi()
    app.connect("127.0.0.1", 4002, clientId=15)
    
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
    
    for i, stock in enumerate(failing_stocks, 1):
        print(f"\n{'='*80}")
        print(f"TESTING {i}/{len(failing_stocks)}: {stock['name']}")
        print(f"{'='*80}")
        
        match, score = comprehensive_stock_search(app, stock)
        
        if match and score > 0.6:  # Stricter threshold with validation
            print(f"\n✓ FOUND! Score: {score:.1%}")
            print(f"  Symbol: {match['symbol']}")
            print(f"  Name: {match['longName']}")
            print(f"  Currency: {match['currency']}")
            print(f"  Exchange: {match['exchange']}")
            
            results['found'].append({
                'original': stock,
                'found': match,
                'score': score
            })
        else:
            print(f"\n✗ NOT FOUND (best score: {score:.1%})")
            results['still_missing'].append(stock)
        
        time.sleep(1)  # Pause between searches
    
    app.disconnect()
    
    # Final summary
    print(f"\n{'='*80}")
    print(f"COMPREHENSIVE SEARCH RESULTS")
    print(f"{'='*80}")
    print(f"Total tested: {len(failing_stocks)}")
    print(f"Successfully found: {len(results['found'])}")
    print(f"Still missing: {len(results['still_missing'])}")
    print(f"Success rate: {len(results['found'])/len(failing_stocks):.1%}")
    
    if results['found']:
        print(f"\n✓ SUCCESSFULLY FOUND:")
        for item in results['found']:
            orig = item['original']
            found = item['found']
            print(f"  {orig['name']} ({orig['ticker']}) -> {found['symbol']} ({found['currency']})")
    
    if results['still_missing']:
        print(f"\n✗ STILL MISSING (likely unavailable in paper trading):")
        for stock in results['still_missing']:
            print(f"  {stock['name']} ({stock['ticker']})")
    
    return results

if __name__ == "__main__":
    test_comprehensive_search()