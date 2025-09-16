#!/usr/bin/env python3
"""
Test IBKR connection
"""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
import threading
import time

class TestApi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connected = False

    def connectAck(self):
        super().connectAck()
        self.connected = True
        print("Connected to IBKR Gateway successfully!")

    def connectionClosed(self):
        super().connectionClosed()
        self.connected = False
        print("Connection to IBKR Gateway closed")

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        print(f"IBKR Error {errorCode}: {errorString}")

def test_connection():
    print("Testing IBKR Gateway connection...")
    print("Host: 127.0.0.1")
    print("Port: 4002")
    print("Client ID: 20")
    print("-" * 40)

    app = TestApi()
    app.connect("127.0.0.1", 4002, clientId=20)

    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()

    # Wait up to 10 seconds for connection
    timeout = 10
    start_time = time.time()
    while not app.connected and (time.time() - start_time) < timeout:
        time.sleep(0.1)

    if app.connected:
        print("Connection successful!")
        print("IBKR Gateway is running and accessible")

        # Disconnect
        app.disconnect()
        time.sleep(1)
        return True
    else:
        print("Connection failed!")
        print("Please check:")
        print("1. IBKR Gateway (TWS) is running")
        print("2. API is enabled in Gateway settings")
        print("3. Port 4002 is correct (paper trading)")
        print("4. No other applications are using client ID 20")
        return False

if __name__ == "__main__":
    test_connection()