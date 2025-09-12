#!/usr/bin/env python3
"""
Main entry point for Uncle Stock API screener
"""

from screener import get_all_screeners, get_all_screener_histories
from config import UNCLE_STOCK_SCREENS

def main():
    print("Uncle Stock Screener")
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
    print("SUMMARY")
    print("=" * 50)
    
    total_stocks = 0
    for key, screen_name in UNCLE_STOCK_SCREENS.items():
        stocks_result = all_stocks.get(key, {})
        history_result = all_histories.get(key, {})
        
        print(f"\n{screen_name}:")
        
        if stocks_result.get('success'):
            stock_count = len(stocks_result['data'])
            total_stocks += stock_count
            print(f"  ✓ Stocks: {stock_count} found")
            print(f"    First 5: {stocks_result['data'][:5]}")
            if 'csv_file' in stocks_result:
                print(f"    CSV: {stocks_result['csv_file']}")
        else:
            print(f"  ✗ Stocks: Failed - {stocks_result.get('data', 'Unknown error')}")
        
        if history_result.get('success'):
            print(f"  ✓ History: Retrieved")
            if 'csv_file' in history_result:
                print(f"    CSV: {history_result['csv_file']}")
        else:
            print(f"  ✗ History: Failed - {history_result.get('data', 'Unknown error')}")
    
    print("\n" + "=" * 50)
    print(f"Total stocks across all screeners: {total_stocks}")
    print("Screener run complete")

if __name__ == "__main__":
    main()