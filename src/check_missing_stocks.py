#!/usr/bin/env python3
"""
Check the specific missing stocks to understand why they're filtered out
"""

import json
from pathlib import Path

def check_missing_stocks():
    """Check why DHI, WAVE.PA, and 7187.T are missing"""
    script_dir = Path(__file__).parent
    universe_path = script_dir.parent / 'data' / 'universe.json'

    with open(universe_path, 'r', encoding='utf-8') as f:
        universe_data = json.load(f)

    missing_tickers = ['DHI', 'WAVE.PA', '7187.T']

    for ticker in missing_tickers:
        print(f"\n{ticker}:")
        print("=" * 50)

        occurrences = []
        for screen_name, screen_data in universe_data.get('screens', {}).items():
            for stock in screen_data.get('stocks', []):
                if stock.get('ticker') == ticker:
                    occurrences.append({
                        'screen': screen_name,
                        'quantity': stock.get('quantity', 0),
                        'final_target': stock.get('final_target', 0),
                        'allocation_target': stock.get('allocation_target', 0)
                    })

        for i, occ in enumerate(occurrences, 1):
            print(f"  {i}. Screen: {occ['screen']}")
            print(f"     Quantity: {occ['quantity']}")
            print(f"     Final Target: {occ['final_target']:.2e}")
            print(f"     Allocation Target: {occ['allocation_target']}")

        # Show which one would be picked by extract_unique_stocks (first one)
        if occurrences:
            first = occurrences[0]
            print(f"\n  → extract_unique_stocks picks FIRST occurrence:")
            print(f"    Screen: {first['screen']}, Quantity: {first['quantity']}")
            if first['quantity'] == 0:
                print(f"    ❌ FILTERED OUT because quantity = 0")
            else:
                print(f"    ✅ KEPT because quantity > 0")

if __name__ == "__main__":
    check_missing_stocks()