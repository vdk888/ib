#!/usr/bin/env python3
"""
Quick script to identify the stocks that couldn't be found on IBKR
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
            "currency": contract.currency
        }
        self.contract_details.append(details)

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        self.search_completed = True

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        pass

def load_all_unique_stocks():
    """Load all unique stocks"""
    try:
        with open('data/universe.json', 'r') as f:
            data = json.load(f)
        
        all_stocks = []
        for screen_name, screen_data in data['screens'].items():
            all_stocks.extend(screen_data['stocks'])
        
        # Remove duplicates
        seen = set()
        unique_stocks = []
        for stock in all_stocks:
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

def create_contract_from_ticker(ticker, currency):
    contract = Contract()
    contract.symbol = ticker
    contract.secType = "STK"
    contract.currency = currency
    contract.exchange = "SMART"
    return contract

def get_best_ticker_variant(ticker):
    if not ticker:
        return None
    clean_ticker = re.sub(r'\.[A-Z]+$', '', ticker)
    if '-A' in clean_ticker:
        clean_ticker = clean_ticker.replace('-A', '.A')
    return clean_ticker

def similarity_score(str1, str2):
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def test_stock(app, stock):
    """Test if stock can be found"""
    
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
        
        if app.contract_details:
            universe_name = stock['name'].lower()
            universe_currency = stock['currency']
            
            for contract in app.contract_details:
                score = 0
                if contract['longName']:
                    name_sim = similarity_score(universe_name, contract['longName'].lower())
                    score += name_sim * 0.7
                if contract['currency'] == universe_currency:
                    score += 0.3
                if score > 0.5:
                    return True
    
    # Try ticker
    if stock.get('ticker'):
        clean_ticker = get_best_ticker_variant(stock['ticker'])
        if clean_ticker:
            contract = create_contract_from_ticker(clean_ticker, stock['currency'])
            
            app.contract_details = []
            app.search_completed = False
            app.reqContractDetails(app.next_req_id, contract)
            app.next_req_id += 1
            
            timeout_start = time.time()
            while not app.search_completed and (time.time() - timeout_start) < 2:
                time.sleep(0.05)
            
            if app.contract_details:
                universe_name = stock['name'].lower()
                universe_currency = stock['currency']
                
                for contract in app.contract_details:
                    score = 0
                    if contract['longName']:
                        name_sim = similarity_score(universe_name, contract['longName'].lower())
                        score += name_sim * 0.7
                    if contract['currency'] == universe_currency:
                        score += 0.3
                    if score > 0.4:
                        return True
    
    return False

def find_failing_stocks():
    """Find stocks that cannot be found on IBKR"""
    universe_stocks = load_all_unique_stocks()
    
    print(f"Identifying failing stocks from {len(universe_stocks)} total stocks...")
    
    # Connect to IBKR
    app = IBApi()
    app.connect("127.0.0.1", 4002, clientId=11)
    
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    timeout = 10
    start_time = time.time()
    while not app.connected and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if not app.connected:
        print("Failed to connect")
        return
    
    failing_stocks = []
    
    for i, stock in enumerate(universe_stocks):
        found = test_stock(app, stock)
        
        if not found:
            failing_stocks.append({
                'name': stock['name'],
                'ticker': stock.get('ticker', 'N/A'),
                'isin': stock.get('isin', 'N/A'), 
                'currency': stock['currency'],
                'country': stock.get('country', 'N/A'),
                'sector': stock.get('sector', 'N/A')
            })
            print(f"FAIL: {stock['name']} | {stock.get('ticker', 'N/A')} | {stock['currency']}")
        
        time.sleep(0.05)
    
    app.disconnect()
    
    print(f"\nFAILING STOCKS ({len(failing_stocks)} total):")
    print("=" * 80)
    for i, stock in enumerate(failing_stocks, 1):
        print(f"{i:2d}. {stock['name']}")
        print(f"    Ticker: {stock['ticker']}")
        print(f"    ISIN: {stock['isin']}")
        print(f"    Currency: {stock['currency']}")
        print(f"    Country: {stock['country']}")  
        print(f"    Sector: {stock['sector']}")
        print()

if __name__ == "__main__":
    find_failing_stocks()