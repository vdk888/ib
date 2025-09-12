#!/usr/bin/env python3
"""
Enhanced Interactive Brokers API script to search for stocks using ISIN or ticker from universe.json
Includes intelligent matching based on name similarity, currency, and country
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
        self.market_data = {}
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

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        self.search_completed = True
        print(f"  Search completed for reqId: {reqId}")

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158, 2107]:  # Ignore common info messages
            print(f'  Error {errorCode}: {errorString}')

def load_universe_stocks():
    """Load stocks from universe.json"""
    try:
        with open('data/universe.json', 'r') as f:
            data = json.load(f)
        
        all_stocks = []
        # Get stocks from all screens
        for screen_name, screen_data in data['screens'].items():
            all_stocks.extend(screen_data['stocks'])
        
        return all_stocks
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
    
    # Remove exchange suffix if present (.L, .AX, .T, .TO, etc.)
    base_ticker = re.sub(r'\.[A-Z]+$', '', ticker)
    if base_ticker != ticker:
        variations.append(base_ticker)
    
    # Handle share class indicators (-A, -B, etc.)
    if '-A' in ticker:
        no_class = ticker.replace('-A', '')
        variations.append(no_class)
        # Try with class indicator as DOT suffix (CCL-A.TO -> CCL.A)  
        class_dot_suffix = ticker.replace('-A', '.A')
        variations.append(class_dot_suffix)
        # Try with class indicator without dash (CCL-A.TO -> CCLA.TO)
        class_suffix = ticker.replace('-A', 'A')
        variations.append(class_suffix)
        # Also try base without exchange suffix but with dot class (CCL-A.TO -> CCL.A)
        no_exchange_base = re.sub(r'\.[A-Z]+$', '', ticker)  # CCL-A.TO -> CCL-A
        if no_exchange_base != ticker:
            dot_class_no_exchange = no_exchange_base.replace('-A', '.A')  # CCL-A -> CCL.A
            variations.append(dot_class_no_exchange)
    
    # Add common exchange mappings
    exchange_mappings = {
        '.TO': ['TSE', 'VENTURE'],  # Toronto Stock Exchange
        '.L': ['LSE', 'LSEETF'],    # London Stock Exchange
        '.AX': ['ASX'],             # Australian Securities Exchange
        '.T': ['TSE', 'TSEJ'],      # Tokyo Stock Exchange
        '.PA': ['SBF'],             # Euronext Paris
        '.DE': ['XETRA', 'DTB'],    # Frankfurt Stock Exchange
        '.CO': ['CSE']              # Copenhagen Stock Exchange
    }
    
    # Remove duplicates while preserving order
    seen = set()
    variations = [x for x in variations if not (x in seen or seen.add(x))]
    
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
    
    print(f"  Matching against: {universe_stock['name']} ({universe_currency})")
    
    for contract in contracts:
        score = 0.0
        reasons = []
        
        # Name similarity (most important - 60% weight)
        ibkr_name = contract['longName'].lower() if contract['longName'] else ''
        name_sim = similarity_score(universe_name, ibkr_name)
        score += name_sim * 0.6
        if name_sim > 0.3:
            reasons.append(f"name_sim:{name_sim:.2f}")
        
        # Currency match (30% weight)
        if contract['currency'] == universe_currency:
            score += 0.3
            reasons.append("currency_match")
        
        # Exchange/Country correlation (10% weight)
        exchange_country_map = {
            'LSE': 'united kingdom', 'LSEETF': 'united kingdom',
            'ASX': 'australia', 'SMART': 'various',
            'TSE': 'japan', 'TSEJ': 'japan',
            'SBF': 'france', 'SBFM': 'france',
            'XETRA': 'germany', 'DTB': 'germany',
            'CSE': 'denmark'
        }
        
        exchange_country = exchange_country_map.get(contract['exchange'], '').lower()
        if exchange_country and exchange_country in universe_country:
            score += 0.1
            reasons.append("country_match")
        
        print(f"    {contract['symbol']} ({contract['exchange']}): score={score:.3f} [{', '.join(reasons)}]")
        
        if score > best_score:
            best_score = score
            best_match = contract
    
    return best_match, best_score

def search_stock_by_isin(app, stock):
    """Search for stock using ISIN"""
    print(f"Searching by ISIN: {stock['isin']}")
    contract = create_contract_from_isin(stock['isin'], stock['currency'])
    
    app.contract_details = []
    app.search_completed = False
    app.reqContractDetails(app.next_req_id, contract)
    app.next_req_id += 1
    
    # Wait for search to complete
    timeout = 5
    start_time = time.time()
    while not app.search_completed and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    return app.contract_details

def search_stock_by_ticker(app, stock):
    """Search for stock using ticker variations and multiple exchanges"""
    ticker = stock['ticker']
    currency = stock['currency']
    variations = get_ticker_variations(ticker)
    
    print(f"Searching by ticker variations: {variations}")
    
    all_contracts = []
    
    # Determine appropriate exchanges based on currency and ticker
    exchanges = ['SMART']  # Always try SMART first
    if currency == 'CAD' or '.TO' in ticker:
        exchanges.extend(['TSE', 'VENTURE'])
    elif currency == 'GBP' or '.L' in ticker:
        exchanges.extend(['LSE', 'LSEETF'])
    elif currency == 'AUD' or '.AX' in ticker:
        exchanges.extend(['ASX'])
    elif currency == 'JPY' or '.T' in ticker:
        exchanges.extend(['TSE', 'TSEJ'])
    elif currency == 'EUR':
        if '.PA' in ticker:
            exchanges.extend(['SBF'])
        elif '.DE' in ticker:
            exchanges.extend(['XETRA', 'DTB'])
    
    if currency == 'USD':
        exchanges.extend(['NASDAQ', 'NYSE'])
    
    for variant in variations[:4]:  # Try top 4 variations
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
            
            if len(all_contracts) >= 10:  # Limit results
                print(f"  Found {len(all_contracts)} contracts, stopping search")
                return all_contracts
    
    # If still no results and currency is CAD, try USD variants (dual-listed)
    if not all_contracts and currency == 'CAD':
        print(f"  No CAD results, trying USD variants...")
        for variant in variations[:2]:
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
                
                if len(all_contracts) >= 5:
                    break
            if len(all_contracts) >= 5:
                break
    
    return all_contracts

def main():
    # Load universe stocks
    universe_stocks = load_universe_stocks()
    if not universe_stocks:
        print("No stocks found in universe data")
        return
    
    # Filter stocks for testing - get some with ISIN and some with ticker only
    stocks_with_isin = [s for s in universe_stocks if s.get('isin') and s.get('isin') != 'null']
    stocks_with_ticker_only = [s for s in universe_stocks if (not s.get('isin') or s.get('isin') == 'null') and s.get('ticker')]
    
    print(f"Found {len(stocks_with_isin)} stocks with ISIN")
    print(f"Found {len(stocks_with_ticker_only)} stocks with ticker only")
    
    # Test with first stock from each category, plus CCL Industries specifically
    test_stocks = []
    if stocks_with_isin:
        test_stocks.append(stocks_with_isin[0])
    
    # Add CCL Industries specifically for testing
    ccl_test = {
        "ticker": "CCL-A.TO",
        "isin": "null",
        "name": "CCL Industries Inc.",
        "currency": "CAD",
        "sector": "Industrials", 
        "country": "Canada",
        "price": 77.35
    }
    test_stocks.append(ccl_test)
    
    # Add another ticker-only stock if available
    if stocks_with_ticker_only and stocks_with_ticker_only[0]['ticker'] != 'CCL-A.TO':
        test_stocks.append(stocks_with_ticker_only[0])
    
    if not test_stocks:
        print("No suitable test stocks found")
        return
    
    # Initialize API client
    app = IBApi()
    
    # Connect to IB Gateway (paper trading port 4002)
    print("Connecting to IB Gateway...")
    app.connect("127.0.0.1", 4002, clientId=5)
    
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
    
    # Process each test stock
    for i, stock in enumerate(test_stocks, 1):
        print(f"\n{'='*80}")
        print(f"TEST STOCK {i}: {stock['name']}")
        print(f"Ticker: {stock.get('ticker', 'N/A')}")
        print(f"ISIN: {stock.get('isin', 'N/A')}")
        print(f"Currency: {stock['currency']}")
        print(f"Country: {stock.get('country', 'N/A')}")
        print(f"Sector: {stock['sector']}")
        print("="*80)
        
        found_contracts = []
        
        # Try ISIN first if available
        if stock.get('isin'):
            found_contracts = search_stock_by_isin(app, stock)
        
        # If no results with ISIN or no ISIN available, try ticker
        if not found_contracts and stock.get('ticker'):
            found_contracts = search_stock_by_ticker(app, stock)
        
        # Match and rank results
        if found_contracts:
            print(f"\nFound {len(found_contracts)} potential matches:")
            best_match, best_score = match_contracts(stock, found_contracts)
            
            if best_match and best_score > 0.3:  # Minimum confidence threshold
                print(f"\nBEST MATCH (confidence: {best_score:.1%}):")
                print(f"  IBKR Symbol: {best_match['symbol']}")
                print(f"  Exchange: {best_match['exchange']}")
                print(f"  Currency: {best_match['currency']}")
                print(f"  Long Name: {best_match['longName']}")
                print(f"  Industry: {best_match['industry']}")
                print(f"  Category: {best_match['category']}")
            else:
                print(f"\nNo confident match found (best score: {best_score:.1%})")
        else:
            print("\nNo contracts found")
        
        time.sleep(1)  # Pause between stocks
    
    # Disconnect
    app.disconnect()

if __name__ == "__main__":
    main()