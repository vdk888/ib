"""
Order Execution Service Implementation
Wraps legacy src/order_executor.py with modern service interface
Provides 100% behavioral compatibility with CLI step10_execute_orders()
"""

import os
import sys
import json
import time
import asyncio
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...services.interfaces import IOrderExecutionService
from ...core.exceptions import BaseServiceError


class OrderExecutionError(BaseServiceError):
    """Order execution specific errors"""
    pass


class IBKRConnectionError(OrderExecutionError):
    """IBKR connection specific errors"""
    pass


class OrderExecutionService(IOrderExecutionService):
    """
    Production-ready Order Execution Service
    Implements IOrderExecutionService interface with legacy compatibility
    """

    def __init__(self):
        self.orders_data = None
        self.execution_api = None
        self._project_root = self._get_project_root()

    def _get_project_root(self) -> str:
        """Get project root directory for data file access"""
        # Navigate up from backend/app/services/implementations to project root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up 4 levels: implementations -> services -> app -> backend -> project_root
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))

    async def load_orders(self, orders_file: str = "orders.json") -> Dict[str, Any]:
        """
        Load orders from JSON file in data directory
        Maintains exact compatibility with legacy load_orders() method
        """
        try:
            # Resolve orders file path relative to backend/data
            if not os.path.isabs(orders_file):
                orders_path = os.path.join(self._project_root, "backend", "data", orders_file)
            else:
                orders_path = orders_file

            print(f"[LOAD] Loading orders from {orders_path}...")
            print(f"[DEBUG] Working directory: {os.getcwd()}")
            print(f"[DEBUG] Orders file exists: {os.path.exists(orders_path)}")

            if not os.path.exists(orders_path):
                raise FileNotFoundError(f"Orders file not found: {orders_path}")

            with open(orders_path, 'r') as f:
                self.orders_data = json.load(f)

            # Extract and validate metadata
            if 'metadata' not in self.orders_data:
                raise ValueError("Invalid orders file format: missing metadata")
            if 'orders' not in self.orders_data:
                raise ValueError("Invalid orders file format: missing orders")

            metadata = self.orders_data['metadata']
            total_orders = metadata['total_orders']
            buy_orders = metadata['buy_orders']
            sell_orders = metadata['sell_orders']

            print(f"[OK] Loaded {total_orders} orders ({sell_orders} SELL, {buy_orders} BUY)")

            return {
                'success': True,
                'metadata': metadata,
                'orders': self.orders_data['orders'],
                'total_orders': total_orders
            }

        except FileNotFoundError as e:
            error_msg = f"Orders file not found: {str(e)}"
            print(f"[ERROR] {error_msg}")
            raise OrderExecutionError(
                message=error_msg,
                error_code="ORDERS_FILE_NOT_FOUND"
            )
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON format in orders file: {str(e)}"
            print(f"[ERROR] {error_msg}")
            raise OrderExecutionError(
                message=error_msg,
                error_code="INVALID_ORDERS_FORMAT"
            )
        except Exception as e:
            error_msg = f"Failed to load orders: {str(e)}"
            print(f"[ERROR] {error_msg}")
            raise OrderExecutionError(
                message=error_msg,
                error_code="ORDERS_LOAD_FAILED",
                details={"exception": str(e)}
            )

    async def connect_to_ibkr(
        self,
        host: str = "127.0.0.1",
        port: int = 4002,
        client_id: int = 20,
        timeout: int = 15
    ) -> bool:
        """
        Establish connection to IBKR Gateway/TWS
        Wraps legacy connection logic with modern async interface
        """
        try:
            print("[CONNECT] Connecting to IB Gateway...")

            # Import legacy order executor here to avoid global dependencies
            from ...services.implementations.legacy.order_executor import IBOrderExecutor

            # Initialize API client
            self.execution_api = IBOrderExecutor()

            # Connect to IB Gateway
            self.execution_api.connect(host, port, clientId=client_id)

            # Start message processing thread
            api_thread = threading.Thread(target=self.execution_api.run, daemon=True)
            api_thread.start()

            # Wait for connection and next valid order ID
            start_time = time.time()
            while (self.execution_api.nextorderId is None or not self.execution_api.connected) and (time.time() - start_time) < timeout:
                await asyncio.sleep(0.1)

            if self.execution_api.nextorderId is None or not self.execution_api.connected:
                error_msg = "Failed to connect to IB Gateway or get valid order ID"
                print(f"[ERROR] {error_msg}")
                raise IBKRConnectionError(
                    message=error_msg,
                    error_code="IBKR_CONNECTION_FAILED"
                )

            # Wait for account ID
            await asyncio.sleep(2.0)
            if not self.execution_api.account_id:
                error_msg = "No account ID received"
                print(f"[ERROR] {error_msg}")
                raise IBKRConnectionError(
                    message=error_msg,
                    error_code="IBKR_ACCOUNT_ID_MISSING"
                )

            print(f"[OK] Connected to IBKR - Account: {self.execution_api.account_id}, Next Order ID: {self.execution_api.nextorderId}")
            return True

        except IBKRConnectionError:
            # Re-raise IBKR specific errors
            raise
        except Exception as e:
            error_msg = f"Unexpected error connecting to IBKR: {str(e)}"
            print(f"[ERROR] {error_msg}")
            raise IBKRConnectionError(
                message=error_msg,
                error_code="IBKR_CONNECTION_UNEXPECTED_ERROR",
                details={"exception": str(e)}
            )

    async def execute_orders(
        self,
        max_orders: Optional[int] = None,
        delay_between_orders: float = 1.0,
        order_type: str = "GTC_MKT"
    ) -> Dict[str, Any]:
        """
        Execute loaded orders through IBKR API
        Maintains exact execution logic and console output from legacy implementation
        """
        if not self.orders_data:
            raise OrderExecutionError(
                message="No orders loaded - call load_orders() first",
                error_code="NO_ORDERS_LOADED"
            )

        if not self.execution_api:
            raise OrderExecutionError(
                message="Not connected to IBKR - call connect_to_ibkr() first",
                error_code="IBKR_NOT_CONNECTED"
            )

        try:
            orders_to_execute = self.orders_data['orders']
            if max_orders:
                orders_to_execute = orders_to_execute[:max_orders]
                print(f"[INFO] Limiting execution to first {max_orders} orders")

            print(f"[EXECUTE] Starting execution of {len(orders_to_execute)} orders")
            print(f"[EXECUTE] Using order type: {order_type}")
            print("=" * 60)

            executed_count = 0
            failed_count = 0
            order_results = []

            for i, order_data in enumerate(orders_to_execute, 1):
                try:
                    symbol = order_data['symbol']
                    action = order_data['action']
                    quantity = order_data['quantity']

                    print(f"\n[{i:3d}/{len(orders_to_execute)}] {action} {quantity:,} {symbol}")

                    # Currency-based order type selection (exact legacy logic)
                    currency = order_data['stock_info']['currency']
                    if currency == 'USD':
                        selected_order_type = "MOO" if order_type == "MOO" else order_type
                    else:
                        selected_order_type = "GTC_MKT"

                    print(f"    Currency: {currency}, Selected order type: {selected_order_type}")

                    # Create contract and order using legacy methods
                    contract_params = self.create_ibkr_contract(order_data)
                    order_params = self.create_ibkr_order(action, quantity, selected_order_type)

                    # Submit order through legacy API
                    order_id = self.execution_api.nextorderId

                    # Use legacy contract and order creation
                    from ...services.implementations.legacy.order_executor import OrderExecutor
                    legacy_executor = OrderExecutor()
                    contract = legacy_executor.create_contract_from_order(order_data)
                    market_order = legacy_executor.create_market_order(action, quantity, selected_order_type)

                    self.execution_api.placeOrder(order_id, contract, market_order)
                    self.execution_api.nextorderId += 1

                    # Wait for order acknowledgment
                    await asyncio.sleep(0.5)

                    # Check order status
                    if order_id in self.execution_api.orders_status:
                        status = self.execution_api.orders_status[order_id]['status']
                        print(f"    Order ID {order_id}: {status}")
                    else:
                        print(f"    Order ID {order_id}: Submitted (status pending)")

                    order_results.append({
                        'order_id': order_id,
                        'symbol': symbol,
                        'action': action,
                        'quantity': quantity,
                        'order_type': selected_order_type,
                        'status': 'submitted',
                        'submission_time': datetime.utcnow().isoformat()
                    })
                    executed_count += 1

                    # Rate limiting between orders
                    if i < len(orders_to_execute):
                        await asyncio.sleep(delay_between_orders)

                except Exception as e:
                    print(f"    [ERROR] Failed to execute order: {str(e)}")
                    order_results.append({
                        'symbol': order_data.get('symbol', 'unknown'),
                        'action': order_data.get('action', 'unknown'),
                        'quantity': order_data.get('quantity', 0),
                        'status': 'failed',
                        'error': str(e)
                    })
                    failed_count += 1
                    continue

            print("\n" + "=" * 60)
            print(f"[SUMMARY] Execution complete:")
            print(f"  Executed: {executed_count}")
            print(f"  Failed: {failed_count}")
            print(f"  Total: {len(orders_to_execute)}")

            return {
                'success': True,
                'executed_count': executed_count,
                'failed_count': failed_count,
                'total_orders': len(orders_to_execute),
                'order_statuses': dict(self.execution_api.orders_status),
                'order_results': order_results,
                'execution_summary': {
                    'total_processed': len(orders_to_execute),
                    'successful_submissions': executed_count,
                    'failed_submissions': failed_count,
                    'success_rate': executed_count / len(orders_to_execute) if orders_to_execute else 0
                }
            }

        except Exception as e:
            error_msg = f"Order execution failed: {str(e)}"
            print(f"[ERROR] {error_msg}")
            raise OrderExecutionError(
                message=error_msg,
                error_code="ORDER_EXECUTION_FAILED",
                details={"exception": str(e)}
            )

    async def get_order_statuses(self, wait_time: int = 30) -> Dict[str, Any]:
        """
        Get current status of all submitted orders
        Replicates exact legacy status checking behavior
        """
        if not self.execution_api:
            raise OrderExecutionError(
                message="Not connected to IBKR - call connect_to_ibkr() first",
                error_code="IBKR_NOT_CONNECTED"
            )

        try:
            print(f"\n[WAIT] Waiting {wait_time} seconds for order status updates...")
            await asyncio.sleep(wait_time)

            print(f"\n[STATUS] Order Status Summary:")
            print("-" * 50)

            status_counts = {}
            total_filled = 0
            total_pending = 0
            order_details = {}

            for order_id, status_info in self.execution_api.orders_status.items():
                status = status_info['status']
                filled = status_info['filled']

                status_counts[status] = status_counts.get(status, 0) + 1
                order_details[order_id] = status_info.copy()

                if status == 'Filled':
                    total_filled += filled
                elif status in ['PreSubmitted', 'Submitted']:
                    total_pending += 1

            # Print status summary (exact legacy format)
            for status, count in status_counts.items():
                print(f"  {status}: {count} orders")

            print(f"\nTotal shares filled: {total_filled:,}")
            print(f"Orders still pending: {total_pending}")

            return {
                'success': True,
                'status_summary': status_counts,
                'total_filled_shares': total_filled,
                'pending_orders_count': total_pending,
                'order_details': order_details,
                'wait_time_used': wait_time
            }

        except Exception as e:
            error_msg = f"Failed to get order statuses: {str(e)}"
            print(f"[ERROR] {error_msg}")
            raise OrderExecutionError(
                message=error_msg,
                error_code="ORDER_STATUS_CHECK_FAILED",
                details={"exception": str(e)}
            )

    async def disconnect(self) -> None:
        """
        Disconnect from IBKR Gateway/TWS
        """
        try:
            if self.execution_api:
                self.execution_api.disconnect()
                print("[OK] Disconnected from IB Gateway")
                self.execution_api = None
        except Exception as e:
            print(f"[WARNING] Error during disconnect: {str(e)}")

    async def run_execution(
        self,
        orders_file: str = "orders.json",
        max_orders: Optional[int] = None,
        delay_between_orders: float = 1.0,
        order_type: str = "GTC_MKT"
    ) -> Dict[str, Any]:
        """
        Complete order execution workflow
        Replicates exact behavior of legacy main() function
        """
        try:
            print("Interactive Brokers Order Execution Service")
            print("=" * 50)

            # Step 1: Load orders
            orders_result = await self.load_orders(orders_file)

            # Step 2: Connect to IBKR
            connected = await self.connect_to_ibkr()
            if not connected:
                return {
                    'success': False,
                    'error_message': 'Failed to connect to IBKR',
                    'execution_summary': None,
                    'order_statuses': None
                }

            # Step 3: Execute orders
            execution_result = await self.execute_orders(max_orders, delay_between_orders, order_type)

            # Step 4: Wait for status updates
            status_result = await self.get_order_statuses()

            # Step 5: Disconnect
            await self.disconnect()

            return {
                'success': True,
                'execution_summary': execution_result['execution_summary'],
                'order_statuses': status_result['order_details'],
                'status_summary': status_result['status_summary'],
                'total_filled_shares': status_result['total_filled_shares'],
                'pending_orders_count': status_result['pending_orders_count'],
                'orders_loaded': orders_result['total_orders'],
                'workflow_completed_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            # Ensure cleanup on failure
            await self.disconnect()

            error_msg = f"Order execution workflow failed: {str(e)}"
            print(f"[ERROR] {error_msg}")

            return {
                'success': False,
                'error_message': error_msg,
                'execution_summary': None,
                'order_statuses': None,
                'failure_time': datetime.utcnow().isoformat()
            }

    def create_ibkr_contract(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create IBKR contract specification from order data
        Returns dict representation for API usage (not actual Contract object)
        """
        ibkr_details = order_data['ibkr_details']
        stock_currency = order_data['stock_info']['currency']

        return {
            'symbol': ibkr_details['symbol'],
            'secType': 'STK',
            'exchange': ibkr_details.get('exchange', 'SMART'),
            'primaryExchange': ibkr_details.get('primaryExchange', ''),
            'currency': stock_currency,
            'conId': ibkr_details.get('conId', None)
        }

    def create_ibkr_order(
        self,
        action: str,
        quantity: int,
        order_type: str = "GTC_MKT"
    ) -> Dict[str, Any]:
        """
        Create IBKR order specification
        Returns dict representation for API usage (not actual Order object)
        """
        order_config = {
            'action': action,
            'totalQuantity': quantity,
            'eTradeOnly': False,
            'firmQuoteOnly': False
        }

        if order_type == "MOO":
            order_config.update({
                'orderType': 'MKT',
                'tif': 'OPG'  # Time in Force: At the Opening
            })
        elif order_type == "GTC_MKT":
            order_config.update({
                'orderType': 'MKT',
                'tif': 'GTC'  # Good Till Cancelled
            })
        elif order_type == "DAY":
            order_config.update({
                'orderType': 'MKT',
                'tif': 'DAY'
            })
        else:  # Default MKT
            order_config.update({
                'orderType': 'MKT'
            })

        return order_config