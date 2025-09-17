#!/usr/bin/env python3
"""
Direct test of order status functionality bypassing FastAPI
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Test the order status service directly
from backend.app.services.implementations.order_status_service import OrderStatusService

def test_order_status():
    print("Testing OrderStatusService directly...")

    # Create service
    service = OrderStatusService()
    print(f"Service created: {type(service)}")

    # Set orders file
    orders_file = os.path.join(os.path.dirname(__file__), "backend", "data", "orders.json")
    service.orders_file = orders_file
    print(f"Orders file: {orders_file}")
    print(f"Orders file exists: {os.path.exists(orders_file)}")

    if not os.path.exists(orders_file):
        print("ERROR: Orders file not found!")
        return False

    try:
        # Run status check
        print("Running status check...")
        success = service.run_status_check()
        print(f"Status check result: {success}")

        if success:
            print("Getting verification results...")
            result = service.get_verification_results()
            print(f"Result type: {type(result)}")
            print(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            return True
        else:
            print("Status check failed")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_order_status()