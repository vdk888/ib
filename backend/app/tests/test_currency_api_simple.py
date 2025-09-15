"""
Simple API test for Currency Service Step 5
Tests API endpoints directly
"""

import requests
import json

def test_api_endpoints():
    """Test currency API endpoints"""
    base_url = "http://localhost:8000/api/v1"

    print("Testing Currency API Endpoints...")
    print("=" * 50)

    # Test 1: Fetch exchange rates
    print("[TEST] GET /currency/rates")
    try:
        response = requests.get(f"{base_url}/currency/rates", timeout=30)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                rates = data.get("exchange_rates", {}).get("rates", {})
                print(f"[OK] Fetched {len(rates)} exchange rates")
                print(f"   EUR rate: {rates.get('EUR', 'N/A')}")
                print(f"   USD rate: {rates.get('USD', 'N/A')}")
            else:
                print("[FAIL] API returned success=False")
                print(f"   Error: {data.get('error_message', 'Unknown')}")
        else:
            print(f"[FAIL] HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Request failed: {e}")

    print()

    # Test 2: Get currencies from universe
    print("[TEST] GET /universe/currencies")
    try:
        response = requests.get(f"{base_url}/universe/currencies", timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                currencies = data.get("currencies", [])
                print(f"[OK] Found {len(currencies)} currencies")
                print(f"   Currencies: {', '.join(currencies[:5])}{'...' if len(currencies) > 5 else ''}")
            else:
                print("[FAIL] API returned success=False")
        else:
            print(f"[FAIL] HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Request failed: {e}")

    print()

    # Test 3: Run full currency update workflow
    print("[TEST] POST /currency/update")
    try:
        response = requests.post(f"{base_url}/currency/update", timeout=60)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("[OK] Currency update workflow succeeded")
                print(f"   Message: {data.get('workflow_message', '')[:100]}...")
            else:
                print("[FAIL] Currency update workflow failed")
                print(f"   Message: {data.get('workflow_message', 'Unknown error')}")
        else:
            print(f"[FAIL] HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Request failed: {e}")

    print("\n" + "=" * 50)


def test_api_vs_cli_comparison():
    """Compare API vs CLI results"""
    print("API vs CLI Comparison Test...")
    print("=" * 50)

    base_url = "http://localhost:8000/api/v1"

    # Get currencies via API
    try:
        response = requests.get(f"{base_url}/universe/currencies", timeout=10)
        if response.status_code == 200:
            api_currencies = set(response.json().get("currencies", []))
            print(f"[API] Found {len(api_currencies)} currencies")
        else:
            print("[FAIL] API call failed")
            return
    except Exception as e:
        print(f"[FAIL] API test failed: {e}")
        return

    # Get currencies via CLI (import)
    import sys
    sys.path.insert(0, 'src')
    try:
        from currency import get_currencies_from_universe
        cli_currencies = get_currencies_from_universe()
        print(f"[CLI] Found {len(cli_currencies)} currencies")

        # Compare results
        if api_currencies == cli_currencies:
            print("[OK] API and CLI return identical currency lists")
        else:
            print("[PARTIAL] API and CLI return different currency lists")
            api_only = api_currencies - cli_currencies
            cli_only = cli_currencies - api_currencies
            if api_only:
                print(f"   API only: {list(api_only)[:3]}")
            if cli_only:
                print(f"   CLI only: {list(cli_only)[:3]}")

    except Exception as e:
        print(f"[FAIL] CLI comparison failed: {e}")

    print("=" * 50)


if __name__ == "__main__":
    print("Currency Service API Testing")
    print("Please make sure the FastAPI server is running on localhost:8000")
    print("Run: cd backend && uvicorn app.main:app --reload")
    print()

    # Wait for user confirmation
    input("Press Enter when the server is ready...")

    test_api_endpoints()
    test_api_vs_cli_comparison()