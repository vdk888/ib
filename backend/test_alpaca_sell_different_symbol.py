"""
Test script for Alpaca sell order execution with a different symbol.
"""

import logging
from app.services.implementations.legacy.alpaca_utils.order_executor import AlpacaOrderExecutor

logging.basicConfig(level=logging.INFO)

try:
    print("=== Testing Alpaca Sell Order Execution (Different Symbol) ===")

    # Initialize executor
    executor = AlpacaOrderExecutor(paper=True)

    # Use a different symbol to avoid wash trade detection
    test_symbol = "QQQ"  # Different from SPY
    test_qty = 0.01  # Small fractional share for testing

    print(f"\nPlacing small test sell order: {test_qty} shares of {test_symbol}")

    # Place sell order (fractional orders must use DAY time in force)
    sell_order = executor.sell_market_order(symbol=test_symbol, qty=test_qty, time_in_force="DAY")
    print(f"SUCCESS: Sell order placed successfully!")
    print(f"Order ID: {sell_order['order_id']}")
    print(f"Symbol: {sell_order['symbol']}")
    print(f"Side: {sell_order['side']}")
    print(f"Quantity: {sell_order['qty']}")
    print(f"Status: {sell_order['status']}")

    # Check order status
    print(f"\nChecking order status...")
    order_status = executor.get_order_status(sell_order['order_id'])
    print(f"Current status: {order_status['status']}")
    print(f"Filled quantity: {order_status['filled_qty']}")

    if order_status['is_filled']:
        print(f"SUCCESS: Order filled at ${order_status['filled_avg_price']}")
    elif order_status['is_pending']:
        print(f"PENDING: Order is pending execution")

except Exception as e:
    print(f"ERROR: {e}")