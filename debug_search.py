#!/usr/bin/env python3
"""
Debug why ROCKA isn't being found in the comprehensive search
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
        print(f"    FOUND: {contract.symbol} | {contractDetails.longName} | {contract.currency}")

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        self.search_completed = True

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158, 2107]:
            print(f"    Error {errorCode}: {errorString}")

def debug_rockwool_search():
    """Debug why ROCKA search fails in comprehensive search but works in simple test"""
    
    app = IBApi()
    app.connect("127.0.0.1", 4002, clientId=16)
    
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    timeout = 10
    start_time = time.time()
    while not app.connected and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if not app.connected:
        print("Failed to connect")
        return
    
    # Test the exact same variations as comprehensive search
    variations = ['ROCK-A.CO', 'ROCK-A', 'ROCKA.CO', 'ROCKA', 'ROCK.A.CO', 'ROCK.A']
    
    print("Testing ROCKWOOL ticker variations step by step:")
    print("=" * 60)
    
    for i, variant in enumerate(variations, 1):
        print(f"\nTest {i}: {variant} (DKK) on SMART")
        
        contract = Contract()
        contract.symbol = variant
        contract.secType = "STK"
        contract.currency = "DKK"
        contract.exchange = "SMART"
        
        app.contract_details = []
        app.search_completed = False
        
        print(f"  Sending request for: {variant}")
        app.reqContractDetails(app.next_req_id, contract)
        app.next_req_id += 1
        
        timeout_start = time.time()
        while not app.search_completed and (time.time() - timeout_start) < 5:
            time.sleep(0.05)
        
        print(f"  Search completed: {app.search_completed}")
        print(f"  Results found: {len(app.contract_details)}")
        
        if app.contract_details:
            print(f"  SUCCESS!")
            break
        else:
            print(f"  No results")
        
        time.sleep(0.5)  # Longer pause between requests
    
    app.disconnect()
    
    print(f"\nDone. If ROCKA was found above, then there's a logic issue in comprehensive search.")

if __name__ == "__main__":
    debug_rockwool_search()