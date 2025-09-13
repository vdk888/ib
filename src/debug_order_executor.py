#!/usr/bin/env python3
"""
Debug Order Executor for Interactive Brokers
Enhanced version with detailed logging to identify order submission failures
"""

import json
import time
import threading
from typing import Dict, List, Optional

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order


class DebugIBOrderExecutor(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connected = False
        self.nextorderId = None
        self.account_id = None

        # Enhanced order tracking
        self.orders_status = {}  # orderId -> status info
        self.orders_submitted = []  # List of successfully submitted order IDs
        self.orders_failed = []    # List of failed orders with reasons
        self.contract_requests = {}  # Track contract resolution requests

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
        self.nextorderId = orderId
        print(f"[OK] Next valid order ID: {self.nextorderId}")

    def managedAccounts(self, accountsList: str):
        super().managedAccounts(accountsList)
        accounts = accountsList.split(",")
        self.account_id = accounts[0]
        print(f"[OK] Account ID: {self.account_id}")

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print(f"[STATUS] Order {orderId}: {status}, Filled: {filled}, Remaining: {remaining}, Avg Price: ${avgFillPrice:.2f}")
        if whyHeld:
            print(f"[STATUS]   Why held: {whyHeld}")
        self.orders_status[orderId] = {
            'status': status,
            'filled': filled,
            'remaining': remaining,
            'avgFillPrice': avgFillPrice,
            'permId': permId,
            'whyHeld': whyHeld
        }

    def openOrder(self, orderId, contract, order, orderState):
        print(f"[OPEN] Order {orderId}: {contract.symbol}, {order.action} {order.totalQuantity}, Status: {orderState.status}")

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode in [2104, 2106, 2158, 2107]:  # Ignore common info messages
            return

        # Log all other errors
        print(f"[ERROR] ReqId: {reqId}, Code: {errorCode}, Message: {errorString}")

        # Track order-related errors
        if reqId in self.contract_requests:
            symbol = self.contract_requests[reqId]
            self.orders_failed.append({
                'symbol': symbol,
                'error_code': errorCode,
                'error_message': errorString,
                'request_id': reqId
            })
            print(f"[ERROR] Contract request for {symbol} failed: {errorString}")


class DebugOrderExecutor:
    def __init__(self, orders_file: str = "orders.json"):
        import os
        if not os.path.isabs(orders_file):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.orders_file = os.path.join(project_root, "data", orders_file)
        else:
            self.orders_file = orders_file
        self.orders_data = None
        self.api = None

    def load_orders(self):
        """Load orders from JSON file"""
        print(f"[LOAD] Loading orders from {self.orders_file}...")
        with open(self.orders_file, 'r') as f:
            self.orders_data = json.load(f)

        total_orders = self.orders_data['metadata']['total_orders']
        buy_orders = self.orders_data['metadata']['buy_orders']
        sell_orders = self.orders_data['metadata']['sell_orders']

        print(f"[OK] Loaded {total_orders} orders ({sell_orders} SELL, {buy_orders} BUY)")

    def create_contract_from_order(self, order_data: dict) -> Contract:
        """Create IBKR Contract from order data with enhanced logging"""
        contract = Contract()
        ibkr_details = order_data['ibkr_details']
        symbol = order_data['symbol']

        print(f"[CONTRACT] Creating contract for {symbol}")
        print(f"[CONTRACT]   IBKR Symbol: {ibkr_details['symbol']}")
        print(f"[CONTRACT]   Exchange: {ibkr_details.get('exchange', 'SMART')}")
        print(f"[CONTRACT]   Primary Exchange: {ibkr_details.get('primaryExchange', '')}")

        contract.symbol = ibkr_details['symbol']
        contract.secType = "STK"
        contract.exchange = ibkr_details.get('exchange', 'SMART')
        contract.primaryExchange = ibkr_details.get('primaryExchange', '')

        # Set currency based on stock info
        stock_currency = order_data['stock_info']['currency']
        contract.currency = stock_currency
        print(f"[CONTRACT]   Currency: {stock_currency}")

        # Use conId if available for precise identification
        if 'conId' in ibkr_details and ibkr_details['conId']:
            contract.conId = ibkr_details['conId']
            print(f"[CONTRACT]   ConId: {ibkr_details['conId']}")
        else:
            print(f"[CONTRACT]   No ConId available")

        return contract

    def create_market_order(self, action: str, quantity: int) -> Order:
        """Create a market order with enhanced logging"""
        order = Order()
        order.action = action
        order.orderType = "MKT"
        order.totalQuantity = quantity
        order.eTradeOnly = False
        order.firmQuoteOnly = False

        print(f"[ORDER] Created {action} order for {quantity} shares")
        return order

    def connect_to_ibkr(self) -> bool:
        """Connect to IBKR Gateway"""
        print("[CONNECT] Connecting to IB Gateway...")

        # Initialize API client
        self.api = DebugIBOrderExecutor()

        # Connect to IB Gateway (paper trading port 4002)
        self.api.connect("127.0.0.1", 4002, clientId=22)  # Different client ID

        # Start message processing thread
        api_thread = threading.Thread(target=self.api.run, daemon=True)
        api_thread.start()

        # Wait for connection and next valid order ID
        timeout = 15
        start_time = time.time()
        while (self.api.nextorderId is None or not self.api.connected) and (time.time() - start_time) < timeout:
            time.sleep(0.1)

        if self.api.nextorderId is None or not self.api.connected:
            print("[ERROR] Failed to connect to IB Gateway or get valid order ID")
            return False

        # Wait for account ID
        time.sleep(2)
        if not self.api.account_id:
            print("[ERROR] No account ID received")
            return False

        return True

    def execute_orders_with_detailed_logging(self, start_index: int = 0, max_orders: Optional[int] = None, delay_between_orders: float = 2.0):
        """Execute orders with detailed logging for each step"""
        if not self.orders_data:
            print("[ERROR] No orders loaded")
            return

        orders_to_execute = self.orders_data['orders'][start_index:]
        if max_orders:
            orders_to_execute = orders_to_execute[:max_orders]

        print(f"[EXECUTE] Starting execution of {len(orders_to_execute)} orders (from index {start_index})")
        print(f"[EXECUTE] Using {delay_between_orders} second delay between orders")
        print("=" * 80)

        executed_count = 0
        failed_count = 0

        for i, order_data in enumerate(orders_to_execute):
            order_index = start_index + i
            try:
                symbol = order_data['symbol']
                action = order_data['action']
                quantity = order_data['quantity']

                print(f"\n[{order_index + 1:3d}/{len(self.orders_data['orders'])}] Processing: {action} {quantity:,} {symbol}")
                print("-" * 60)

                # Step 1: Create contract
                print("[STEP 1] Creating contract...")
                contract = self.create_contract_from_order(order_data)
                print("[STEP 1] Contract created successfully")

                # Step 2: Create order
                print("[STEP 2] Creating order...")
                market_order = self.create_market_order(action, quantity)
                print("[STEP 2] Order created successfully")

                # Step 3: Submit order
                print("[STEP 3] Submitting order to IBKR...")
                order_id = self.api.nextorderId
                print(f"[STEP 3] Using Order ID: {order_id}")

                # Track this contract request
                self.api.contract_requests[order_id] = symbol

                # Place order
                self.api.placeOrder(order_id, contract, market_order)
                self.api.nextorderId += 1

                # Wait for order acknowledgment
                print("[STEP 4] Waiting for order acknowledgment...")
                wait_time = 3.0  # Longer wait for debugging
                time.sleep(wait_time)

                # Check results
                if order_id in self.api.orders_status:
                    status = self.api.orders_status[order_id]['status']
                    why_held = self.api.orders_status[order_id].get('whyHeld', '')
                    print(f"[STEP 4] ✓ Order acknowledged - Status: {status}")
                    if why_held:
                        print(f"[STEP 4]   Why held: {why_held}")
                    self.api.orders_submitted.append(order_id)
                    executed_count += 1
                else:
                    print(f"[STEP 4] ⚠ Order acknowledgment not received within {wait_time}s")
                    print(f"[STEP 4]   Order may still be processing...")
                    executed_count += 1

                # Check for errors
                failed_orders = [f for f in self.api.orders_failed if f['symbol'] == symbol]
                if failed_orders:
                    print(f"[STEP 4] ✗ Order failed: {failed_orders[-1]['error_message']}")
                    failed_count += 1
                    executed_count -= 1

                print(f"[RESULT] Order {order_index + 1}: {'SUCCESS' if not failed_orders else 'FAILED'}")

                # Add delay between orders
                if i < len(orders_to_execute) - 1:  # Don't delay after last order
                    print(f"[DELAY] Waiting {delay_between_orders}s before next order...")
                    time.sleep(delay_between_orders)

            except Exception as e:
                print(f"[EXCEPTION] Failed to process order {order_index + 1}: {str(e)}")
                import traceback
                traceback.print_exc()
                failed_count += 1
                continue

        print("\n" + "=" * 80)
        print(f"[SUMMARY] Execution complete:")
        print(f"  Successfully submitted: {executed_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Total processed: {len(orders_to_execute)}")
        print(f"  API errors logged: {len(self.api.orders_failed)}")

        # Show failed orders
        if self.api.orders_failed:
            print(f"\n[FAILED ORDERS]:")
            for failed_order in self.api.orders_failed:
                print(f"  {failed_order['symbol']}: {failed_order['error_message']}")

    def disconnect(self):
        """Disconnect from IBKR"""
        if self.api:
            self.api.disconnect()
            print("[OK] Disconnected from IB Gateway")


def main():
    """Main function for debug order execution"""
    import sys

    print("DEBUG Interactive Brokers Order Executor")
    print("=" * 60)

    # Parse command line arguments
    start_index = 0
    max_orders = None
    delay = 2.0

    if len(sys.argv) > 1:
        try:
            start_index = int(sys.argv[1])
            print(f"[INFO] Starting from order index {start_index}")
        except ValueError:
            print(f"[WARNING] Invalid start_index argument: {sys.argv[1]}")

    if len(sys.argv) > 2:
        try:
            max_orders = int(sys.argv[2])
            print(f"[INFO] Will execute maximum {max_orders} orders")
        except ValueError:
            print(f"[WARNING] Invalid max_orders argument: {sys.argv[2]}")

    if len(sys.argv) > 3:
        try:
            delay = float(sys.argv[3])
            print(f"[INFO] Using {delay} second delay between orders")
        except ValueError:
            print(f"[WARNING] Invalid delay argument: {sys.argv[3]}")

    # Create and run debug executor
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    orders_file = os.path.join(project_root, "data", "orders.json")
    executor = DebugOrderExecutor(orders_file)

    try:
        # Load orders
        executor.load_orders()

        # Connect to IBKR
        if not executor.connect_to_ibkr():
            sys.exit(1)

        # Execute orders with detailed logging
        executor.execute_orders_with_detailed_logging(start_index, max_orders, delay)

        # Disconnect
        executor.disconnect()

        print("\n[SUCCESS] Debug order execution completed")

    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Execution interrupted by user")
        if executor.api:
            executor.disconnect()
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAILED] Debug execution failed: {str(e)}")
        if executor.api:
            executor.disconnect()
        sys.exit(1)


if __name__ == "__main__":
    main()