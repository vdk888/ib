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
        self.account_id = None
        self.open_orders = {}
        self.cancelled_orders = []
        self.orders_received = False

    def connectAck(self):
        super().connectAck()
        print("Connected to IB Gateway")
        self.connected = True

    def connectionClosed(self):
        super().connectionClosed()
        print("Connection closed")
        self.connected = False

    def managedAccounts(self, accountsList: str):
        super().managedAccounts(accountsList)
        accounts = accountsList.split(",")
        self.account_id = accounts[0]
        print(f"Account ID: {self.account_id}")

    def openOrder(self, orderId, contract, order, orderState):
        """Receive open order information"""
        self.open_orders[orderId] = {
            'symbol': contract.symbol,
            'action': order.action,
            'quantity': order.totalQuantity,
            'status': orderState.status
        }
        print(f"Found Order {orderId}: {contract.symbol} {order.action} {order.totalQuantity} ({orderState.status})")

    def openOrderEnd(self):
        """Called when all open orders have been received"""
        self.orders_received = True
        print(f"Total open orders found: {len(self.open_orders)}")

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        """Receive order status updates"""
        if status == "Cancelled":
            self.cancelled_orders.append(orderId)
            print(f"Order {orderId} cancelled successfully")
        else:
            print(f"Order {orderId} status: {status}")

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158, 2107]:  # Ignore common info messages
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
    app.connect("127.0.0.1", 4002, clientId=50)  # Use unique client ID

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

    # Wait for account ID
    time.sleep(2)
    if not app.account_id:
        print("Warning: No account ID received")

    # Step 1: Retrieve all open orders first
    print("\n[STEP 1] Retrieving all open orders...")
    app.reqAllOpenOrders()  # Get all open orders from all clients

    # Wait for orders to be retrieved
    timeout = 10
    start_time = time.time()
    while not app.orders_received and (time.time() - start_time) < timeout:
        time.sleep(0.5)

    if not app.open_orders:
        print("No open orders found. Account is already clean.")
        app.disconnect()
        return

    # Show order breakdown by status
    presubmitted_count = sum(1 for order in app.open_orders.values() if order['status'] == 'PreSubmitted')
    pendingcancel_count = sum(1 for order in app.open_orders.values() if order['status'] == 'PendingCancel')
    other_count = len(app.open_orders) - presubmitted_count - pendingcancel_count

    print(f"Order Status Summary:")
    print(f"  PreSubmitted: {presubmitted_count}")
    print(f"  PendingCancel: {pendingcancel_count}")
    print(f"  Other: {other_count}")
    print(f"  Total: {len(app.open_orders)}")

    # Step 2: Try global cancel first
    print(f"\n[STEP 2] Attempting global cancel of {len(app.open_orders)} orders...")
    print("This will cancel ALL open orders including PreSubmitted ones...")

    app.reqGlobalCancel()
    print("Global cancel request sent!")

    # Wait for global cancel to process
    time.sleep(5)

    # Step 3: Individual cancellation for any remaining orders
    print(f"\n[STEP 3] Checking for remaining orders and canceling individually...")

    # Re-request orders to see what's left
    app.open_orders.clear()
    app.orders_received = False
    app.reqAllOpenOrders()

    # Wait for updated order list
    timeout = 8
    start_time = time.time()
    while not app.orders_received and (time.time() - start_time) < timeout:
        time.sleep(0.5)

    remaining_orders = [oid for oid, order in app.open_orders.items()
                       if order['status'] in ['PreSubmitted', 'Submitted']]

    if remaining_orders:
        print(f"Found {len(remaining_orders)} remaining orders. Canceling individually...")
        for order_id in remaining_orders:
            order_info = app.open_orders[order_id]
            print(f"Canceling Order {order_id}: {order_info['symbol']} ({order_info['status']})")
            app.reqCancelOrder(order_id)
            time.sleep(0.5)  # Small delay between cancellations

        # Wait for individual cancellations to process
        print("Waiting for individual cancellations to complete...")
        time.sleep(5)
    else:
        print("No remaining orders to cancel individually.")

    # Step 4: Final verification
    print(f"\n[STEP 4] Final verification...")
    app.open_orders.clear()
    app.orders_received = False
    app.reqAllOpenOrders()

    timeout = 5
    start_time = time.time()
    while not app.orders_received and (time.time() - start_time) < timeout:
        time.sleep(0.5)

    if app.open_orders:
        print(f"WARNING: {len(app.open_orders)} orders still remain:")
        for order_id, order_info in app.open_orders.items():
            print(f"  Order {order_id}: {order_info['symbol']} {order_info['action']} ({order_info['status']})")
    else:
        print("SUCCESS: All orders have been cancelled!")

    print(f"Total orders cancelled: {len(app.cancelled_orders)}")

    # Disconnect
    print("\nDisconnecting...")
    app.disconnect()
    print("Done!")

if __name__ == "__main__":
    main()