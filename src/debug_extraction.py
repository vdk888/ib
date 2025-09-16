#!/usr/bin/env python3
"""
Debug the extraction and filtering process to find why we get 60 instead of 67 stocks
"""

import json
from pathlib import Path

def extract_unique_stocks(universe_data):
    """Extract unique stocks from universe.json - same logic as comprehensive_enhanced_search.py"""
    unique_stocks = {}

    # Process all screens
    for screen_name, screen_data in universe_data.get('screens', {}).items():
        for stock in screen_data.get('stocks', []):
            # Use ticker as unique key
            ticker = stock.get('ticker')
            if ticker and ticker not in unique_stocks:
                unique_stocks[ticker] = {
                    'ticker': ticker,
                    'isin': stock.get('isin'),
                    'name': stock.get('name'),
                    'currency': stock.get('currency'),
                    'sector': stock.get('sector'),
                    'country': stock.get('country'),
                    'quantity': stock.get('quantity', 0)  # Include quantity field
                }

    return list(unique_stocks.values())

def filter_stocks_by_quantity(stocks):
    """Filter stocks to only include those with quantities > 0"""
    filtered_stocks = [stock for stock in stocks if stock.get('quantity', 0) > 0]
    return filtered_stocks

def debug_extraction():
    """Debug the extraction process"""
    script_dir = Path(__file__).parent
    universe_path = script_dir.parent / 'data' / 'universe.json'

    print(f"Loading universe from: {universe_path}")

    with open(universe_path, 'r', encoding='utf-8') as f:
        universe_data = json.load(f)

    # Count stocks with meaningful allocations in raw data
    meaningful_stocks_raw = []
    for screen_name, screen_data in universe_data.get('screens', {}).items():
        for stock in screen_data.get('stocks', []):
            final_target = stock.get('final_target', 0)
            quantity = stock.get('quantity', 0)
            if final_target > 1e-10:
                meaningful_stocks_raw.append({
                    'ticker': stock.get('ticker'),
                    'quantity': quantity,
                    'final_target': final_target,
                    'screen': screen_name
                })

    print(f"Raw meaningful stocks (final_target > 1e-10): {len(meaningful_stocks_raw)}")

    # Extract unique stocks using the same logic as comprehensive_enhanced_search.py
    all_unique_stocks = extract_unique_stocks(universe_data)
    print(f"Total unique stocks extracted: {len(all_unique_stocks)}")

    # Filter by quantity
    filtered_stocks = filter_stocks_by_quantity(all_unique_stocks)
    print(f"Stocks with quantity > 0: {len(filtered_stocks)}")

    # Find which meaningful stocks are missing after extraction
    meaningful_tickers = {stock['ticker'] for stock in meaningful_stocks_raw if stock['quantity'] > 0}
    extracted_tickers = {stock['ticker'] for stock in filtered_stocks}

    missing_tickers = meaningful_tickers - extracted_tickers
    extra_tickers = extracted_tickers - meaningful_tickers

    print(f"\nMeaningful stocks with quantity > 0: {len(meaningful_tickers)}")
    print(f"Extracted stocks with quantity > 0: {len(extracted_tickers)}")

    if missing_tickers:
        print(f"\nMISSING TICKERS ({len(missing_tickers)}):")
        for ticker in missing_tickers:
            # Find the stock details
            for stock in meaningful_stocks_raw:
                if stock['ticker'] == ticker and stock['quantity'] > 0:
                    print(f"  {ticker} (quantity: {stock['quantity']}, target: {stock['final_target']:.2e})")
                    break

    if extra_tickers:
        print(f"\nEXTRA TICKERS ({len(extra_tickers)}):")
        for ticker in extra_tickers:
            # Find why this ticker was included
            for stock in all_unique_stocks:
                if stock['ticker'] == ticker:
                    print(f"  {ticker} (quantity: {stock['quantity']})")
                    break

    # Check for duplicate tickers in raw data
    ticker_counts = {}
    for screen_name, screen_data in universe_data.get('screens', {}).items():
        for stock in screen_data.get('stocks', []):
            ticker = stock.get('ticker')
            if ticker:
                if ticker not in ticker_counts:
                    ticker_counts[ticker] = []
                ticker_counts[ticker].append(screen_name)

    duplicates = {ticker: screens for ticker, screens in ticker_counts.items() if len(screens) > 1}
    if duplicates:
        print(f"\nDUPLICATE TICKERS FOUND ({len(duplicates)}):")
        for ticker, screens in list(duplicates.items())[:10]:  # Show first 10
            print(f"  {ticker}: appears in {screens}")

if __name__ == "__main__":
    debug_extraction()