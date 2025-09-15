"""
AccountService implementation wrapping legacy qty.py IBKR functionality
Maintains 100% behavioral compatibility with CLI step7_calculate_quantities()
"""

import asyncio
import sys
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Add legacy directory to path for imports
legacy_path = Path(__file__).parent / "legacy"
sys.path.append(str(legacy_path))

from ib_utils.ib_fetch import IBApi
from ..interfaces import IAccountService


class AccountService(IAccountService):
    """
    IBKR account service implementation
    Wraps legacy ib_fetch.py functionality with async interface
    """

    def __init__(self):
        """Initialize AccountService with IBKR configuration"""
        self.host = "127.0.0.1"
        self.port = 4002  # Paper trading port
        self.client_id = 3  # Same as legacy implementation
        self.connection_timeout = 10
        self.account_id_timeout = 2
        self.data_timeout = 3

    async def get_account_total_value(self) -> Tuple[Optional[float], Optional[str]]:
        """
        Connect to IBKR and fetch account net liquidation value

        Maintains exact behavioral compatibility with legacy get_account_total_value()
        """
        print("Connecting to IBKR to get account value...")

        # Run IBKR connection in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_get_account_value)

    def _sync_get_account_value(self) -> Tuple[Optional[float], Optional[str]]:
        """
        Synchronous IBKR account value fetching (exact legacy behavior)
        """
        # Initialize API client
        app = IBApi()

        try:
            # Connect to IB Gateway (paper trading port 4002)
            app.connect(self.host, self.port, clientId=self.client_id)

            # Start message processing in separate thread
            api_thread = threading.Thread(target=app.run, daemon=True)
            api_thread.start()

            # Wait for connection
            start_time = time.time()
            while not app.connected and (time.time() - start_time) < self.connection_timeout:
                time.sleep(0.1)

            if not app.connected:
                print("Failed to connect to IB Gateway")
                return None, None

            # Wait a moment for account ID
            time.sleep(self.account_id_timeout)

            if not app.account_id:
                print("No account ID received")
                return None, None

            # Request account summary
            app.reqAccountSummary(9002, "All", "NetLiquidation")

            # Wait for data to be received
            time.sleep(self.data_timeout)

            # Cancel subscription
            app.cancelAccountSummary(9002)

            # Get total value
            total_value = None
            currency = None
            if "NetLiquidation" in app.account_summary:
                total_value = float(app.account_summary["NetLiquidation"]["value"])
                currency = app.account_summary["NetLiquidation"]["currency"]
                print(f"Account Total Value: ${total_value:,.2f} {currency}")

            # Disconnect
            app.disconnect()

            return total_value, currency

        except Exception as e:
            print(f"Error fetching account value: {e}")
            try:
                app.disconnect()
            except:
                pass
            return None, None

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test IBKR connection without fetching account data
        """
        start_time = time.time()
        result = {
            "connected": False,
            "account_id": None,
            "connection_time": 0.0,
            "error_message": None
        }

        app = IBApi()

        try:
            # Connect to IB Gateway
            app.connect(self.host, self.port, clientId=self.client_id + 100)  # Different client ID

            # Start message processing
            api_thread = threading.Thread(target=app.run, daemon=True)
            api_thread.start()

            # Wait for connection
            timeout_start = time.time()
            while not app.connected and (time.time() - timeout_start) < self.connection_timeout:
                time.sleep(0.1)

            if app.connected:
                # Wait for account ID
                time.sleep(self.account_id_timeout)

                result["connected"] = True
                result["account_id"] = app.account_id
                result["connection_time"] = time.time() - start_time
            else:
                result["error_message"] = "Connection timeout"

        except Exception as e:
            result["error_message"] = str(e)

        finally:
            try:
                app.disconnect()
            except:
                pass

            if not result["connected"]:
                result["connection_time"] = time.time() - start_time

        return result