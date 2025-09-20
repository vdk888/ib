"""
Test script for Alpaca order history functionality.
"""

import logging
from app.services.implementations.legacy.alpaca_utils.order_executor import AlpacaOrderExecutor

logging.basicConfig(level=logging.INFO)

try:
    print("=== Testing Alpaca Order History Functions ===")

    # Initialize executor
    executor = AlpacaOrderExecutor(paper=True)

    # Test getting recent orders (last 5)
    print(f"\n1. Getting last 5 recent orders...")
    recent_orders = executor.get_recent_orders(limit=5)
    print(f"Found {len(recent_orders)} recent orders")

    if recent_orders:
        print("Recent orders:")
        for i, order in enumerate(recent_orders, 1):
            print(f"  {i}. {order['symbol']}: {order['side'].upper()} {order['qty']} shares")
            print(f"     Status: {order['status']}, Created: {order['created_at'][:19]}")

    # Test getting order history (last 10)
    print(f"\n2. Getting order history (last 10)...")
    order_history = executor.get_order_history(limit=10)
    print(f"Found {len(order_history)} orders in history")

    if order_history:
        print("Order history summary:")
        for i, order in enumerate(order_history, 1):
            status_emoji = "[FILLED]" if order['is_filled'] else "[CANCELED]" if order['is_canceled'] else "[PENDING]"
            print(f"  {i}. {order['symbol']}: {order['side'].upper()} {order['qty']} ({order['status']}) {status_emoji}")

    # Test getting filled orders only
    print(f"\n3. Getting filled orders (last 5)...")
    filled_orders = executor.get_filled_orders(limit=5)
    print(f"Found {len(filled_orders)} filled orders")

    if filled_orders:
        print("Filled orders:")
        for i, order in enumerate(filled_orders, 1):
            print(f"  {i}. {order['symbol']}: {order['side'].upper()} {order['filled_qty']} @ ${order['filled_avg_price']}")
            print(f"     Filled at: {order['filled_at'][:19] if order['filled_at'] else 'N/A'}")

    # Test getting orders for specific symbol
    print(f"\n4. Getting orders for SPY...")
    spy_orders = executor.get_recent_orders(limit=5, symbol="SPY")
    print(f"Found {len(spy_orders)} orders for SPY")

    if spy_orders:
        print("SPY orders:")
        for i, order in enumerate(spy_orders, 1):
            print(f"  {i}. {order['side'].upper()} {order['qty']} shares ({order['status']})")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()