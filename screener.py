#!/usr/bin/env python3
"""
Lightweight Uncle Stock API screener functions
Fetches current stocks and screener history from saved queries
"""

import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import constants from environment variables with fallback
UNCLE_STOCK_USER_ID = os.getenv("UNCLE_STOCK_USER_ID", "missing id")
UNCLE_STOCK_QUERY_NAME = "Graham"

def get_current_stocks(user_id=None, query_name=None, max_results=200):
    """
    Fetch current stocks from a saved Uncle Stock screener query
    
    Args:
        user_id: Uncle Stock user ID (defaults to config)
        query_name: Saved query name (defaults to config) 
        max_results: Maximum number of stocks to return
        
    Returns:
        dict: {'success': bool, 'data': list/str, 'raw_response': str}
    """
    user_id = user_id or UNCLE_STOCK_USER_ID
    query_name = query_name or UNCLE_STOCK_QUERY_NAME
    
    params = {
        'user': user_id,
        'query': query_name,
        'results': max_results,
        'owner': user_id
    }
    
    try:
        response = requests.get(
            "https://www.unclestock.com/csv", 
            params=params, 
            timeout=60
        )
        
        if response.status_code == 200:
            # Save raw CSV response to file with screen name prefix
            # Replace spaces with underscores for filename
            safe_query_name = query_name.replace(' ', '_').replace('/', '_')
            csv_filename = f"files_exports/{safe_query_name}_current_screen.csv"
            
            # Ensure the files_exports directory exists
            os.makedirs("files_exports", exist_ok=True)
            
            try:
                with open(csv_filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"Saved {query_name} current stocks CSV to: {csv_filename}")
            except Exception as save_error:
                print(f"Warning: Could not save CSV file: {save_error}")
            
            # Parse CSV to extract symbols
            lines = response.text.split('\n')
            symbols = []
            
            # Skip metadata and header lines
            data_lines = [line for line in lines if line and not line.startswith('sep=')]
            if len(data_lines) > 1:
                for line in data_lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.split(',')
                        if parts:
                            symbol = parts[0].strip('"').strip()
                            if symbol:
                                symbols.append(symbol)
            
            return {
                'success': True,
                'data': symbols,
                'raw_response': response.text,
                'csv_file': csv_filename
            }
        else:
            return {
                'success': False,
                'data': f"API returned status {response.status_code}",
                'raw_response': response.text
            }
            
    except Exception as e:
        return {
            'success': False,
            'data': str(e),
            'raw_response': None
        }

def get_screener_history(user_id=None, query_name=None):
    """
    Fetch screener backtest history from a saved Uncle Stock query
    
    Args:
        user_id: Uncle Stock user ID (defaults to config)
        query_name: Saved query name (defaults to config)
        
    Returns:
        dict: {'success': bool, 'data': dict/str, 'raw_response': str}
    """
    user_id = user_id or UNCLE_STOCK_USER_ID
    query_name = query_name or UNCLE_STOCK_QUERY_NAME
    
    params = {
        'user': user_id,
        'query': query_name,
        'owner': user_id
    }
    
    try:
        response = requests.get(
            "https://www.unclestock.com/backtest-result", 
            params=params, 
            timeout=60
        )
        
        if response.status_code == 200:
            # Save raw CSV response to file with consistent naming
            # Replace spaces with underscores for filename
            safe_query_name = query_name.replace(' ', '_').replace('/', '_')
            csv_filename = f"files_exports/{safe_query_name}_backtest_results.csv"
            
            # Ensure the files_exports directory exists
            os.makedirs("files_exports", exist_ok=True)
            
            try:
                with open(csv_filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"Saved {query_name} backtest results CSV to: {csv_filename}")
            except Exception as save_error:
                print(f"Warning: Could not save CSV file: {save_error}")
            
            # Parse CSV to structured data
            lines = response.text.split('\n')
            history_data = {}
            
            for line in lines:
                if line.strip() and ',' in line:
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        key = parts[0].strip('"').strip()
                        value = parts[1].strip('"').strip()
                        if key and value:
                            history_data[key] = value
            
            return {
                'success': True,
                'data': history_data,
                'raw_response': response.text,
                'csv_file': csv_filename
            }
        else:
            return {
                'success': False,
                'data': f"API returned status {response.status_code}",
                'raw_response': response.text
            }
            
    except Exception as e:
        return {
            'success': False,
            'data': str(e),
            'raw_response': None
        }

if __name__ == "__main__":
    # Test both functions
    print("Testing Uncle Stock Screener Functions")
    print("=" * 50)
    
    print("\n1. Testing current stocks...")
    stocks_result = get_current_stocks()
    print(f"Success: {stocks_result['success']}")
    if stocks_result['success']:
        print(f"Found {len(stocks_result['data'])} stocks: {stocks_result['data'][:5]}...")
    else:
        print(f"Error: {stocks_result['data']}")
    
    print("\n2. Testing screener history...")
    history_result = get_screener_history()
    print(f"Success: {history_result['success']}")
    if history_result['success']:
        print(f"History data: {history_result['data']}")
    else:
        print(f"Error: {history_result['data']}")