#!/usr/bin/env python3
"""
Find stocks with meaningful allocations (final_target > 1e-10) but quantity = 0
"""

import json
from pathlib import Path

def find_meaningful_zero_quantity_stocks():
    """Find stocks with final_target > 1e-10 but quantity = 0"""

    script_dir = Path(__file__).parent
    universe_path = script_dir.parent / 'data' / 'universe.json'

    print(f"Loading universe from: {universe_path}")

    with open(universe_path, 'r', encoding='utf-8') as f:
        universe_data = json.load(f)

    meaningful_zero_stocks = []
    total_stocks = 0
    meaningful_stocks = 0
    zero_quantity_stocks = 0

    # Process all screens
    for screen_name, screen_data in universe_data.get('screens', {}).items():
        for stock in screen_data.get('stocks', []):
            total_stocks += 1

            final_target = stock.get('final_target', 0)
            quantity = stock.get('quantity', 0)

            if final_target > 1e-10:
                meaningful_stocks += 1

            if quantity == 0:
                zero_quantity_stocks += 1

            # Find stocks with meaningful allocation but zero quantity
            if final_target > 1e-10 and quantity == 0:
                meaningful_zero_stocks.append({
                    'ticker': stock.get('ticker'),
                    'name': stock.get('name'),
                    'final_target': final_target,
                    'quantity': quantity,
                    'target_value_eur': stock.get('target_value_eur', 0),
                    'eur_price': stock.get('eur_price', 0),
                    'screen': screen_name,
                    'currency': stock.get('currency'),
                    'country': stock.get('country')
                })

    print(f"\nANALYSIS RESULTS:")
    print(f"Total stocks processed: {total_stocks}")
    print(f"Stocks with meaningful allocations (final_target > 1e-10): {meaningful_stocks}")
    print(f"Stocks with zero quantity: {zero_quantity_stocks}")
    print(f"Stocks with meaningful allocation BUT zero quantity: {len(meaningful_zero_stocks)}")

    if meaningful_zero_stocks:
        print(f"\nTHE {len(meaningful_zero_stocks)} STOCKS WITH MEANINGFUL ALLOCATIONS BUT ZERO QUANTITY:")
        print("=" * 80)

        for i, stock in enumerate(meaningful_zero_stocks, 1):
            print(f"{i}. {stock['ticker']} - {stock['name']}")
            print(f"   Country: {stock['country']}, Currency: {stock['currency']}")
            print(f"   Final Target: {stock['final_target']:.2e}")
            print(f"   Target Value EUR: {stock['target_value_eur']:.6f}")
            print(f"   EUR Price: {stock['eur_price']:.6f}")
            print(f"   Screen: {stock['screen']}")

            # Calculate why it rounded to zero
            if stock['eur_price'] > 0:
                theoretical_quantity = stock['target_value_eur'] / stock['eur_price']
                print(f"   Theoretical quantity: {theoretical_quantity:.6f} shares")
                print(f"   → Rounded to: {int(round(theoretical_quantity))} shares")
            print()
    else:
        print("\n✅ NO STOCKS found with meaningful allocations but zero quantity")
        print("   This suggests the discrepancy is elsewhere in the pipeline")

if __name__ == "__main__":
    find_meaningful_zero_quantity_stocks()