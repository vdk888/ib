#!/usr/bin/env python3
"""
Parser for Uncle Stock screener CSV files
Extracts key information and creates universe.json
"""

import csv
import json
import os
from glob import glob
from config import UNCLE_STOCK_SCREENS

def parse_screener_csv(csv_path):
    """
    Parse a single screener CSV file and extract key information
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        list: List of stock dictionaries with extracted information
    """
    stocks = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip the sep= line if present
            first_line = f.readline()
            if not first_line.startswith('sep='):
                f.seek(0)  # Go back to beginning if no sep line
            
            reader = csv.DictReader(f)
            
            for row in reader:
                # Extract key fields
                stock_data = {
                    'ticker': row.get('symbol', '').strip(),
                    'isin': row.get('ISIN', '').strip(),
                    'name': row.get('name', '').strip(),
                    'currency': row.get('stock price currency', '').strip(),
                    'sector': row.get('sector', '').strip(),
                    'country': row.get('country', '').strip()
                }
                
                # Only add if ticker exists
                if stock_data['ticker']:
                    stocks.append(stock_data)
                    
    except Exception as e:
        print(f"Error parsing {csv_path}: {e}")
    
    return stocks

def create_universe():
    """
    Parse all screener CSV files and create universe.json
    
    Returns:
        dict: Universe data with stocks from all screeners
    """
    universe = {
        'metadata': {
            'screens': list(UNCLE_STOCK_SCREENS.values()),
            'total_stocks': 0,
            'unique_stocks': 0
        },
        'screens': {},
        'all_stocks': {}
    }
    
    # Track unique stocks across all screens
    unique_stocks = {}
    
    # Process each screener
    for screen_key, screen_name in UNCLE_STOCK_SCREENS.items():
        # Find the corresponding CSV file
        safe_name = screen_name.replace(' ', '_').replace('/', '_')
        csv_path = f"data/files_exports/{safe_name}_current_screen.csv"
        
        if os.path.exists(csv_path):
            print(f"Parsing {screen_name} from {csv_path}...")
            stocks = parse_screener_csv(csv_path)
            
            # Store stocks for this screen
            universe['screens'][screen_key] = {
                'name': screen_name,
                'count': len(stocks),
                'stocks': stocks
            }
            
            # Add to unique stocks collection
            for stock in stocks:
                ticker = stock['ticker']
                if ticker not in unique_stocks:
                    unique_stocks[ticker] = stock
                    unique_stocks[ticker]['screens'] = [screen_name]
                else:
                    # Stock exists in multiple screens, add this screen to its list
                    if 'screens' not in unique_stocks[ticker]:
                        unique_stocks[ticker]['screens'] = []
                    if screen_name not in unique_stocks[ticker]['screens']:
                        unique_stocks[ticker]['screens'].append(screen_name)
            
            print(f"  Found {len(stocks)} stocks in {screen_name}")
        else:
            print(f"Warning: CSV file not found for {screen_name}: {csv_path}")
            universe['screens'][screen_key] = {
                'name': screen_name,
                'count': 0,
                'stocks': []
            }
    
    # Store unique stocks
    universe['all_stocks'] = unique_stocks
    
    # Update metadata
    universe['metadata']['total_stocks'] = sum(
        screen['count'] for screen in universe['screens'].values()
    )
    universe['metadata']['unique_stocks'] = len(unique_stocks)
    
    return universe

def save_universe(universe, output_path='data/universe.json'):
    """
    Save universe data to JSON file
    
    Args:
        universe: Universe dictionary
        output_path: Path to save the JSON file
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(universe, f, indent=2, ensure_ascii=False)
        print(f"\nUniverse saved to {output_path}")
        print(f"  Total stocks across all screens: {universe['metadata']['total_stocks']}")
        print(f"  Unique stocks: {universe['metadata']['unique_stocks']}")
        
        # Show stocks in multiple screens
        multi_screen_stocks = [
            (ticker, data) for ticker, data in universe['all_stocks'].items()
            if len(data.get('screens', [])) > 1
        ]
        
        if multi_screen_stocks:
            print(f"\nStocks appearing in multiple screens ({len(multi_screen_stocks)}):")
            for ticker, data in multi_screen_stocks[:10]:  # Show first 10
                screens = ', '.join(data['screens'])
                print(f"  {ticker}: {screens}")
            if len(multi_screen_stocks) > 10:
                print(f"  ... and {len(multi_screen_stocks) - 10} more")
                
    except Exception as e:
        print(f"Error saving universe: {e}")

def main():
    """Main function to parse CSVs and create universe.json"""
    print("Parsing Uncle Stock screener CSV files")
    print("=" * 50)
    
    # Check if data/files_exports directory exists
    if not os.path.exists('data/files_exports'):
        print("Error: data/files_exports directory not found")
        print("Please run screener.py first to fetch the CSV files")
        return
    
    # Create universe
    universe = create_universe()
    
    # Save to JSON
    save_universe(universe)
    
    print("\n" + "=" * 50)
    print("Parsing complete")

if __name__ == "__main__":
    main()