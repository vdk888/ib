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

def find_column_index(headers, description_row, header_name, subtitle_pattern):
    """
    Find column index based on header name and subtitle pattern
    
    Args:
        headers: List of column headers
        description_row: Row containing descriptions/subtitles
        header_name: Name of the header to match (e.g., 'Price')
        subtitle_pattern: Pattern to match in the description (e.g., '180d change')
        
    Returns:
        int or None: Column index if found, None otherwise
    """
    for i, (h, d) in enumerate(zip(headers, description_row)):
        if h == header_name and subtitle_pattern in d:
            return i
    return None

def extract_field_data(csv_path, header_name, subtitle_pattern, ticker=None):
    """
    Extract data from a CSV file based on header and subtitle pattern
    
    Args:
        csv_path: Path to the CSV file
        header_name: Name of the header to match (e.g., 'Price')
        subtitle_pattern: Pattern to match in the description (e.g., '180d change')
        ticker: Optional ticker to filter for specific stock, if None returns all stocks
        
    Returns:
        dict or list: If ticker specified, returns single stock data, otherwise all stocks
    """
    results = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip the sep= line if present
            first_line = f.readline()
            if not first_line.startswith('sep='):
                f.seek(0)
            
            reader = csv.reader(f)
            headers = next(reader)
            subheaders = next(reader)
            description_row = next(reader)
            
            # Find the target column
            column_index = find_column_index(headers, description_row, header_name, subtitle_pattern)
            if column_index is None:
                return None if ticker else []
            
            # Find symbol column
            symbol_index = None
            for i, h in enumerate(headers):
                if h == 'symbol':
                    symbol_index = i
                    break
            
            if symbol_index is None:
                return None if ticker else []
            
            # Extract data
            for row in reader:
                if len(row) <= max(column_index, symbol_index):
                    continue
                
                stock_ticker = row[symbol_index].strip()
                if not stock_ticker or len(stock_ticker) < 2:
                    continue
                
                value = row[column_index].strip() if column_index < len(row) else ''
                
                stock_data = {
                    'ticker': stock_ticker,
                    'field': f'{header_name} | {subtitle_pattern}',
                    'value': value
                }
                
                if ticker and stock_ticker == ticker:
                    return stock_data
                elif not ticker:
                    results.append(stock_data)
            
            return None if ticker else results
            
    except Exception as e:
        print(f"Error extracting field data from {csv_path}: {e}")
        return None if ticker else []

def parse_screener_csv_flexible(csv_path, additional_fields=None):
    """
    Parse a CSV file and extract both standard fields and additional custom fields
    
    Args:
        csv_path: Path to the CSV file
        additional_fields: List of tuples (header_name, subtitle_pattern, field_alias)
                          e.g., [('Price', '180d change', 'price_180d_change')]
        
    Returns:
        list: List of stock dictionaries with extracted information
    """
    stocks = []
    
    if additional_fields is None:
        additional_fields = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip the sep= line if present
            first_line = f.readline()
            if not first_line.startswith('sep='):
                f.seek(0)
            
            reader = csv.reader(f)
            headers = next(reader)
            subheaders = next(reader)
            description_row = next(reader)
            
            # Find standard field indices
            basic_fields = {
                'symbol': None, 'ISIN': None, 'name': None,
                'stock price currency': None, 'sector': None, 'country': None
            }
            
            for i, header in enumerate(headers):
                if header in basic_fields:
                    basic_fields[header] = i
            
            # Find price column index
            price_column_index = find_column_index(headers, description_row, 'Price', 'per share in stock price currency')
            
            # Find additional field indices
            additional_indices = {}
            for header_name, subtitle_pattern, field_alias in additional_fields:
                idx = find_column_index(headers, description_row, header_name, subtitle_pattern)
                if idx is not None:
                    additional_indices[field_alias] = idx
            
            # Parse data rows
            for row in reader:
                if len(row) <= max([idx for idx in basic_fields.values() if idx is not None] or [0]):
                    continue
                
                # Skip rows without valid ticker
                ticker = (row[basic_fields['symbol']] if basic_fields['symbol'] is not None and basic_fields['symbol'] < len(row) else '').strip()
                if not ticker or len(ticker) < 2:
                    continue
                
                # Extract standard fields
                stock_data = {
                    'ticker': ticker,
                    'isin': (row[basic_fields['ISIN']] if basic_fields['ISIN'] is not None and basic_fields['ISIN'] < len(row) else '').strip(),
                    'name': (row[basic_fields['name']] if basic_fields['name'] is not None and basic_fields['name'] < len(row) else '').strip(),
                    'currency': (row[basic_fields['stock price currency']] if basic_fields['stock price currency'] is not None and basic_fields['stock price currency'] < len(row) else '').strip(),
                    'sector': (row[basic_fields['sector']] if basic_fields['sector'] is not None and basic_fields['sector'] < len(row) else '').strip(),
                    'country': (row[basic_fields['country']] if basic_fields['country'] is not None and basic_fields['country'] < len(row) else '').strip()
                }
                
                # Extract price
                if price_column_index is not None and price_column_index < len(row):
                    try:
                        price_str = row[price_column_index].strip()
                        if price_str and price_str != '' and not price_str.startswith('per share') and price_str not in ['Latest', 'N/A']:
                            stock_data['price'] = float(price_str)
                        else:
                            stock_data['price'] = None
                    except (ValueError, AttributeError):
                        stock_data['price'] = None
                else:
                    stock_data['price'] = None
                
                # Extract additional fields
                for field_alias, column_index in additional_indices.items():
                    if column_index < len(row):
                        value = row[column_index].strip()
                        stock_data[field_alias] = value if value else None
                    else:
                        stock_data[field_alias] = None
                
                stocks.append(stock_data)
                
    except Exception as e:
        print(f"Error parsing {csv_path}: {e}")
    
    return stocks

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
            
            # Read headers and subheaders manually to handle the complex structure
            reader = csv.reader(f)
            headers = next(reader)
            subheaders = next(reader)
            description_row = next(reader)  # Row with descriptions like 'per share in stock price currency'
            
            # Find the price column index using the description row
            price_column_index = None
            for i, (h, d) in enumerate(zip(headers, description_row)):
                if h == 'Price' and 'per share in stock price currency' in d:
                    price_column_index = i
                    break
            
            # Create field mapping for basic fields
            basic_fields = {
                'symbol': None, 'ISIN': None, 'name': None, 
                'stock price currency': None, 'sector': None, 'country': None
            }
            
            for i, header in enumerate(headers):
                if header in basic_fields:
                    basic_fields[header] = i
            
            # Parse data rows
            for row in reader:
                if len(row) <= max(basic_fields.values() or [0]):
                    continue
                
                # Skip rows that don't have actual stock data (empty symbol, or description rows)
                ticker = (row[basic_fields['symbol']] if basic_fields['symbol'] is not None and basic_fields['symbol'] < len(row) else '').strip()
                if not ticker or ticker == '' or len(ticker) < 2:
                    continue
                    
                # Extract key fields (handle None values)
                stock_data = {
                    'ticker': ticker,
                    'isin': (row[basic_fields['ISIN']] if basic_fields['ISIN'] is not None and basic_fields['ISIN'] < len(row) else '').strip(),
                    'name': (row[basic_fields['name']] if basic_fields['name'] is not None and basic_fields['name'] < len(row) else '').strip(),
                    'currency': (row[basic_fields['stock price currency']] if basic_fields['stock price currency'] is not None and basic_fields['stock price currency'] < len(row) else '').strip(),
                    'sector': (row[basic_fields['sector']] if basic_fields['sector'] is not None and basic_fields['sector'] < len(row) else '').strip(),
                    'country': (row[basic_fields['country']] if basic_fields['country'] is not None and basic_fields['country'] < len(row) else '').strip()
                }
                
                # Extract price if found
                if price_column_index is not None and price_column_index < len(row):
                    try:
                        price_str = row[price_column_index].strip()
                        # Skip non-numeric price values (descriptions, etc.)
                        if price_str and price_str != '' and not price_str.startswith('per share') and not price_str.startswith('BOY') and price_str not in ['Latest', 'N/A']:
                            stock_data['price'] = float(price_str)
                        else:
                            stock_data['price'] = None
                    except (ValueError, AttributeError):
                        stock_data['price'] = None
                else:
                    stock_data['price'] = None
                
                # Only add if ticker exists and looks valid
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

def get_stock_field(ticker, header_name, subtitle_pattern, screen_name=None):
    """
    Get a specific field value for a stock from the screener data
    
    Args:
        ticker: Stock ticker (e.g., 'GRR.AX')
        header_name: Header name (e.g., 'Price')
        subtitle_pattern: Subtitle pattern (e.g., '180d change')
        screen_name: Optional screen name to search in, if None searches all screens
        
    Returns:
        dict: {'ticker': str, 'field': str, 'value': str, 'screen': str} or None if not found
    """
    screens_to_search = []
    
    if screen_name:
        # Search specific screen
        for key, name in UNCLE_STOCK_SCREENS.items():
            if name == screen_name or key == screen_name:
                safe_name = name.replace(' ', '_').replace('/', '_')
                csv_path = f"data/files_exports/{safe_name}_current_screen.csv"
                if os.path.exists(csv_path):
                    screens_to_search.append((name, csv_path))
                break
    else:
        # Search all screens
        for key, name in UNCLE_STOCK_SCREENS.items():
            safe_name = name.replace(' ', '_').replace('/', '_')
            csv_path = f"data/files_exports/{safe_name}_current_screen.csv"
            if os.path.exists(csv_path):
                screens_to_search.append((name, csv_path))
    
    # Search in the screens
    for screen_name_search, csv_path in screens_to_search:
        result = extract_field_data(csv_path, header_name, subtitle_pattern, ticker)
        if result:
            result['screen'] = screen_name_search
            return result
    
    return None

def find_available_fields(csv_path=None):
    """
    Find all available header/subtitle combinations in a CSV file
    
    Args:
        csv_path: Path to CSV file, if None uses first available screen
        
    Returns:
        list: List of tuples (header, subtitle, column_index)
    """
    if csv_path is None:
        # Use first available screen
        for key, name in UNCLE_STOCK_SCREENS.items():
            safe_name = name.replace(' ', '_').replace('/', '_')
            test_path = f"data/files_exports/{safe_name}_current_screen.csv"
            if os.path.exists(test_path):
                csv_path = test_path
                break
        
        if csv_path is None:
            return []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            f.readline()  # skip sep line
            reader = csv.reader(f)
            headers = next(reader)
            subheaders = next(reader)
            description_row = next(reader)
            
            fields = []
            for i, (h, d) in enumerate(zip(headers, description_row)):
                if h and d:  # Both header and description exist
                    fields.append((h, d, i))
            
            return fields
            
    except Exception as e:
        print(f"Error finding fields in {csv_path}: {e}")
        return []

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