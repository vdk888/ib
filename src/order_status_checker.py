#!/usr/bin/env python3
"""
Order Status Checker for Interactive Brokers
Fetches current orders from IBKR account and compares with orders.json
"""

import json
import time
import threading
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.execution import Execution


class IBOrderStatusChecker(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connected = False
        self.account_id = None

        # Order tracking
        self.open_orders = {}  # orderId -> {contract, order, orderState}
        self.order_status = {}  # orderId -> status info
        self.executions = {}   # orderId -> execution details
        self.positions = {}    # symbol -> position info
        self.completed_orders = {}  # orderId -> completed order info

        # Request tracking
        self.requests_completed = {
            'orders': False,
            'positions': False,
            'executions': False,
            'completed_orders': False
        }

    def connectAck(self):
        super().connectAck()
        print("[OK] Connected to IB Gateway")
        self.connected = True

    def connectionClosed(self):
        super().connectionClosed()
        print("[CLOSED] Connection closed")
        self.connected = False

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        print(f"[OK] Next valid order ID: {orderId}")

    def managedAccounts(self, accountsList: str):
        super().managedAccounts(accountsList)
        accounts = accountsList.split(",")
        self.account_id = accounts[0]
        print(f"[OK] Account ID: {self.account_id}")

    def openOrder(self, orderId, contract, order, orderState):
        """Receive open order information"""
        print(f"[OPEN] Order {orderId}: {contract.symbol}, {order.action} {order.totalQuantity}, Status: {orderState.status}")
        self.open_orders[orderId] = {
            'contract': contract,
            'order': order,
            'orderState': orderState,
            'symbol': contract.symbol,
            'action': order.action,
            'quantity': order.totalQuantity,
            'orderType': order.orderType,
            'status': orderState.status,
            'avgFillPrice': getattr(orderState, 'avgFillPrice', ''),
            'currency': contract.currency,
            'filled': getattr(orderState, 'filled', 0),
            'remaining': getattr(orderState, 'remaining', 0)
        }

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        """Receive order status updates"""
        print(f"[STATUS] Order {orderId}: {status}, Filled: {filled}, Remaining: {remaining}, Avg Price: ${avgFillPrice:.2f}")
        if whyHeld:
            print(f"[STATUS]   Why held: {whyHeld}")
        self.order_status[orderId] = {
            'status': status,
            'filled': filled,
            'remaining': remaining,
            'avgFillPrice': avgFillPrice,
            'permId': permId,
            'lastFillPrice': lastFillPrice,
            'whyHeld': whyHeld
        }

    def openOrderEnd(self):
        """Called when all open orders have been received"""
        self.requests_completed['orders'] = True
        print(f"[OK] Received {len(self.open_orders)} open orders")

    def position(self, account, contract, position, avgCost):
        """Receive position information"""
        if position != 0:  # Only store non-zero positions
            self.positions[contract.symbol] = {
                'symbol': contract.symbol,
                'position': position,
                'avgCost': avgCost,
                'currency': contract.currency,
                'exchange': contract.exchange
            }

    def positionEnd(self):
        """Called when all positions have been received"""
        self.requests_completed['positions'] = True
        print(f"[OK] Received {len(self.positions)} positions")

    def execDetails(self, reqId, contract, execution):
        """Receive execution details"""
        order_id = execution.orderId
        if order_id not in self.executions:
            self.executions[order_id] = []

        self.executions[order_id].append({
            'symbol': contract.symbol,
            'side': execution.side,
            'shares': execution.shares,
            'price': execution.price,
            'time': execution.time,
            'exchange': execution.exchange
        })

    def execDetailsEnd(self, reqId):
        """Called when all execution details have been received"""
        self.requests_completed['executions'] = True
        print(f"[OK] Received execution details for {len(self.executions)} orders")

    def completedOrder(self, contract, order, orderState):
        """Receive completed order information"""
        order_id = order.orderId
        self.completed_orders[order_id] = {
            'contract': contract,
            'order': order,
            'orderState': orderState,
            'symbol': contract.symbol,
            'action': order.action,
            'quantity': order.totalQuantity,
            'orderType': order.orderType,
            'status': orderState.status,
            'avgFillPrice': getattr(orderState, 'avgFillPrice', ''),
            'currency': contract.currency,
            'filled': getattr(orderState, 'filled', 0),
            'remaining': getattr(orderState, 'remaining', 0)
        }

    def completedOrdersEnd(self):
        """Called when all completed orders have been received"""
        self.requests_completed['completed_orders'] = True
        print(f"[OK] Received {len(self.completed_orders)} completed orders")

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158, 2107, 2119]:  # Ignore common info messages
            print(f"[ERROR] {errorCode}: {errorString}")


class OrderStatusChecker:
    def __init__(self, orders_file: str = "orders.json"):
        import os
        # If relative path, make it relative to data directory
        if not os.path.isabs(orders_file):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.orders_file = os.path.join(project_root, "data", orders_file)
        else:
            self.orders_file = orders_file
        self.orders_data = None
        self.api = None

    def load_orders_json(self):
        """Load orders from JSON file"""
        print(f"[LOAD] Loading orders from {self.orders_file}...")
        with open(self.orders_file, 'r') as f:
            self.orders_data = json.load(f)

        total_orders = self.orders_data['metadata']['total_orders']
        print(f"[OK] Loaded {total_orders} orders from JSON file")
        return self.orders_data

    def connect_to_ibkr(self) -> bool:
        """Connect to IBKR Gateway"""
        print("[CONNECT] Connecting to IB Gateway...")

        # Initialize API client
        self.api = IBOrderStatusChecker()

        # Connect to IB Gateway - use a different client ID to see ALL orders
        client_id = 99  # Use a high client ID to avoid conflicts
        print(f"[DEBUG] Using client ID: {client_id}")
        self.api.connect("127.0.0.1", 4002, clientId=client_id)

        # Start message processing thread
        api_thread = threading.Thread(target=self.api.run, daemon=True)
        api_thread.start()

        # Wait for connection AND next valid order ID (like debug executor)
        timeout = 15
        start_time = time.time()
        while (not self.api.connected) and (time.time() - start_time) < timeout:
            time.sleep(0.1)

        if not self.api.connected:
            print("[ERROR] Failed to connect to IB Gateway")
            return False

        # Extended wait to capture all immediate order callbacks including high order IDs
        print("[DEBUG] Waiting for immediate order callbacks (scanning up to order ID 500+)...")
        time.sleep(10)  # Longer wait to capture orders with higher IDs
        if not self.api.account_id:
            print("[ERROR] No account ID received")
            return False

        # Log immediate orders found during connection phase
        if self.api.open_orders:
            print(f"[DEBUG] Found {len(self.api.open_orders)} orders during connection phase")
            for order_id, order_info in self.api.open_orders.items():
                print(f"[DEBUG]   Order {order_id}: {order_info['symbol']} {order_info['action']} {order_info['quantity']} ({order_info['status']})")
        else:
            print("[DEBUG] No orders found during connection phase")

        return True

    def fetch_account_data(self):
        """Fetch current orders, positions, and executions from IBKR"""
        print(f"[FETCH] Requesting additional account data from IBKR...")
        print(f"[DEBUG] Already have {len(self.api.open_orders)} orders from connection phase")

        # Reset completion flags
        for key in self.api.requests_completed:
            self.api.requests_completed[key] = False

        # Store orders already found during connection
        initial_order_count = len(self.api.open_orders)

        # Request ALL orders using multiple methods to catch everything
        print("[DEBUG] Requesting all orders with reqAllOpenOrders()...")
        self.api.reqAllOpenOrders()  # This gets ALL open orders, not just from current client
        time.sleep(3)

        # Also request open orders from current client
        print("[DEBUG] Requesting client open orders with reqOpenOrders()...")
        self.api.reqOpenOrders()
        time.sleep(3)

        # Request auto open orders (sometimes catches more)
        print("[DEBUG] Requesting auto open orders...")
        self.api.reqAutoOpenOrders(True)  # Request automatic order binding
        time.sleep(3)

        # Request positions
        print("[DEBUG] Requesting positions...")
        self.api.reqPositions()
        time.sleep(2)

        # Request completed orders (recent history)
        print("[DEBUG] Requesting completed orders...")
        self.api.reqCompletedOrders(False)  # False = all orders, True = only API orders
        time.sleep(2)

        # Request executions for today
        print("[DEBUG] Requesting executions...")
        from ibapi.execution import ExecutionFilter
        exec_filter = ExecutionFilter()
        # Get executions from today - use proper format
        today = datetime.now().strftime("%Y%m%d 00:00:00")
        exec_filter.time = today
        self.api.reqExecutions(1, exec_filter)
        time.sleep(2)

        # Extended timeout to capture orders with higher IDs (up to 500+)
        timeout = 20
        start_time = time.time()
        print("[DEBUG] Waiting for additional responses (including high order IDs up to 500+)...")

        while (time.time() - start_time) < timeout:
            time.sleep(3)
            current_time = int(time.time() - start_time)
            if current_time % 6 == 0:
                additional_orders = len(self.api.open_orders) - initial_order_count
                max_order_id = max(self.api.open_orders.keys()) if self.api.open_orders else 0
                print(f"[DEBUG] Current status: Open Orders: {len(self.api.open_orders)} (+{additional_orders} from requests), "
                      f"Completed Orders: {len(self.api.completed_orders)}, "
                      f"Positions: {len(self.api.positions)}, Max Order ID: {max_order_id}")

        # Final status with order ID range
        additional_orders = len(self.api.open_orders) - initial_order_count
        max_order_id = max(self.api.open_orders.keys()) if self.api.open_orders else 0
        min_order_id = min(self.api.open_orders.keys()) if self.api.open_orders else 0
        print(f"[DEBUG] Final counts: Open Orders: {len(self.api.open_orders)} (+{additional_orders} from API requests), "
              f"Completed Orders: {len(self.api.completed_orders)}, "
              f"Positions: {len(self.api.positions)}")
        print(f"[DEBUG] Order ID range: {min_order_id} to {max_order_id} (scanning capacity up to 500+)")

        # Check if all requests completed
        completed = list(self.api.requests_completed.values())
        if not all(completed):
            print(f"[WARNING] Some requests did not complete in time: {self.api.requests_completed}")
        else:
            print("[OK] All account data requests completed")

    def analyze_orders(self):
        """Analyze and compare orders from JSON with current IBKR status"""
        print("\n" + "=" * 80)
        print("ORDER STATUS ANALYSIS")
        print("=" * 80)

        # Create lookup dictionaries
        json_orders_by_symbol = {}
        for order in self.orders_data['orders']:
            symbol = order['symbol']
            json_orders_by_symbol[symbol] = order

        # Combine open orders and completed orders
        all_ibkr_orders = {}

        # Add open orders
        for order_id, order_info in self.api.open_orders.items():
            all_ibkr_orders[order_id] = order_info

        # Add completed orders
        for order_id, order_info in self.api.completed_orders.items():
            all_ibkr_orders[order_id] = order_info

        ibkr_orders_by_symbol = {}
        for order_id, order_info in all_ibkr_orders.items():
            symbol = order_info['symbol']
            if symbol not in ibkr_orders_by_symbol:
                ibkr_orders_by_symbol[symbol] = []
            ibkr_orders_by_symbol[symbol].append(order_info)

        # Analysis counters
        found_in_ibkr = 0
        missing_from_ibkr = 0
        quantity_mismatches = 0

        print(f"\nJSON ORDERS vs IBKR ORDERS:")
        print("-" * 80)
        print(f"{'Symbol':<12} {'JSON Action':<8} {'JSON Qty':<10} {'IBKR Status':<15} {'IBKR Qty':<10} {'Match'}")
        print("-" * 80)

        for symbol, json_order in json_orders_by_symbol.items():
            json_action = json_order['action']
            json_quantity = json_order['quantity']

            # Check if symbol exists in IBKR orders
            if symbol in ibkr_orders_by_symbol:
                found_in_ibkr += 1
                ibkr_orders = ibkr_orders_by_symbol[symbol]

                # Find matching order by action
                matching_order = None
                for ibkr_order in ibkr_orders:
                    if ibkr_order['action'] == json_action:
                        matching_order = ibkr_order
                        break

                if matching_order:
                    ibkr_qty = matching_order['quantity']
                    status = matching_order['status']

                    if ibkr_qty == json_quantity:
                        match_status = "OK"
                    else:
                        match_status = "QTY_DIFF"
                        quantity_mismatches += 1

                    print(f"{symbol:<12} {json_action:<8} {json_quantity:<10} {status:<15} {ibkr_qty:<10} {match_status}")
                else:
                    print(f"{symbol:<12} {json_action:<8} {json_quantity:<10} {'NOT FOUND':<15} {'-':<10} {'MISSING'}")
                    missing_from_ibkr += 1
                    found_in_ibkr -= 1
            else:
                print(f"{symbol:<12} {json_action:<8} {json_quantity:<10} {'NOT FOUND':<15} {'-':<10} {'MISSING'}")
                missing_from_ibkr += 1

        print("-" * 80)
        print(f"SUMMARY:")
        print(f"  Total orders in JSON: {len(json_orders_by_symbol)}")
        print(f"  Found in IBKR: {found_in_ibkr}")
        print(f"  Missing from IBKR: {missing_from_ibkr}")
        print(f"  Quantity mismatches: {quantity_mismatches}")

        # Show additional IBKR orders not in JSON
        extra_ibkr_orders = []
        for symbol, ibkr_orders in ibkr_orders_by_symbol.items():
            if symbol not in json_orders_by_symbol:
                extra_ibkr_orders.extend(ibkr_orders)

        if extra_ibkr_orders:
            print(f"  Extra orders in IBKR (not in JSON): {len(extra_ibkr_orders)}")

    def show_order_status_summary(self):
        """Show detailed order status summary"""
        print("\n" + "=" * 80)
        print("DETAILED ORDER STATUS")
        print("=" * 80)

        # Combine open and completed orders
        all_orders = {}

        # Add open orders
        for order_id, order_info in self.api.open_orders.items():
            all_orders[order_id] = order_info

        # Add completed orders
        for order_id, order_info in self.api.completed_orders.items():
            all_orders[order_id] = order_info

        if not all_orders:
            print("No orders found in IBKR account.")
            return

        # Group orders by status
        status_groups = {}
        for order_id, order_info in all_orders.items():
            status = order_info['status']
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append((order_id, order_info))

        for status, orders in status_groups.items():
            print(f"\n{status.upper()} ORDERS ({len(orders)}):")
            print("-" * 80)
            print(f"{'Order ID':<10} {'Symbol':<12} {'Action':<8} {'Quantity':<10} {'Filled':<8} {'Price':<12}")
            print("-" * 80)

            for order_id, order_info in orders:
                price = order_info.get('avgFillPrice', 'N/A')
                if price and price != 'N/A' and price != '':
                    try:
                        price = f"${float(price):.2f}"
                    except:
                        price = str(price)
                else:
                    price = order_info['orderType']

                filled = order_info.get('filled', 0)

                print(f"{order_id:<10} {order_info['symbol']:<12} {order_info['action']:<8} "
                      f"{order_info['quantity']:<10} {filled:<8} {price:<12}")

    def show_positions(self):
        """Show current positions"""
        print("\n" + "=" * 80)
        print("CURRENT POSITIONS")
        print("=" * 80)

        if not self.api.positions:
            print("No positions found in IBKR account.")
            return

        print(f"{'Symbol':<12} {'Position':<12} {'Avg Cost':<12} {'Currency':<8} {'Market Value'}")
        print("-" * 60)

        total_symbols = 0
        for symbol, pos_info in self.api.positions.items():
            position = pos_info['position']
            avg_cost = pos_info['avgCost']
            currency = pos_info['currency']
            market_value = position * avg_cost

            total_symbols += 1
            print(f"{symbol:<12} {position:<12} {avg_cost:<12.2f} {currency:<8} {market_value:<12.2f}")

        print("-" * 60)
        print(f"Total positions: {total_symbols}")

    def disconnect(self):
        """Disconnect from IBKR"""
        if self.api:
            self.api.disconnect()
            print("[OK] Disconnected from IB Gateway")

    def run_status_check(self):
        """Run the complete order status check"""
        try:
            print("Interactive Brokers Order Status Checker")
            print("=" * 50)

            # Step 1: Load orders from JSON
            self.load_orders_json()

            # Step 2: Connect to IBKR
            if not self.connect_to_ibkr():
                return False

            # Step 3: Fetch current account data
            self.fetch_account_data()

            # Step 4: Analyze orders
            self.analyze_orders()

            # Step 5: Show detailed status
            self.show_order_status_summary()

            # Step 6: Show positions
            self.show_positions()

            # Step 7: Disconnect
            self.disconnect()

            return True

        except Exception as e:
            print(f"[ERROR] Status check failed: {str(e)}")
            if self.api:
                self.disconnect()
            return False


def main():
    """Main function to run order status check"""
    import sys
    import os

    # Create and run status checker
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    orders_file = os.path.join(project_root, "data", "orders.json")
    checker = OrderStatusChecker(orders_file)
    success = checker.run_status_check()

    if success:
        print("\n[SUCCESS] Order status check completed successfully")
    else:
        print("\n[FAILED] Order status check failed")
        sys.exit(1)


if __name__ == "__main__":
    main()