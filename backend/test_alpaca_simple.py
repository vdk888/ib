"""
Simple test script to debug Alpaca API connection.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if credentials are loaded
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

print(f"API Key loaded: {api_key[:10]}..." if api_key else "API Key: None")
print(f"Secret Key loaded: {secret_key[:10]}..." if secret_key else "Secret Key: None")

if not api_key or not secret_key:
    print("ERROR: Credentials not found in environment variables")
    exit(1)

try:
    from alpaca.trading.client import TradingClient

    # Test paper trading
    print("\nTesting Paper Trading...")
    paper_client = TradingClient(api_key, secret_key, paper=True)

    try:
        account = paper_client.get_account()
        print(f"SUCCESS: Paper trading connection successful!")
        print(f"Account Status: {account.status}")
        print(f"Equity: ${account.equity}")
        print(f"Buying Power: ${account.buying_power}")
        print(f"Cash: ${account.cash}")
    except Exception as e:
        print(f"FAILED: Paper trading failed: {e}")

    # Test live trading
    print("\nTesting Live Trading...")
    live_client = TradingClient(api_key, secret_key, paper=False)

    try:
        account = live_client.get_account()
        print(f"SUCCESS: Live trading connection successful!")
        print(f"Account Status: {account.status}")
        print(f"Equity: ${account.equity}")
        print(f"Buying Power: ${account.buying_power}")
        print(f"Cash: ${account.cash}")
    except Exception as e:
        print(f"FAILED: Live trading failed: {e}")

except ImportError as e:
    print(f"ERROR: Import error: {e}")
except Exception as e:
    print(f"ERROR: Unexpected error: {e}")