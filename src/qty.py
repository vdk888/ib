#!/usr/bin/env python3
"""
Quantity calculator for portfolio management
Gets account total value from IBKR and updates universe.json with account balance
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path to import ib_fetch
sys.path.append(str(Path(__file__).parent.parent))

from ib_fetch import IBApi
import threading
import time

def get_account_total_value():
    """Get total account value from IBKR using ib_fetch functions"""
    print("Connecting to IBKR to get account value...")
    
    # Initialize API client
    app = IBApi()
    
    # Connect to IB Gateway (paper trading port 4002)
    app.connect("127.0.0.1", 4002, clientId=3)
    
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
        return None
    
    # Wait a moment for account ID
    time.sleep(2)
    
    if not app.account_id:
        print("No account ID received")
        return None
    
    # Request account summary
    app.reqAccountSummary(9002, "All", "NetLiquidation")
    
    # Wait for data to be received
    time.sleep(3)
    
    # Cancel subscription
    app.cancelAccountSummary(9002)
    
    # Get total value
    total_value = None
    currency = None
    if "NetLiquidation" in app.account_summary:
        total_value = float(app.account_summary["NetLiquidation"]["value"])
        currency = app.account_summary["NetLiquidation"]["currency"]
        print(f"Account Total Value: ${total_value:,.2f} {currency}")
    
    # Disconnect
    app.disconnect()
    
    return total_value, currency

def update_universe_json(account_value):
    """Add account total value to the top of universe.json file"""
    universe_path = Path(__file__).parent.parent / "data" / "universe.json"
    
    if not universe_path.exists():
        print(f"Universe file not found at: {universe_path}")
        return False
    
    try:
        # Read current universe.json
        with open(universe_path, 'r', encoding='utf-8') as f:
            universe_data = json.load(f)
        
        # Add account value at the top level
        universe_data["account_total_value"] = {
            "value": account_value,
            "currency": "USD",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Write back to file
        with open(universe_path, 'w', encoding='utf-8') as f:
            json.dump(universe_data, f, indent=2, ensure_ascii=False)
        
        print(f"Updated universe.json with account value: ${account_value:,.2f}")
        return True
        
    except Exception as e:
        print(f"Error updating universe.json: {e}")
        return False

def main():
    """Main function to get account value and update universe.json"""
    print("Starting quantity calculator...")
    
    # Get account total value from IBKR
    account_value = get_account_total_value()
    
    if account_value is None:
        print("Failed to get account value from IBKR")
        return
    
    # Update universe.json with the account value
    success = update_universe_json(account_value)
    
    if success:
        print("Successfully updated universe.json with account total value")
    else:
        print("Failed to update universe.json")

if __name__ == "__main__":
    main()