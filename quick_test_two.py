#!/usr/bin/env python3
"""
Quick test of just ROCKWOOL and New Wave to verify they work
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

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        self.search_completed = True

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        pass

def test_two_stocks():
    """Test just ROCKWOOL and New Wave"""
    
    app = IBApi()
    app.connect("127.0.0.1", 4002, clientId=14)
    
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    timeout = 10
    start_time = time.time()
    while not app.connected and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if not app.connected:
        print("Failed to connect")
        return
    
    # Test ROCKA
    print("Testing ROCKA (DKK)...")
    contract = Contract()
    contract.symbol = "ROCKA"
    contract.secType = "STK"
    contract.currency = "DKK"
    contract.exchange = "SMART"
    
    app.contract_details = []
    app.search_completed = False
    app.reqContractDetails(app.next_req_id, contract)
    app.next_req_id += 1
    
    timeout_start = time.time()
    while not app.search_completed and (time.time() - timeout_start) < 3:
        time.sleep(0.05)
    
    if app.contract_details:
        print(f"ROCKA FOUND: {app.contract_details[0]['longName']}")
    else:
        print("ROCKA NOT FOUND")
    
    # Test NEWA.B
    print("\nTesting NEWA.B (SEK)...")
    contract = Contract()
    contract.symbol = "NEWA.B"
    contract.secType = "STK"
    contract.currency = "SEK"
    contract.exchange = "SMART"
    
    app.contract_details = []
    app.search_completed = False
    app.reqContractDetails(app.next_req_id, contract)
    app.next_req_id += 1
    
    timeout_start = time.time()
    while not app.search_completed and (time.time() - timeout_start) < 3:
        time.sleep(0.05)
    
    if app.contract_details:
        print(f"NEWA.B FOUND: {app.contract_details[0]['longName']}")
    else:
        print("NEWA.B NOT FOUND")
    
    app.disconnect()

if __name__ == "__main__":
    test_two_stocks()