#!/usr/bin/env python3
"""
Simple Interactive Brokers API script to place a market buy order
Connects to paper trading account via IB Gateway on port 4002
"""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
import threading
import time

class IBApi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.nextorderId = None
        self.connected = False

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextorderId = orderId
        print(f'Next valid order ID: {self.nextorderId}')

    def connectAck(self):
        super().connectAck()
        print("Connected to IB Gateway")

    def connectionClosed(self):
        super().connectionClosed()
        print("Connection closed")
        self.connected = False

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print(f'Order Status - ID: {orderId}, Status: {status}, Filled: {filled}, Remaining: {remaining}, Avg Fill Price: {avgFillPrice}')

    def openOrder(self, orderId, contract, order, orderState):
        print(f'Open Order - ID: {orderId}, Symbol: {contract.symbol}, Action: {order.action}, Qty: {order.totalQuantity}, Status: {orderState.status}')

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        print(f'Error {errorCode}: {errorString}')

def create_stock_contract(symbol):
    """Create a stock contract"""
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"
    return contract

def create_market_order(action, quantity):
    """Create a market order"""
    order = Order()
    order.action = action
    order.orderType = "MKT"
    order.totalQuantity = quantity
    order.eTradeOnly = False
    order.firmQuoteOnly = False
    return order

def main():
    # Initialize API client
    app = IBApi()
    
    # Connect to IB Gateway (paper trading port 4002)
    print("Connecting to IB Gateway...")
    app.connect("127.0.0.1", 4002, clientId=1)
    
    # Start message processing in separate thread
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    # Wait for connection and next valid order ID
    timeout = 10
    start_time = time.time()
    while app.nextorderId is None and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if app.nextorderId is None:
        print("Failed to get valid order ID. Check connection.")
        return
    
    # Create contract for AAPL stock
    contract = create_stock_contract("AAPL")
    
    # Create market buy order for 1 share
    order = create_market_order("BUY", 1)
    
    # Place the order
    print(f"Placing market buy order for 1 share of AAPL...")
    app.placeOrder(app.nextorderId, contract, order)
    
    # Wait a bit to see order status updates
    time.sleep(5)
    
    # Disconnect
    app.disconnect()
    print("Disconnected from IB Gateway")

if __name__ == "__main__":
    main()