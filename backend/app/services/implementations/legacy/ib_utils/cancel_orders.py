#!/usr/bin/env python3
"""
Interactive Brokers API script to cancel all open orders
Connects to IB Gateway and cancels all pending orders
"""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.order import Order
from ibapi.contract import Contract
import threading
import time

class IBOrderCanceler(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connected = False
        self.open_orders = []
        self.orders_received = False
        
    def connectAck(self):
        super().connectAck()
        print("Connected to IB Gateway")
        self.connected = True

    def connectionClosed(self):
        super().connectionClosed()
        print("Connection closed")
        self.connected = False

    def openOrder(self, orderId: int, contract: Contract, order: Order, orderState):
        super().openOrder(orderId, contract, order, orderState)
        order_info = {
            'orderId': orderId,
            'symbol': contract.symbol,
            'action': order.action,
            'totalQuantity': order.totalQuantity,
            'orderType': order.orderType,
            'status': orderState.status
        }
        self.open_orders.append(order_info)
        print(f"Open Order - ID: {orderId}, {contract.symbol} {order.action} {order.totalQuantity} @ {order.orderType}, Status: {orderState.status}")

    def openOrderEnd(self):
        super().openOrderEnd()
        print(f"\n=== Found {len(self.open_orders)} open orders ===")
        self.orders_received = True

    def orderStatus(self, orderId: int, status: str, filled: float, remaining: float, avgFillPrice: float, 
                   permId: int, parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float):
        super().orderStatus(orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        print(f"Order {orderId} status: {status}")

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158]:  # Ignore common info messages
            print(f'Error {errorCode}: {errorString}')

def main():
    # Initialize API client
    app = IBOrderCanceler()
    
    # Connect to IB Gateway (try paper trading port 4002 first, then live port 4001)
    print("Connecting to IB Gateway...")
    try:
        app.connect("127.0.0.1", 4002, clientId=3)
        print("Attempting paper trading connection (port 4002)...")
    except:
        print("Paper trading port failed, trying live port 4001...")
        app.connect("127.0.0.1", 4001, clientId=3)
    
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
    
    print("Connected successfully!")
    
    # Request all open orders
    print("\nRequesting open orders...")
    app.reqAllOpenOrders()
    
    # Wait for orders to be received
    timeout = 10
    start_time = time.time()
    while not app.orders_received and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if not app.orders_received:
        print("Timeout waiting for open orders")
        app.disconnect()
        return
    
    # Cancel all open orders
    if app.open_orders:
        print(f"\nCanceling {len(app.open_orders)} open orders...")
        
        for order_info in app.open_orders:
            order_id = order_info['orderId']
            print(f"Canceling order {order_id} ({order_info['symbol']} {order_info['action']} {order_info['totalQuantity']})")
            app.cancelOrder(order_id, "")
            time.sleep(0.5)  # Small delay between cancellations
        
        print("\nAll cancellation requests sent.")
        
        # Wait a moment for confirmations
        time.sleep(3)
        
    else:
        print("No open orders found to cancel.")
    
    # Disconnect
    print("Disconnecting...")
    app.disconnect()
    print("Done!")

if __name__ == "__main__":
    main()