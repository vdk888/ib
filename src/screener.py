#!/usr/bin/env python3
"""
Lightweight Uncle Stock API screener functions
Fetches current stocks and screener history from saved queries
"""

import requests
import json
import os
from datetime import datetime
from config import UNCLE_STOCK_USER_ID, UNCLE_STOCK_SCREENS

def get_current_stocks(user_id=None, query_name=None, max_results=200):
    """
    Fetch current stocks from a saved Uncle Stock screener query
    
    Args:
        user_id: Uncle Stock user ID (defaults to config)
        query_name: Saved query name (must be provided or will return error) 
        max_results: Maximum number of stocks to return
        
    Returns:
        dict: {'success': bool, 'data': list/str, 'raw_response': str}
    """
    user_id = user_id or UNCLE_STOCK_USER_ID
    
    if not query_name:
        return {
            'success': False,
            'data': "Query name must be provided",
            'raw_response': None
        }
    
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
            csv_filename = f"data/files_exports/{safe_query_name}_current_screen.csv"
            
            # Ensure the data/files_exports directory exists
            os.makedirs("data/files_exports", exist_ok=True)
            
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
        query_name: Saved query name (must be provided or will return error)
        
    Returns:
        dict: {'success': bool, 'data': dict/str, 'raw_response': str}
    """
    user_id = user_id or UNCLE_STOCK_USER_ID
    
    if not query_name:
        return {
            'success': False,
            'data': "Query name must be provided",
            'raw_response': None
        }
    
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
            csv_filename = f"data/files_exports/{safe_query_name}_backtest_results.csv"
            
            # Ensure the data/files_exports directory exists
            os.makedirs("data/files_exports", exist_ok=True)
            
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

def get_all_screeners():
    """
    Fetch current stocks from all configured screeners
    
    Returns:
        dict: Results for each screener
    """
    results = {}
    
    for key, screen_name in UNCLE_STOCK_SCREENS.items():
        print(f"\nFetching stocks for {screen_name}...")
        result = get_current_stocks(query_name=screen_name)
        results[key] = result
        
        if result['success']:
            print(f"+ Found {len(result['data'])} stocks for {screen_name}")
        else:
            print(f"X Error fetching {screen_name}: {result['data']}")
    
    return results

def get_all_screener_histories():
    """
    Fetch backtest history from all configured screeners
    
    Returns:
        dict: History results for each screener
    """
    results = {}
    
    for key, screen_name in UNCLE_STOCK_SCREENS.items():
        print(f"\nFetching history for {screen_name}...")
        result = get_screener_history(query_name=screen_name)
        results[key] = result
        
        if result['success']:
            print(f"+ Retrieved history for {screen_name}")
        else:
            print(f"X Error fetching history for {screen_name}: {result['data']}")
    
    return results

if __name__ == "__main__":
    # Test all screeners from config
    print("Testing Uncle Stock Screener Functions")
    print("=" * 50)
    
    print("\n1. Testing current stocks for all screeners...")
    all_stocks = get_all_screeners()
    
    print("\n2. Testing screener history for all screeners...")
    all_histories = get_all_screener_histories()
    
    print("\n" + "=" * 50)
    print("Summary:")
    for key, screen_name in UNCLE_STOCK_SCREENS.items():
        stocks_result = all_stocks.get(key, {})
        history_result = all_histories.get(key, {})
        
        print(f"\n{screen_name}:")
        if stocks_result.get('success'):
            print(f"  Stocks: {len(stocks_result['data'])} found")
        else:
            print(f"  Stocks: Failed")
        
        if history_result.get('success'):
            print(f"  History: Retrieved")
        else:
            print(f"  History: Failed")