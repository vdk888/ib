#!/usr/bin/env python3
"""
Quantity calculator for portfolio management
Gets account total value from IBKR and updates universe.json with account balance
"""

import json
import os
import sys
from pathlib import Path

# Add ib_utils directory to path to import ib_fetch
sys.path.append(str(Path(__file__).parent / "ib_utils"))

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

def calculate_stock_quantities(universe_data, account_value):
    """Calculate EUR prices and quantities for all stocks based on account value and target allocations"""
    print("Calculating stock quantities...")
    
    total_stocks_processed = 0
    minimal_allocation_count = 0
    meaningful_allocation_count = 0
    
    # Get screen allocations from portfolio optimization
    screen_allocations = {}
    if ("metadata" in universe_data and 
        "portfolio_optimization" in universe_data["metadata"] and 
        "optimal_allocations" in universe_data["metadata"]["portfolio_optimization"]):
        screen_allocations = universe_data["metadata"]["portfolio_optimization"]["optimal_allocations"]
    
    # Process all stock categories
    stock_categories = ["screens", "all_stocks"] if "all_stocks" in universe_data else ["screens"]
    
    for category in stock_categories:
        if category == "screens":
            # Process each screen
            for screen_name, screen_data in universe_data["screens"].items():
                print(f"Processing screen: {screen_name}")
                if isinstance(screen_data, dict) and "stocks" in screen_data:
                    # Get the correct screen allocation for this screen
                    screen_allocation = screen_allocations.get(screen_name, 0)
                    
                    for stock in screen_data["stocks"]:
                        if isinstance(stock, dict):  # Make sure it's a stock dictionary
                            calculate_stock_fields(stock, account_value, screen_allocation)
                            total_stocks_processed += 1
                            
                            # Count allocation types
                            final_target = float(stock.get("final_target", 0))
                            if final_target < 1e-10 and final_target > 0:
                                minimal_allocation_count += 1
                            elif final_target > 0:
                                meaningful_allocation_count += 1
                        else:
                            print(f"Warning: Non-dict stock found in {screen_name}: {stock}")
                else:
                    print(f"Warning: Screen {screen_name} has no stocks or is not a dict: {type(screen_data)}")
        
        elif category == "all_stocks":
            # Process all_stocks category - it's a dict with ticker keys
            print(f"Processing all_stocks category")
            for ticker, stock in universe_data["all_stocks"].items():
                if isinstance(stock, dict):  # Make sure it's a stock dictionary
                    # For all_stocks, use the stored final_target
                    calculate_stock_fields(stock, account_value, None)
                    total_stocks_processed += 1
                else:
                    print(f"Warning: Non-dict stock found in all_stocks: {ticker}: {stock}")
    
    print(f"Processed {total_stocks_processed} stocks with quantity calculations")
    print(f"  - {meaningful_allocation_count} stocks with meaningful allocations (>1e-10)")
    print(f"  - {minimal_allocation_count} stocks with minimal allocations (<1e-10)")
    return total_stocks_processed

def calculate_stock_fields(stock, account_value, screen_allocation=None):
    """Calculate EUR price, target value, and quantity for a single stock"""
    try:
        # Get stock price and exchange rate
        price = float(stock.get("price", 0))
        eur_exchange_rate = float(stock.get("eur_exchange_rate", 1))
        
        # Calculate final_target based on context
        if screen_allocation is not None:
            # We're in a screen context - calculate final_target using this screen's allocation
            allocation_target = float(stock.get("allocation_target", 0))
            final_target = allocation_target * screen_allocation
            # Update the screen_target field to reflect the current screen
            stock["screen_target"] = screen_allocation
        else:
            # We're in all_stocks context - use the stored final_target
            final_target = float(stock.get("final_target", 0))
        
        # Update the final_target in the stock
        stock["final_target"] = final_target
        
        # Calculate EUR equivalent price
        eur_price = price / eur_exchange_rate
        
        # Calculate target value in EUR
        target_value_eur = account_value * final_target
        
        # Calculate quantity (shares to buy)
        quantity = target_value_eur / eur_price if eur_price > 0 else 0
        
        # Add new fields to the stock
        stock["eur_price"] = round(eur_price, 6)
        stock["target_value_eur"] = round(target_value_eur, 2)
        stock["quantity"] = int(round(quantity))
        
        # Add a flag for very small allocations for transparency
        if final_target < 1e-10 and final_target > 0:
            stock["allocation_note"] = "minimal_allocation"
        elif "allocation_note" in stock:
            # Remove the note if allocation is no longer minimal
            del stock["allocation_note"]
        
    except (ValueError, TypeError, ZeroDivisionError) as e:
        # Handle missing or invalid data
        stock["eur_price"] = 0
        stock["target_value_eur"] = 0
        stock["quantity"] = 0
        print(f"Warning: Error calculating for {stock.get('ticker', 'Unknown')}: {e}")

def update_universe_json(account_value, currency):
    """Add account total value and calculate stock quantities in universe.json"""
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
            "currency": currency,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Calculate stock quantities for all stocks
        stocks_processed = calculate_stock_quantities(universe_data, account_value)
        
        # Write back to file
        with open(universe_path, 'w', encoding='utf-8') as f:
            json.dump(universe_data, f, indent=2, ensure_ascii=False)
        
        print(f"Updated universe.json with account value: ${account_value:,.2f}")
        print(f"Added quantity calculations for {stocks_processed} stocks")
        return True
        
    except Exception as e:
        print(f"Error updating universe.json: {e}")
        return False

def main():
    """Main function to get account value and update universe.json"""
    print("Starting quantity calculator...")
    
    # Get account total value from IBKR
    account_value, currency = get_account_total_value()
    
    if account_value is None or currency is None:
        print("Failed to get account value from IBKR")
        return
    
    # Update universe.json with the account value
    success = update_universe_json(account_value, currency)
    
    if success:
        print("Successfully updated universe.json with account total value")
    else:
        print("Failed to update universe.json")

if __name__ == "__main__":
    main()