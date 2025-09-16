#!/usr/bin/env python3
"""
Create mock backend results using the legacy results to test API output format
"""

import json
import shutil
from pathlib import Path

def create_mock_backend_results():
    """Copy legacy results to backend to test output format"""

    # Source and destination paths
    legacy_ibkr = Path("data/universe_with_ibkr.json")
    backend_ibkr = Path("backend/data/universe_with_ibkr.json")

    if not legacy_ibkr.exists():
        print("Legacy universe_with_ibkr.json not found")
        return False

    # Copy the file to simulate API processing
    print(f"Copying {legacy_ibkr} to {backend_ibkr}")

    # Ensure backend data directory exists
    backend_ibkr.parent.mkdir(parents=True, exist_ok=True)

    # Copy the file
    shutil.copy2(legacy_ibkr, backend_ibkr)

    print(f"Mock backend results created!")
    print(f"Backend file size: {backend_ibkr.stat().st_size:,} bytes")

    return True

def simulate_api_response():
    """Create a simulated API response based on the backend results"""

    backend_ibkr = Path("backend/data/universe_with_ibkr.json")

    if not backend_ibkr.exists():
        print("Backend results file not found")
        return None

    # Load the data
    with open(backend_ibkr, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Calculate statistics like the real API would
    stats = {
        'total': 0,
        'found_isin': 0,
        'found_ticker': 0,
        'found_name': 0,
        'not_found': 0,
        'execution_time_seconds': 127.5  # Mock time
    }

    # Count results
    for screen_name, screen_data in data.get('screens', {}).items():
        for stock in screen_data.get('stocks', []):
            if stock.get('quantity', 0) > 0:
                stats['total'] += 1
                ibkr_details = stock.get('ibkr_details', {})

                if ibkr_details.get('found'):
                    method = ibkr_details.get('search_method', 'unknown')
                    if method == 'isin':
                        stats['found_isin'] += 1
                    elif method == 'ticker':
                        stats['found_ticker'] += 1
                    elif method == 'name':
                        stats['found_name'] += 1
                    else:
                        stats['found_ticker'] += 1  # Default assumption
                else:
                    stats['not_found'] += 1

    # Create API response format
    api_response = {
        "success": True,
        "message": f"IBKR search completed successfully. Processed {stats['total']} stocks with {stats['total'] - stats['not_found']} found.",
        "statistics": stats,
        "output_file": "backend/data/universe_with_ibkr.json"
    }

    return api_response

if __name__ == "__main__":
    print("Creating Mock Backend Results for API Testing")
    print("=" * 50)

    if create_mock_backend_results():
        print("\nSimulating API Response:")
        print("-" * 30)

        api_response = simulate_api_response()
        if api_response:
            # Pretty print the API response
            print(json.dumps(api_response, indent=2))

            print(f"\nAPI Response Summary:")
            print(f"Total stocks processed: {api_response['statistics']['total']}")
            print(f"Found via ISIN: {api_response['statistics']['found_isin']}")
            print(f"Found via ticker: {api_response['statistics']['found_ticker']}")
            print(f"Found via name: {api_response['statistics']['found_name']}")
            print(f"Not found: {api_response['statistics']['not_found']}")

            total_found = (api_response['statistics']['found_isin'] +
                          api_response['statistics']['found_ticker'] +
                          api_response['statistics']['found_name'])
            coverage = (total_found / api_response['statistics']['total']) * 100
            print(f"Coverage: {total_found}/{api_response['statistics']['total']} ({coverage:.1f}%)")

        print(f"\nMock results ready for comparison!")
    else:
        print("Failed to create mock results")