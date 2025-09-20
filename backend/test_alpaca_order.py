"""
Test script for Alpaca order execution with minimal order.
"""

import logging
from app.services.implementations.legacy.alpaca_utils.order_executor import AlpacaOrderExecutor

logging.basicConfig(level=logging.INFO)

try:
    print("=== Testing Real Alpaca Order Execution ===")

    # Initialize executor
    executor = AlpacaOrderExecutor(paper=True)

    # Test with a very small fractional share order
    test_symbol = "SPY"
    test_qty = 0.01  # $60+ for SPY, so about $0.60 order

    print(f"\nPlacing small test buy order: {test_qty} shares of {test_symbol}")

    # Place buy order (fractional orders must use DAY time in force)
    buy_order = executor.buy_market_order(symbol=test_symbol, qty=test_qty, time_in_force="DAY")
    print(f"SUCCESS: Buy order placed successfully!")
    print(f"Order ID: {buy_order['order_id']}")
    print(f"Symbol: {buy_order['symbol']}")
    print(f"Side: {buy_order['side']}")
    print(f"Quantity: {buy_order['qty']}")
    print(f"Status: {buy_order['status']}")

    # Check order status
    print(f"\nChecking order status...")
    order_status = executor.get_order_status(buy_order['order_id'])
    print(f"Current status: {order_status['status']}")
    print(f"Filled quantity: {order_status['filled_qty']}")

    if order_status['is_filled']:
        print(f"SUCCESS: Order filled at ${order_status['filled_avg_price']}")
    elif order_status['is_pending']:
        print(f"PENDING: Order is pending execution")

    # Check open orders
    print(f"\nChecking open orders...")
    open_orders = executor.get_open_orders()
    print(f"Found {len(open_orders)} open orders")

except Exception as e:
    print(f"ERROR: {e}")