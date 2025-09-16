#!/usr/bin/env python3
"""
Compare API and legacy results
Since IBKR Gateway is not available, we'll compare file structures and data format
"""

import json
import os
from pathlib import Path

def compare_universe_files():
    """Compare universe.json files between backend and legacy data directories"""

    # Paths
    legacy_universe = Path("data/universe.json")
    backend_universe = Path("backend/data/universe.json")
    legacy_ibkr = Path("data/universe_with_ibkr.json")
    backend_ibkr = Path("backend/data/universe_with_ibkr.json")

    print("Comparing Universe Data Files")
    print("=" * 50)

    # Check if files exist
    print(f"Legacy universe.json exists: {legacy_universe.exists()}")
    print(f"Backend universe.json exists: {backend_universe.exists()}")
    print(f"Legacy universe_with_ibkr.json exists: {legacy_ibkr.exists()}")
    print(f"Backend universe_with_ibkr.json exists: {backend_ibkr.exists()}")

    if not legacy_universe.exists():
        print("❌ Legacy universe.json not found")
        return

    if not backend_universe.exists():
        print("❌ Backend universe.json not found")
        return

    # Load and compare universe.json files
    print(f"\nComparing universe.json files...")

    with open(legacy_universe, 'r', encoding='utf-8') as f:
        legacy_data = json.load(f)

    with open(backend_universe, 'r', encoding='utf-8') as f:
        backend_data = json.load(f)

    # Compare basic structure
    print(f"Legacy total stocks: {legacy_data.get('metadata', {}).get('total_stocks', 'N/A')}")
    print(f"Backend total stocks: {backend_data.get('metadata', {}).get('total_stocks', 'N/A')}")

    # Check screens
    legacy_screens = list(legacy_data.get('screens', {}).keys())
    backend_screens = list(backend_data.get('screens', {}).keys())

    print(f"Legacy screens: {legacy_screens}")
    print(f"Backend screens: {backend_screens}")
    print(f"Screens match: {legacy_screens == backend_screens}")

    # Count stocks with quantities > 0
    def count_stocks_with_quantity(data):
        count = 0
        for screen_name, screen_data in data.get('screens', {}).items():
            for stock in screen_data.get('stocks', []):
                if stock.get('quantity', 0) > 0:
                    count += 1
        return count

    legacy_qty_count = count_stocks_with_quantity(legacy_data)
    backend_qty_count = count_stocks_with_quantity(backend_data)

    print(f"\nStocks with quantity > 0:")
    print(f"Legacy: {legacy_qty_count}")
    print(f"Backend: {backend_qty_count}")
    print(f"Match: {legacy_qty_count == backend_qty_count}")

    # If both IBKR files exist, compare them
    if legacy_ibkr.exists() and backend_ibkr.exists():
        print(f"\nComparing universe_with_ibkr.json files...")

        with open(legacy_ibkr, 'r', encoding='utf-8') as f:
            legacy_ibkr_data = json.load(f)

        with open(backend_ibkr, 'r', encoding='utf-8') as f:
            backend_ibkr_data = json.load(f)

        # Compare IBKR search results
        def count_ibkr_found(data):
            found = 0
            not_found = 0
            for screen_name, screen_data in data.get('screens', {}).items():
                for stock in screen_data.get('stocks', []):
                    if stock.get('quantity', 0) > 0:
                        ibkr_details = stock.get('ibkr_details', {})
                        if ibkr_details.get('found'):
                            found += 1
                        else:
                            not_found += 1
            return found, not_found

        legacy_found, legacy_not_found = count_ibkr_found(legacy_ibkr_data)
        backend_found, backend_not_found = count_ibkr_found(backend_ibkr_data)

        print(f"IBKR Search Results:")
        print(f"Legacy - Found: {legacy_found}, Not Found: {legacy_not_found}")
        print(f"Backend - Found: {backend_found}, Not Found: {backend_not_found}")
        print(f"Found counts match: {legacy_found == backend_found}")

        # Sample first few stocks to compare IBKR details format
        print(f"\nSample IBKR Details Comparison:")
        legacy_samples = []
        backend_samples = []

        for screen_name, screen_data in legacy_ibkr_data.get('screens', {}).items():
            for stock in screen_data.get('stocks', []):
                if stock.get('quantity', 0) > 0 and stock.get('ibkr_details', {}).get('found'):
                    legacy_samples.append({
                        'ticker': stock.get('ticker'),
                        'ibkr_details': stock.get('ibkr_details')
                    })
                    if len(legacy_samples) >= 3:
                        break
            if len(legacy_samples) >= 3:
                break

        for screen_name, screen_data in backend_ibkr_data.get('screens', {}).items():
            for stock in screen_data.get('stocks', []):
                if stock.get('quantity', 0) > 0 and stock.get('ibkr_details', {}).get('found'):
                    backend_samples.append({
                        'ticker': stock.get('ticker'),
                        'ibkr_details': stock.get('ibkr_details')
                    })
                    if len(backend_samples) >= 3:
                        break
            if len(backend_samples) >= 3:
                break

        print("Legacy samples:")
        for sample in legacy_samples:
            print(f"  {sample['ticker']}: {sample['ibkr_details']}")

        print("Backend samples:")
        for sample in backend_samples:
            print(f"  {sample['ticker']}: {sample['ibkr_details']}")

    else:
        print(f"\nIBKR result files not available for comparison")
        print(f"  Legacy IBKR file: {'Yes' if legacy_ibkr.exists() else 'No'}")
        print(f"  Backend IBKR file: {'Yes' if backend_ibkr.exists() else 'No'}")

def show_file_sizes():
    """Show file sizes for comparison"""
    print(f"\nFile Sizes:")

    files_to_check = [
        "data/universe.json",
        "backend/data/universe.json",
        "data/universe_with_ibkr.json",
        "backend/data/universe_with_ibkr.json"
    ]

    for file_path in files_to_check:
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size
            print(f"  {file_path}: {size:,} bytes")
        else:
            print(f"  {file_path}: Not found")

if __name__ == "__main__":
    compare_universe_files()
    show_file_sizes()

    print(f"\nComparison complete!")