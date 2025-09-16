#!/usr/bin/env python3
"""
Simple test script to search for AAPL stock using IBKR API
Tests contract details request functionality
"""

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
            "symbol": contract.symbol,
            "longName": contractDetails.longName,
            "currency": contract.currency,
            "exchange": contract.exchange,
            "primaryExchange": contract.primaryExchange,
            "conId": contract.conId,
            "secType": contract.secType
        }
        self.contract_details.append(details)

        print(f"Found contract:")
        print(f"  Symbol: {details['symbol']}")
        print(f"  Long Name: {details['longName']}")
        print(f"  Currency: {details['currency']}")
        print(f"  Exchange: {details['exchange']}")
        print(f"  Primary Exchange: {details['primaryExchange']}")
        print(f"  Contract ID: {details['conId']}")
        print(f"  Security Type: {details['secType']}")
        print("-" * 50)

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        print(f"Contract details search completed for request {reqId}")
        self.search_completed = True

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158]:  # Ignore common info messages
            print(f'Error {errorCode}: {errorString}')

def create_stock_contract(symbol, currency="USD", exchange="SMART"):
    """Create a stock contract for search"""
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.currency = currency
    contract.exchange = exchange
    return contract

def search_stock(symbol, currency="USD"):
    """Search for a stock using IBKR API"""
    print(f"Searching for {symbol} in {currency}...")
    print("=" * 50)

    # Initialize API client
    app = IBApi()

    # Connect to IB Gateway (paper trading port 4002)
    print("Connecting to IB Gateway...")
    app.connect("127.0.0.1", 4002, clientId=21)

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
        return None

    # Create contract for search
    contract = create_stock_contract(symbol, currency)

    # Request contract details
    print(f"Requesting contract details for {symbol}...")
    app.contract_details = []
    app.search_completed = False
    app.reqContractDetails(1, contract)

    # Wait for search to complete
    timeout = 15
    start_time = time.time()
    while not app.search_completed and (time.time() - start_time) < timeout:
        time.sleep(0.1)

    # Disconnect
    app.disconnect()

    # Return results
    if app.contract_details:
        print(f"\nSearch successful! Found {len(app.contract_details)} contract(s) for {symbol}")
        return app.contract_details
    else:
        print(f"\nNo contracts found for {symbol}")
        return None

def main():
    """Main function to test stock search"""
    print("IBKR Stock Search Test")
    print("=" * 50)

    # Test with AAPL
    results = search_stock("AAPL", "USD")

    if results:
        print("\n" + "=" * 50)
        print("SEARCH RESULTS SUMMARY")
        print("=" * 50)
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['symbol']} - {result['longName']}")
            print(f"   Exchange: {result['exchange']} | Currency: {result['currency']}")
            print(f"   Contract ID: {result['conId']}")
    else:
        print("\nNo results to display")

if __name__ == "__main__":
    main()