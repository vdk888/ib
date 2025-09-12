#!/usr/bin/env python3
"""
Currency exchange rate fetcher for Uncle Stock screener
Fetches current exchange rates and updates universe.json with EUR exchange rates
Uses exchangerate-api.com free API
"""

import json
import requests
import os
from typing import Dict, Any

def fetch_exchange_rates() -> Dict[str, float]:
    """
    Fetch current exchange rates with EUR as base currency
    Uses exchangerate-api.com free API
    
    Returns:
        Dict with currency codes as keys and rates as values
    """
    try:
        # Using free exchangerate-api.com API with EUR as base
        url = "https://api.exchangerate-api.com/v4/latest/EUR"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            rates = data.get('rates', {})
            
            # Add EUR itself (1.0 rate)
            rates['EUR'] = 1.0
            
            print(f"+ Fetched exchange rates for {len(rates)} currencies")
            return rates
        else:
            print(f"X API returned status {response.status_code}")
            return {}
            
    except Exception as e:
        print(f"X Error fetching exchange rates: {e}")
        return {}

def get_currencies_from_universe() -> set:
    """
    Extract unique currencies from universe.json
    
    Returns:
        Set of unique currency codes
    """
    universe_path = "data/universe.json"
    if not os.path.exists(universe_path):
        print(f"X {universe_path} not found")
        return set()
    
    currencies = set()
    
    try:
        with open(universe_path, 'r', encoding='utf-8') as f:
            universe_data = json.load(f)
        
        # Extract currencies from screens
        for screen_key, screen_data in universe_data.get('screens', {}).items():
            for stock in screen_data.get('stocks', []):
                currency = stock.get('currency')
                if currency:
                    currencies.add(currency)
        
        # Extract currencies from all_stocks
        for ticker, stock in universe_data.get('all_stocks', {}).items():
            currency = stock.get('currency')
            if currency:
                currencies.add(currency)
        
        print(f"+ Found {len(currencies)} unique currencies: {', '.join(sorted(currencies))}")
        return currencies
        
    except Exception as e:
        print(f"X Error reading universe.json: {e}")
        return set()

def update_universe_with_exchange_rates(exchange_rates: Dict[str, float]) -> bool:
    """
    Update universe.json stocks with EUR exchange rates
    
    Args:
        exchange_rates: Dict with currency codes and their rates to EUR
        
    Returns:
        bool: True if successful, False otherwise
    """
    universe_path = "data/universe.json"
    
    if not os.path.exists(universe_path):
        print(f"X {universe_path} not found")
        return False
    
    try:
        # Load universe data
        with open(universe_path, 'r', encoding='utf-8') as f:
            universe_data = json.load(f)
        
        updated_stocks = 0
        missing_rates = set()
        
        # Update each screen's stocks
        for screen_key, screen_data in universe_data.get('screens', {}).items():
            for stock in screen_data.get('stocks', []):
                currency = stock.get('currency')
                
                if currency in exchange_rates:
                    # Add EUR exchange rate to stock
                    stock['eur_exchange_rate'] = exchange_rates[currency]
                    updated_stocks += 1
                else:
                    missing_rates.add(currency)
        
        # Save updated universe data
        with open(universe_path, 'w', encoding='utf-8') as f:
            json.dump(universe_data, f, indent=2, ensure_ascii=False)
        
        print(f"+ Updated {updated_stocks} stocks with EUR exchange rates")
        
        if missing_rates:
            print(f"X Warning: Missing exchange rates for currencies: {', '.join(sorted(missing_rates))}")
        
        return True
        
    except Exception as e:
        print(f"X Error updating universe.json: {e}")
        return False

def display_exchange_rate_summary(exchange_rates: Dict[str, float]):
    """Display summary of fetched exchange rates"""
    print("\n" + "=" * 50)
    print("EXCHANGE RATES TO EUR")
    print("=" * 50)
    
    for currency in sorted(exchange_rates.keys()):
        rate = exchange_rates[currency]
        if currency == 'EUR':
            print(f"{currency}: {rate:.4f} (base currency)")
        else:
            print(f"{currency}: {rate:.4f} (1 EUR = {rate:.4f} {currency})")

def main():
    """Main currency exchange rate function"""
    print("Uncle Stock Currency Exchange Rate Updater")
    print("=" * 60)
    
    try:
        # Get unique currencies from universe.json
        print("\nStep 1: Analyzing currencies in universe.json...")
        currencies = get_currencies_from_universe()
        
        if not currencies:
            print("X No currencies found in universe.json")
            return False
        
        # Fetch exchange rates
        print("\nStep 2: Fetching current exchange rates...")
        exchange_rates = fetch_exchange_rates()
        
        if not exchange_rates:
            print("X Failed to fetch exchange rates")
            return False
        
        # Display rate summary
        display_exchange_rate_summary(exchange_rates)
        
        # Update universe.json
        print(f"\nStep 3: Updating universe.json with EUR exchange rates...")
        success = update_universe_with_exchange_rates(exchange_rates)
        
        if success:
            print("\n+ Currency exchange rates successfully added to universe.json!")
            print("+ Each stock now has an 'eur_exchange_rate' field")
        else:
            print("\nX Failed to update universe.json with exchange rates")
        
        return success
        
    except Exception as e:
        print(f"X Error in currency exchange rate updater: {e}")
        return False

if __name__ == "__main__":
    main()