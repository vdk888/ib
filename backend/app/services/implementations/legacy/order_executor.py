#!/usr/bin/env python3
"""
Order Executor for Interactive Brokers
Reads orders from orders.json and executes them through IBKR API
"""

import json
import time
import threading
from typing import Dict, List, Optional

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order


class IBOrderExecutor(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connected = False
        self.nextorderId = None
        self.account_id = None
        
        # Order tracking
        self.orders_status = {}  # orderId -> status info
        self.executed_orders = []
        self.failed_orders = []
        
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
        self.orders_status[orderId] = {
            'status': status,
            'filled': filled,
            'remaining': remaining,
            'avgFillPrice': avgFillPrice,
            'permId': permId
        }
        
    def openOrder(self, orderId, contract, order, orderState):
        print(f"[OPEN] Order {orderId}: {contract.symbol}, {order.action} {order.totalQuantity}, Status: {orderState.status}")
        
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158, 2107]:  # Ignore common info messages
            print(f"[ERROR] {errorCode}: {errorString}")


class OrderExecutor:
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
        
    def load_orders(self):
        """Load orders from JSON file"""
        import os
        print(f"[LOAD] Loading orders from {self.orders_file}...")
        print(f"[DEBUG] Working directory: {os.getcwd()}")
        print(f"[DEBUG] Orders file exists: {os.path.exists(self.orders_file)}")
        with open(self.orders_file, 'r') as f:
            self.orders_data = json.load(f)
            
        total_orders = self.orders_data['metadata']['total_orders']
        buy_orders = self.orders_data['metadata']['buy_orders']
        sell_orders = self.orders_data['metadata']['sell_orders']
        
        print(f"[OK] Loaded {total_orders} orders ({sell_orders} SELL, {buy_orders} BUY)")
        
    def create_contract_from_order(self, order_data: dict) -> Contract:
        """Create IBKR Contract from order data"""
        contract = Contract()
        ibkr_details = order_data['ibkr_details']
        
        contract.symbol = ibkr_details['symbol']
        contract.secType = "STK"
        contract.exchange = ibkr_details.get('exchange', 'SMART')
        contract.primaryExchange = ibkr_details.get('primaryExchange', '')
        
        # Set currency based on stock info
        stock_currency = order_data['stock_info']['currency']
        contract.currency = stock_currency
        
        # Use conId if available for precise identification
        if 'conId' in ibkr_details and ibkr_details['conId']:
            contract.conId = ibkr_details['conId']
            
        return contract
        
    def create_market_order(self, action: str, quantity: int, order_type: str = "MKT") -> Order:
        """Create a market order with configurable order type for different market sessions"""
        order = Order()
        order.action = action
        order.totalQuantity = quantity
        order.eTradeOnly = False
        order.firmQuoteOnly = False

        if order_type == "MOO":
            # Market on Open - executes at opening price
            order.orderType = "MKT"
            order.tif = "OPG"  # Time in Force: At the Opening
            print(f"    Order type: Market on Open (MOO)")
        elif order_type == "GTC_MKT":
            # Good Till Cancelled Market order - stays active until market opens
            order.orderType = "MKT"
            order.tif = "GTC"  # Good Till Cancelled
            print(f"    Order type: Good Till Cancelled Market (GTC)")
        elif order_type == "DAY":
            # Day order - expires at end of trading day
            order.orderType = "MKT"
            order.tif = "DAY"
            print(f"    Order type: Day Market")
        else:
            # Default market order
            order.orderType = "MKT"
            print(f"    Order type: Market")

        return order
        
    def connect_to_ibkr(self) -> bool:
        """Connect to IBKR Gateway"""
        print("[CONNECT] Connecting to IB Gateway...")
        
        # Initialize API client
        self.api = IBOrderExecutor()
        
        # Connect to IB Gateway (paper trading port 4002)
        self.api.connect("127.0.0.1", 4002, clientId=20)
        
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
        
    def execute_orders(self, max_orders: Optional[int] = None, delay_between_orders: float = 1.0, order_type: str = "GTC_MKT"):
        """Execute orders from the JSON file with configurable order type"""
        if not self.orders_data:
            print("[ERROR] No orders loaded")
            return

        orders_to_execute = self.orders_data['orders']
        if max_orders:
            orders_to_execute = orders_to_execute[:max_orders]
            print(f"[INFO] Limiting execution to first {max_orders} orders")

        print(f"[EXECUTE] Starting execution of {len(orders_to_execute)} orders")
        print(f"[EXECUTE] Using order type: {order_type}")
        print("=" * 60)

        executed_count = 0
        failed_count = 0

        for i, order_data in enumerate(orders_to_execute, 1):
            try:
                symbol = order_data['symbol']
                action = order_data['action']
                quantity = order_data['quantity']

                print(f"\n[{i:3d}/{len(orders_to_execute)}] {action} {quantity:,} {symbol}")

                # Determine best order type based on market/currency
                currency = order_data['stock_info']['currency']
                if currency == 'USD':
                    # US stocks - can use MOO for market open execution
                    selected_order_type = "MOO" if order_type == "MOO" else order_type
                else:
                    # International stocks - use GTC to stay active until market opens
                    selected_order_type = "GTC_MKT"

                print(f"    Currency: {currency}, Selected order type: {selected_order_type}")

                # Create contract and order
                contract = self.create_contract_from_order(order_data)
                market_order = self.create_market_order(action, quantity, selected_order_type)

                # Place order
                order_id = self.api.nextorderId
                self.api.placeOrder(order_id, contract, market_order)
                self.api.nextorderId += 1
                
                # Wait briefly for order acknowledgment
                time.sleep(0.5)
                
                # Check if order was accepted
                if order_id in self.api.orders_status:
                    status = self.api.orders_status[order_id]['status']
                    print(f"    Order ID {order_id}: {status}")
                    executed_count += 1
                else:
                    print(f"    Order ID {order_id}: Submitted (status pending)")
                    executed_count += 1
                
                # Add delay between orders to avoid overwhelming the API
                if i < len(orders_to_execute):  # Don't delay after last order
                    time.sleep(delay_between_orders)
                    
            except Exception as e:
                print(f"    [ERROR] Failed to execute order: {str(e)}")
                failed_count += 1
                continue
                
        print("\n" + "=" * 60)
        print(f"[SUMMARY] Execution complete:")
        print(f"  Executed: {executed_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Total: {len(orders_to_execute)}")
        
    def wait_for_order_status(self, wait_time: int = 30):
        """Wait for order status updates"""
        print(f"\n[WAIT] Waiting {wait_time} seconds for order status updates...")
        time.sleep(wait_time)
        
        print(f"\n[STATUS] Order Status Summary:")
        print("-" * 50)
        
        status_counts = {}
        total_filled = 0
        total_pending = 0
        
        for order_id, status_info in self.api.orders_status.items():
            status = status_info['status']
            filled = status_info['filled']
            
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if status == 'Filled':
                total_filled += filled
            elif status in ['PreSubmitted', 'Submitted']:
                total_pending += 1
                
        for status, count in status_counts.items():
            print(f"  {status}: {count} orders")
            
        print(f"\nTotal shares filled: {total_filled:,}")
        print(f"Orders still pending: {total_pending}")
        
    def disconnect(self):
        """Disconnect from IBKR"""
        if self.api:
            self.api.disconnect()
            print("[OK] Disconnected from IB Gateway")
            
    def run_execution(self, max_orders: Optional[int] = None, delay_between_orders: float = 1.0, order_type: str = "GTC_MKT"):
        """Run the complete order execution process"""
        try:
            # Step 1: Load orders
            self.load_orders()

            # Step 2: Connect to IBKR
            if not self.connect_to_ibkr():
                return False

            # Step 3: Execute orders with specified order type
            self.execute_orders(max_orders, delay_between_orders, order_type)

            # Step 4: Wait for status updates
            self.wait_for_order_status()

            # Step 5: Disconnect
            self.disconnect()

            return True
            
        except Exception as e:
            print(f"[ERROR] Execution failed: {str(e)}")
            if self.api:
                self.disconnect()
            return False


def main():
    """Main function to run order execution"""
    import sys
    
    print("Interactive Brokers Order Executor")
    print("=" * 50)
    
    # Parse command line arguments
    max_orders = None
    delay = 1.0
    order_type = "GTC_MKT"  # Default to Good Till Cancelled for Sunday night execution

    if len(sys.argv) > 1:
        try:
            max_orders = int(sys.argv[1])
            print(f"[INFO] Will execute maximum {max_orders} orders")
        except ValueError:
            print(f"[WARNING] Invalid max_orders argument: {sys.argv[1]}")

    if len(sys.argv) > 2:
        try:
            delay = float(sys.argv[2])
            print(f"[INFO] Using {delay} second delay between orders")
        except ValueError:
            print(f"[WARNING] Invalid delay argument: {sys.argv[2]}")

    if len(sys.argv) > 3:
        order_type = sys.argv[3].upper()
        if order_type not in ["MKT", "GTC_MKT", "MOO", "DAY"]:
            print(f"[WARNING] Invalid order type: {order_type}, using default GTC_MKT")
            order_type = "GTC_MKT"
        else:
            print(f"[INFO] Using order type: {order_type}")

    print(f"[INFO] Order Type: {order_type}")
    if order_type == "GTC_MKT":
        print("[INFO] GTC orders will stay active until markets open - perfect for Sunday night execution!")
    elif order_type == "MOO":
        print("[INFO] Market on Open orders will execute at opening bell")

    # Create and run executor
    import os
    # Default to orders.json in data directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    orders_file = os.path.join(project_root, "data", "orders.json")
    executor = OrderExecutor(orders_file)
    success = executor.run_execution(max_orders, delay, order_type)
    
    if success:
        print("\n[SUCCESS] Order execution completed successfully")
    else:
        print("\n[FAILED] Order execution failed")
        sys.exit(1)


if __name__ == "__main__":
    main()