#!/usr/bin/env python3
"""
Main entry point for Uncle Stock API screener
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.screener import get_all_screeners, get_all_screener_histories
from src.parser import create_universe, save_universe
from src.history_parser import update_universe_with_history
from config import UNCLE_STOCK_SCREENS

def step1_fetch_data():
    """Step 1: Fetch current stocks and backtest history from all screeners"""
    print("STEP 1: Fetching data from Uncle Stock API")
    print("=" * 50)
    print(f"Configured screeners: {list(UNCLE_STOCK_SCREENS.values())}")
    
    # Fetch current stocks from all screeners
    print("\nFetching current stocks from all screeners...")
    all_stocks = get_all_screeners()
    
    # Fetch backtest history from all screeners
    print("\nFetching backtest history from all screeners...")
    all_histories = get_all_screener_histories()
    
    # Display summary
    print("\n" + "=" * 50)
    print("STEP 1 SUMMARY")
    print("=" * 50)
    
    total_stocks = 0
    for key, screen_name in UNCLE_STOCK_SCREENS.items():
        stocks_result = all_stocks.get(key, {})
        history_result = all_histories.get(key, {})
        
        print(f"\n{screen_name}:")
        
        if stocks_result.get('success'):
            stock_count = len(stocks_result['data'])
            total_stocks += stock_count
            print(f"  + Stocks: {stock_count} found")
            print(f"    First 5: {stocks_result['data'][:5]}")
            if 'csv_file' in stocks_result:
                print(f"    CSV: {stocks_result['csv_file']}")
        else:
            print(f"  X Stocks: Failed - {stocks_result.get('data', 'Unknown error')}")
        
        if history_result.get('success'):
            print(f"  + History: Retrieved")
            if 'csv_file' in history_result:
                print(f"    CSV: {history_result['csv_file']}")
        else:
            print(f"  X History: Failed - {history_result.get('data', 'Unknown error')}")
    
    print(f"\nTotal stocks across all screeners: {total_stocks}")
    print("Step 1 complete - CSV files saved to data/files_exports/")
    return True

def step2_parse_data():
    """Step 2: Parse CSV files and create universe.json"""
    print("\nSTEP 2: Parsing CSV files and creating universe.json")
    print("=" * 50)
    
    # Create universe from CSV files
    universe = create_universe()
    
    # Save to JSON
    save_universe(universe)
    
    print("Step 2 complete - universe.json created")
    return True

def step3_parse_history():
    """Step 3: Parse historical performance data and update universe.json"""
    print("\nSTEP 3: Parsing historical performance data")
    print("=" * 50)
    
    # Update universe.json with historical performance data
    success = update_universe_with_history()
    
    if success:
        print("Step 3 complete - universe.json updated with historical performance data")
        return True
    else:
        print("Step 3 failed - could not update universe.json with historical data")
        return False

def step4_optimize_portfolio():
    """Step 4: Optimize portfolio allocations using Sharpe ratio maximization"""
    print("\nSTEP 4: Optimizing portfolio allocations")
    print("=" * 50)
    
    try:
        # Import and run portfolio optimizer
        import sys
        import subprocess
        
        # Run portfolio optimizer
        result = subprocess.run(
            ["python", "src/portfolio_optimizer.py"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("Step 4 complete - portfolio optimization successful")
            # Display key results
            print("\nOptimization output:")
            print(result.stdout)
            return True
        else:
            print("Step 4 failed - portfolio optimization error")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Step 4 failed - {e}")
        return False

def step5_update_currency():
    """Step 5: Update universe.json with EUR exchange rates"""
    print("\nSTEP 5: Updating EUR exchange rates")
    print("=" * 50)
    
    try:
        # Import and run currency updater
        from src.currency import main as currency_main
        
        success = currency_main()
        
        if success:
            print("Step 5 complete - exchange rates updated")
            return True
        else:
            print("Step 5 failed - exchange rate update error")
            return False
            
    except Exception as e:
        print(f"Step 5 failed - {e}")
        return False

def step6_calculate_targets():
    """Step 6: Calculate final stock allocations based on screener allocations and 180d performance"""
    print("\nSTEP 6: Calculating final stock allocations")
    print("=" * 50)
    
    try:
        # Import and run targetter
        from src.targetter import main as targetter_main
        
        success = targetter_main()
        
        if success:
            print("Step 6 complete - stock allocations calculated")
            return True
        else:
            print("Step 6 failed - allocation calculation error")
            return False
            
    except Exception as e:
        print(f"Step 6 failed - {e}")
        return False

def step7_calculate_quantities():
    """Step 7: Get account value from IBKR and calculate stock quantities"""
    print("\nSTEP 7: Calculating stock quantities based on account value")
    print("=" * 50)
    
    try:
        # Import and run quantity calculator
        import subprocess
        
        # Run qty.py
        result = subprocess.run(
            ["python", "src/qty.py"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("Step 7 complete - stock quantities calculated")
            # Display key results
            print("\nQuantity calculation output:")
            print(result.stdout)
            return True
        else:
            print("Step 7 failed - quantity calculation error")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Step 7 failed - {e}")
        return False

def step8_ibkr_search():
    """Step 8: Search for all universe stocks on IBKR and update with identification details"""
    print("\nSTEP 8: Searching for stocks on Interactive Brokers")
    print("=" * 50)
    
    try:
        # Import and run IBKR comprehensive search directly
        from src.comprehensive_enhanced_search import process_all_universe_stocks
        
        # Run the function directly
        process_all_universe_stocks()
        
        print("Step 8 complete - IBKR stock search completed")
        return True
            
    except Exception as e:
        print(f"Step 8 failed - {e}")
        return False

def step9_rebalancer():
    """Step 9: Generate rebalancing orders based on target quantities and current positions"""
    print("\nSTEP 9: Generating portfolio rebalancing orders")
    print("=" * 50)
    
    try:
        # Import and run portfolio rebalancer directly
        from src.rebalancer import main as run_rebalancer
        
        # Run the function directly
        run_rebalancer()
        
        print("Step 9 complete - rebalancing orders generated")
        return True
            
    except Exception as e:
        print(f"Step 9 failed - {e}")
        return False

def step10_execute_orders():
    """Step 10: Execute rebalancing orders through IBKR API"""
    print("\nSTEP 10: Executing rebalancing orders through IBKR")
    print("=" * 50)
    
    try:
        # Import and run order executor directly
        from src.order_executor import main as execute_orders
        
        # Run the function directly
        execute_orders()
        
        print("Step 10 complete - orders executed successfully")
        return True
            
    except Exception as e:
        print(f"Step 10 failed - {e}")
        return False

def run_all_steps():
    """Run all steps in sequence"""
    print("Uncle Stock Screener - Full Pipeline")
    print("=" * 60)
    
    try:
        # Step 1: Fetch data
        if step1_fetch_data():
            # Step 2: Parse data
            if step2_parse_data():
                # Step 3: Parse historical data
                if step3_parse_history():
                    # Step 4: Optimize portfolio
                    if step4_optimize_portfolio():
                        # Step 5: Update currency exchange rates
                        if step5_update_currency():
                            # Step 6: Calculate final stock allocations
                            if step6_calculate_targets():
                                # Step 7: Calculate stock quantities from IBKR account value
                                if step7_calculate_quantities():
                                    # Step 8: Search for stocks on IBKR and update with identification details
                                    if step8_ibkr_search():
                                        # Step 9: Generate rebalancing orders
                                        if step9_rebalancer():
                                            # Step 10: Execute orders
                                            step10_execute_orders()
                                            
                                            print("\n" + "=" * 60)
                                            print("ALL STEPS COMPLETE")
                                            print("Files created:")
                                            print("  - CSV files in data/files_exports/")
                                            print("  - universe.json with complete stock data, portfolio optimization, allocations, and quantities")
                                            print("  - universe_with_ibkr.json with IBKR identification details")
                                            print("  - data/orders.json with rebalancing orders ready for execution")
                                            print("\nPortfolio rebalancing complete!")
                                        else:
                                            print("Step 9 failed - stopping pipeline")
                                    else:
                                        print("Step 8 failed - stopping pipeline")
                                else:
                                    print("Step 7 failed - stopping pipeline")
                            else:
                                print("Step 6 failed - stopping pipeline")
                        else:
                            print("Step 5 failed - stopping pipeline")
                    else:
                        print("Step 4 failed - stopping pipeline")
                else:
                    print("Step 3 failed - stopping pipeline")
            else:
                print("Step 2 failed - stopping pipeline")
        else:
            print("Step 1 failed - stopping pipeline")
            
    except Exception as e:
        print(f"Error in pipeline: {e}")

def show_help():
    """Show usage help"""
    print("Uncle Stock Screener")
    print("=" * 30)
    print("Usage: python main.py [step]")
    print("\nAvailable steps:")
    print("  1, step1, fetch     - Fetch data from Uncle Stock API")
    print("  2, step2, parse     - Parse CSV files and create universe.json")
    print("  3, step3, history   - Parse historical performance data")
    print("  4, step4, portfolio - Optimize portfolio allocations")
    print("  5, step5, currency  - Update EUR exchange rates")
    print("  6, step6, target    - Calculate final stock allocations")
    print("  7, step7, qty       - Get account value from IBKR and calculate stock quantities")
    print("  8, step8, ibkr      - Search for all universe stocks on IBKR")
    print("  9, step9, rebalance - Generate rebalancing orders based on targets vs current positions")
    print("  10, step10, execute - Execute rebalancing orders through IBKR API")
    print("  all, full           - Run all steps (default)")
    print("  help, -h, --help    - Show this help")
    print("\nExamples:")
    print("  python main.py            # Run all steps")
    print("  python main.py 1          # Only fetch data")
    print("  python main.py parse      # Only parse existing CSV files")
    print("  python main.py 3          # Only parse historical data")
    print("  python main.py portfolio  # Only optimize portfolio")
    print("  python main.py 5          # Only update exchange rates")
    print("  python main.py target     # Only calculate stock allocations")
    print("  python main.py qty        # Only calculate stock quantities from IBKR")
    print("  python main.py ibkr       # Only search for stocks on IBKR")
    print("  python main.py rebalance  # Only generate rebalancing orders")
    print("  python main.py execute    # Only execute orders from orders.json")

def main():
    """Main function with command-line argument support"""
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ['1', 'step1', 'fetch']:
            step1_fetch_data()
        elif arg in ['2', 'step2', 'parse']:
            step2_parse_data()
        elif arg in ['3', 'step3', 'history']:
            step3_parse_history()
        elif arg in ['4', 'step4', 'portfolio']:
            step4_optimize_portfolio()
        elif arg in ['5', 'step5', 'currency']:
            step5_update_currency()
        elif arg in ['6', 'step6', 'target']:
            step6_calculate_targets()
        elif arg in ['7', 'step7', 'qty']:
            step7_calculate_quantities()
        elif arg in ['8', 'step8', 'ibkr']:
            step8_ibkr_search()
        elif arg in ['9', 'step9', 'rebalance']:
            step9_rebalancer()
        elif arg in ['10', 'step10', 'execute']:
            step10_execute_orders()
        elif arg in ['all', 'full']:
            run_all_steps()
        elif arg in ['help', '-h', '--help']:
            show_help()
        else:
            print(f"Unknown argument: {arg}")
            show_help()
    else:
        # Default: run all steps
        run_all_steps()

if __name__ == "__main__":
    main()