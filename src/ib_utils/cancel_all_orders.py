#!/usr/bin/env python3
"""
Interactive Brokers API script to cancel ALL orders globally
Uses the reqGlobalCancel() method to cancel all orders at once
"""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
import threading
import time

class IBGlobalCanceler(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connected = False
        
    def connectAck(self):
        super().connectAck()
        print("Connected to IB Gateway")
        self.connected = True

    def connectionClosed(self):
        super().connectionClosed()
        print("Connection closed")
        self.connected = False

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158]:  # Ignore common info messages
            print(f'Error {errorCode}: {errorString}')
        elif errorCode == 2104:
            print("Market data farm connection OK")
        elif errorCode == 2106:
            print("HMDS data farm connection OK")

def main():
    # Initialize API client
    app = IBGlobalCanceler()
    
    # Connect to IB Gateway
    print("Connecting to IB Gateway...")
    app.connect("127.0.0.1", 4002, clientId=4)
    
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
        print("Make sure IB Gateway/TWS is running and configured properly")
        return
    
    print("Connected successfully!")
    
    # Wait a moment for connection to stabilize
    time.sleep(2)
    
    # Cancel ALL orders globally
    print("\n🚨 CANCELING ALL ORDERS GLOBALLY 🚨")
    print("This will cancel ALL open orders across ALL accounts...")
    
    # Use global cancel - this cancels ALL orders
    app.reqGlobalCancel()
    print("Global cancel request sent!")
    
    # Wait for the cancellation to process
    time.sleep(3)
    
    print("All orders should now be cancelled.")
    
    # Disconnect
    print("\nDisconnecting...")
    app.disconnect()
    print("Done!")

if __name__ == "__main__":
    main()