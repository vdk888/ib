#!/usr/bin/env python3
"""
Interactive Brokers API script to search for stocks using ISIN from universe.json
Gets contract details and market data for stocks from the portfolio universe
"""

import json
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
            "category": contractDetails.category
        }
        self.contract_details.append(details)
        print(f"Contract found: {contract.symbol} ({contract.localSymbol}) on {contract.exchange}")
        print(f"  Long Name: {contractDetails.longName}")
        print(f"  Industry: {contractDetails.industry}")
        print(f"  Category: {contractDetails.category}")

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        print(f"Contract details search completed for reqId: {reqId}")

    def tickPrice(self, reqId, tickType, price, attrib):
        super().tickPrice(reqId, tickType, price, attrib)
        if reqId not in self.market_data:
            self.market_data[reqId] = {}
        
        tick_names = {
            1: "bid", 2: "ask", 4: "last", 6: "high", 7: "low", 9: "close"
        }
        
        if tickType in tick_names:
            self.market_data[reqId][tick_names[tickType]] = price
            print(f"Market Data - {tick_names[tickType]}: ${price:.2f}")

    def tickSize(self, reqId, tickType, size):
        super().tickSize(reqId, tickType, size)
        if reqId not in self.market_data:
            self.market_data[reqId] = {}
        
        size_names = {
            0: "bid_size", 3: "ask_size", 5: "last_size", 8: "volume"
        }
        
        if tickType in size_names:
            self.market_data[reqId][size_names[tickType]] = size
            if tickType == 8:  # Volume
                print(f"Market Data - Volume: {size:,}")

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158, 2107]:  # Ignore common info messages
            print(f'Error {errorCode}: {errorString}')

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

def main():
    # Load universe stocks
    universe_stocks = load_universe_stocks()
    if not universe_stocks:
        print("No stocks found in universe data")
        return
    
    # Take the first stock for testing
    test_stock = universe_stocks[0]
    print(f"Testing with stock: {test_stock['name']} (ISIN: {test_stock['isin']})")
    print(f"Currency: {test_stock['currency']}, Sector: {test_stock['sector']}")
    print("-" * 60)
    
    # Initialize API client
    app = IBApi()
    
    # Connect to IB Gateway (paper trading port 4002)
    print("Connecting to IB Gateway...")
    app.connect("127.0.0.1", 4002, clientId=3)
    
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
    
    # Create contract using ISIN
    contract = create_contract_from_isin(test_stock['isin'], test_stock['currency'])
    
    # Request contract details
    print(f"Searching for contract details using ISIN: {test_stock['isin']}")
    app.reqContractDetails(app.next_req_id, contract)
    
    # Wait for contract details
    time.sleep(3)
    
    if app.contract_details:
        # Get market data for the first contract found
        first_contract_details = app.contract_details[0]
        print(f"\nRequesting market data for {first_contract_details['symbol']}...")
        
        # Create proper contract for market data request
        market_contract = Contract()
        market_contract.symbol = first_contract_details['symbol']
        market_contract.secType = "STK"
        market_contract.exchange = first_contract_details['exchange']
        market_contract.currency = first_contract_details['currency']
        
        # Request market data
        app.reqMktData(app.next_req_id + 1, market_contract, "", False, False, [])
        
        # Wait for market data
        time.sleep(5)
        
        # Cancel market data
        app.cancelMktData(app.next_req_id + 1)
        
        print("\n" + "="*60)
        print("SEARCH RESULTS SUMMARY")
        print("="*60)
        
        print(f"Universe Stock: {test_stock['name']}")
        print(f"ISIN: {test_stock['isin']}")
        print(f"Sector: {test_stock['sector']}")
        print(f"Universe Price: {test_stock['currency']} {test_stock['price']}")
        
        print(f"\nIBKR Contract Details:")
        for detail in app.contract_details:
            print(f"  Symbol: {detail['symbol']}")
            print(f"  Exchange: {detail['exchange']}")
            print(f"  Currency: {detail['currency']}")
            print(f"  Long Name: {detail['longName']}")
            print(f"  Industry: {detail['industry']}")
        
        if app.market_data:
            print(f"\nCurrent Market Data:")
            for req_id, data in app.market_data.items():
                for key, value in data.items():
                    if key == 'volume':
                        print(f"  {key.capitalize()}: {value:,}")
                    else:
                        print(f"  {key.capitalize()}: ${value:.2f}")
        
    else:
        print("No contract details found for this ISIN")
    
    # Disconnect
    app.disconnect()

if __name__ == "__main__":
    main()