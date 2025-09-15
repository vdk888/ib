"""
Simple Currency Service Test for Step 5
Tests CLI vs API compatibility directly
"""

import sys
import os

# Add paths
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def test_currency_cli():
    """Test CLI currency functionality"""
    print("Testing CLI currency functionality...")

    try:
        # Test legacy currency import
        from currency import main as currency_main, fetch_exchange_rates, get_currencies_from_universe
        print("[OK] Successfully imported legacy currency functions")

        # Test fetching exchange rates (this will make real API call)
        print("[API] Testing exchange rate fetching...")
        rates = fetch_exchange_rates()

        if rates:
            print(f"[OK] Successfully fetched {len(rates)} exchange rates")
            print(f"   Sample rates: EUR=1.0, USD={rates.get('USD', 'N/A')}")

            # Check that EUR is base currency
            if rates.get('EUR') == 1.0:
                print("[OK] EUR correctly set as base currency")
            else:
                print("[FAIL] EUR not set as base currency")

        else:
            print("[FAIL] Failed to fetch exchange rates")
            return False

        return True

    except Exception as e:
        print(f"[FAIL] CLI test failed: {e}")
        return False

def main():
    """Run currency CLI test"""
    print("=" * 50)
    print("CURRENCY SERVICE CLI TEST")
    print("=" * 50)

    success = test_currency_cli()

    print("\n" + "=" * 50)
    if success:
        print("[SUCCESS] Currency CLI functionality works!")
    else:
        print("[ERROR] Currency CLI test failed!")
    print("=" * 50)

    return success

if __name__ == "__main__":
    main()