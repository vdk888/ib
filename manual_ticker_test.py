#!/usr/bin/env python3
"""
Manual test of specific tickers that should work according to the user
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
        }
        self.contract_details.append(details)
        print(f"  FOUND: {contract.symbol} | {contractDetails.longName} | {contract.currency} | {contract.exchange}")

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        self.search_completed = True

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158, 2107]:
            print(f"  Error {errorCode}: {errorString}")

def test_specific_tickers():
    """Test the specific ticker formats mentioned by the user"""
    
    test_cases = [
        # Format: (description, symbol, currency, exchange)
        ("ROCKWOOL A shares", "ROCKA", "DKK", "SMART"),
        ("ROCKWOOL A shares - OMXCOP", "ROCKA", "DKK", "OMXCOP"),
        ("Everplay Group", "EVPL", "GBP", "SMART"),
        ("Everplay Group - LSE", "EVPL", "GBP", "LSE"),
        ("New Wave B shares", "NEWA.B", "SEK", "SMART"),
        ("New Wave B shares - OMXSTO", "NEWA.B", "SEK", "OMXSTO"),
        ("New Wave B shares alt", "NEWAB", "SEK", "SMART"),
        ("Sarantis", "SAR", "EUR", "SMART"),
        ("Dewhurst", "DWHT", "GBP", "SMART"),
        ("Dewhurst - LSE", "DWHT", "GBP", "LSE"),
        ("Ilyda", "ILYDA", "EUR", "SMART"),
        ("Thessaloniki Port (OLTH)", "OLTH", "EUR", "SMART"),
        # Test some known working tickers for comparison
        ("Apple (control)", "AAPL", "USD", "SMART"),
        ("Microsoft (control)", "MSFT", "USD", "SMART"),
    ]
    
    # Connect to IBKR
    app = IBApi()
    app.connect("127.0.0.1", 4002, clientId=13)
    
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    timeout = 10
    start_time = time.time()
    while not app.connected and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if not app.connected:
        print("Failed to connect")
        return
    
    print("Testing specific ticker formats...")
    print("="*80)
    
    found_count = 0
    
    for description, symbol, currency, exchange in test_cases:
        print(f"\nTesting {description}: {symbol} ({currency}) on {exchange}")
        
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.currency = currency
        contract.exchange = exchange
        
        app.contract_details = []
        app.search_completed = False
        app.reqContractDetails(app.next_req_id, contract)
        app.next_req_id += 1
        
        timeout_start = time.time()
        while not app.search_completed and (time.time() - timeout_start) < 3:
            time.sleep(0.05)
        
        if app.contract_details:
            found_count += 1
            print(f"  SUCCESS!")
        else:
            print(f"  NOT FOUND")
        
        time.sleep(0.2)
    
    app.disconnect()
    
    print(f"\n{'='*80}")
    print(f"MANUAL TICKER TEST RESULTS")
    print(f"{'='*80}")
    print(f"Total tests: {len(test_cases)}")
    print(f"Found: {found_count}")
    print(f"Success rate: {found_count/len(test_cases):.1%}")

if __name__ == "__main__":
    test_specific_tickers()