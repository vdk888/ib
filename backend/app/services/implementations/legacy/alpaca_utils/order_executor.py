"""
Alpaca order execution utilities.

This module provides functions to submit buy/sell market orders to Alpaca Markets
with GTC (Good Till Canceled) validity. Supports both share quantities and notional amounts.
"""

import os
import logging
from typing import Dict, Any, Optional, Union, List
from decimal import Decimal
from datetime import datetime

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus, OrderClass
from alpaca.common.exceptions import APIError

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class AlpacaOrderExecutor:
    """Order execution client for Alpaca Markets."""

    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None, paper: bool = True):
        """
        Initialize Alpaca trading client for order execution.

        Args:
            api_key: Alpaca API key (defaults to ALPACA_API_KEY env var)
            secret_key: Alpaca secret key (defaults to ALPACA_SECRET_KEY env var)
            paper: Whether to use paper trading (default True for safety)
        """
        self.api_key = api_key or os.getenv('ALPACA_API_KEY')
        self.secret_key = secret_key or os.getenv('ALPACA_SECRET_KEY')
        self.paper = paper

        if not self.api_key or not self.secret_key:
            raise ValueError("Alpaca API credentials not found. Set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables.")

        try:
            self.trading_client = TradingClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
                paper=self.paper
            )
            logger.info(f"Alpaca order executor initialized (paper mode: {self.paper})")
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca trading client: {e}")
            raise

    def submit_market_order(
        self,
        symbol: str,
        side: str,
        qty: Optional[Union[int, float, Decimal]] = None,
        notional: Optional[Union[int, float, Decimal]] = None,
        time_in_force: str = "GTC",
        client_order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a market order (buy or sell) with GTC validity.

        Args:
            symbol: Stock symbol (e.g., "AAPL", "SPY")
            side: Order side - "BUY" or "SELL"
            qty: Number of shares (use qty OR notional, not both)
            notional: Dollar amount to trade (use qty OR notional, not both)
            time_in_force: Time in force (default "GTC" - Good Till Canceled)
            client_order_id: Optional client-assigned order ID

        Returns:
            Dictionary containing order details

        Raises:
            ValueError: If invalid parameters are provided
            APIError: If Alpaca API returns an error
        """
        try:
            # Validate inputs
            if not symbol:
                raise ValueError("Symbol is required")

            if (qty is None and notional is None) or (qty is not None and notional is not None):
                raise ValueError("Must specify either qty or notional, but not both")

            # Convert side string to enum
            if side.upper() == "BUY":
                order_side = OrderSide.BUY
            elif side.upper() == "SELL":
                order_side = OrderSide.SELL
            else:
                raise ValueError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'")

            # Convert time_in_force string to enum
            if time_in_force.upper() == "GTC":
                tif = TimeInForce.GTC
            elif time_in_force.upper() == "DAY":
                tif = TimeInForce.DAY
            elif time_in_force.upper() == "IOC":
                tif = TimeInForce.IOC
            elif time_in_force.upper() == "FOK":
                tif = TimeInForce.FOK
            else:
                raise ValueError(f"Invalid time_in_force: {time_in_force}")

            # Create market order request
            if qty is not None:
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=float(qty),
                    side=order_side,
                    time_in_force=tif,
                    client_order_id=client_order_id
                )
            else:  # notional is not None
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    notional=float(notional),
                    side=order_side,
                    time_in_force=tif,
                    client_order_id=client_order_id
                )

            # Submit order
            order = self.trading_client.submit_order(order_data=order_request)

            # Convert to dictionary for consistent return format
            order_details = {
                'order_id': str(order.id),
                'client_order_id': order.client_order_id,
                'symbol': order.symbol,
                'asset_id': str(order.asset_id),
                'asset_class': order.asset_class.value,
                'side': order.side.value,
                'order_class': order.order_class.value,
                'order_type': order.order_type.value,
                'qty': float(order.qty) if order.qty else None,
                'notional': float(order.notional) if order.notional else None,
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'status': order.status.value,
                'time_in_force': order.time_in_force.value,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'updated_at': order.updated_at.isoformat() if order.updated_at else None,
                'submitted_at': order.submitted_at.isoformat() if order.submitted_at else None,
                'filled_at': order.filled_at.isoformat() if order.filled_at else None,
                'expired_at': order.expired_at.isoformat() if order.expired_at else None,
                'canceled_at': order.canceled_at.isoformat() if order.canceled_at else None,
                'failed_at': order.failed_at.isoformat() if order.failed_at else None,
                'paper_trading': self.paper
            }

            logger.info(f"Market {side.lower()} order submitted - Symbol: {symbol}, Order ID: {order.id}, Status: {order.status.value}")
            return order_details

        except APIError as e:
            logger.error(f"Alpaca API error submitting market order: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error submitting market order: {e}")
            raise

    def buy_market_order(
        self,
        symbol: str,
        qty: Optional[Union[int, float, Decimal]] = None,
        notional: Optional[Union[int, float, Decimal]] = None,
        time_in_force: str = "GTC",
        client_order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a market buy order with GTC validity.

        Args:
            symbol: Stock symbol
            qty: Number of shares to buy
            notional: Dollar amount to buy
            time_in_force: Time in force (default "GTC")
            client_order_id: Optional client order ID

        Returns:
            Dictionary containing order details
        """
        return self.submit_market_order(
            symbol=symbol,
            side="BUY",
            qty=qty,
            notional=notional,
            time_in_force=time_in_force,
            client_order_id=client_order_id
        )

    def sell_market_order(
        self,
        symbol: str,
        qty: Optional[Union[int, float, Decimal]] = None,
        notional: Optional[Union[int, float, Decimal]] = None,
        time_in_force: str = "GTC",
        client_order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a market sell order with GTC validity.

        Args:
            symbol: Stock symbol
            qty: Number of shares to sell
            notional: Dollar amount to sell
            time_in_force: Time in force (default "GTC")
            client_order_id: Optional client order ID

        Returns:
            Dictionary containing order details
        """
        return self.submit_market_order(
            symbol=symbol,
            side="SELL",
            qty=qty,
            notional=notional,
            time_in_force=time_in_force,
            client_order_id=client_order_id
        )

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get the current status of an order.

        Args:
            order_id: Alpaca order ID

        Returns:
            Dictionary containing order status details
        """
        try:
            order = self.trading_client.get_order_by_id(order_id)

            order_status = {
                'order_id': str(order.id),
                'client_order_id': order.client_order_id,
                'symbol': order.symbol,
                'side': order.side.value,
                'qty': float(order.qty) if order.qty else None,
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'status': order.status.value,
                'time_in_force': order.time_in_force.value,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'filled_at': order.filled_at.isoformat() if order.filled_at else None,
                'is_filled': order.status.value == 'filled',
                'is_canceled': order.status.value == 'canceled',
                'is_pending': order.status.value in ['new', 'accepted', 'pending_new', 'partially_filled']
            }

            logger.info(f"Retrieved order status - Order ID: {order_id}, Status: {order.status.value}")
            return order_status

        except APIError as e:
            logger.error(f"Alpaca API error getting order status: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting order status: {e}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.

        Args:
            order_id: Alpaca order ID

        Returns:
            True if cancellation was successful
        """
        try:
            self.trading_client.cancel_order_by_id(order_id)
            logger.info(f"Order canceled - Order ID: {order_id}")
            return True

        except APIError as e:
            logger.error(f"Alpaca API error canceling order: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error canceling order: {e}")
            raise

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all open orders, optionally filtered by symbol.

        Args:
            symbol: Optional symbol to filter by

        Returns:
            List of dictionaries containing open order details
        """
        try:
            # Create request for open orders (use specific open statuses)
            request = GetOrdersRequest(
                status="open",  # Use string instead of enum
                symbols=[symbol] if symbol else None
            )

            orders = self.trading_client.get_orders(request)

            open_orders = []
            for order in orders:
                order_data = {
                    'order_id': str(order.id),
                    'client_order_id': order.client_order_id,
                    'symbol': order.symbol,
                    'side': order.side.value,
                    'qty': float(order.qty) if order.qty else None,
                    'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                    'status': order.status.value,
                    'time_in_force': order.time_in_force.value,
                    'created_at': order.created_at.isoformat() if order.created_at else None
                }
                open_orders.append(order_data)

            logger.info(f"Retrieved {len(open_orders)} open orders" + (f" for {symbol}" if symbol else ""))
            return open_orders

        except APIError as e:
            logger.error(f"Alpaca API error getting open orders: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting open orders: {e}")
            raise


# Convenience functions for quick order execution
def alpaca_buy_market_gtc(symbol: str, qty: Union[int, float], paper: bool = True) -> Dict[str, Any]:
    """
    Convenience function to place a market buy order with GTC validity.

    Args:
        symbol: Stock symbol
        qty: Number of shares to buy
        paper: Use paper trading (default True)

    Returns:
        Order details dictionary
    """
    executor = AlpacaOrderExecutor(paper=paper)
    return executor.buy_market_order(symbol=symbol, qty=qty, time_in_force="GTC")


def alpaca_sell_market_gtc(symbol: str, qty: Union[int, float], paper: bool = True) -> Dict[str, Any]:
    """
    Convenience function to place a market sell order with GTC validity.

    Args:
        symbol: Stock symbol
        qty: Number of shares to sell
        paper: Use paper trading (default True)

    Returns:
        Order details dictionary
    """
    executor = AlpacaOrderExecutor(paper=paper)
    return executor.sell_market_order(symbol=symbol, qty=qty, time_in_force="GTC")


if __name__ == "__main__":
    # Test the order executor
    logging.basicConfig(level=logging.INFO)

    try:
        print("=== Alpaca Order Executor Test ===")

        # Initialize executor (paper trading by default)
        executor = AlpacaOrderExecutor(paper=True)

        # Example: Test buy order (small quantity for testing)
        print("\nTesting Market Buy Order...")
        test_symbol = "SPY"
        test_qty = 0.1  # Small fractional share for testing

        # Check if we can trade fractional shares of this symbol first
        print(f"Placing test buy order: {test_qty} shares of {test_symbol}")

        # Note: This will place a real order in paper trading
        # Uncomment the line below to actually test order placement
        # buy_order = executor.buy_market_order(symbol=test_symbol, qty=test_qty)
        # print(f"Buy order placed: {buy_order}")

        print("Order execution test completed (actual order placement commented out for safety)")

        # Test getting open orders
        print("\nGetting open orders...")
        open_orders = executor.get_open_orders()
        print(f"Found {len(open_orders)} open orders")

        if open_orders:
            print("Open orders:")
            for order in open_orders[:3]:  # Show first 3 orders
                print(f"  {order['symbol']}: {order['side']} {order['qty']} shares (Status: {order['status']})")

    except Exception as e:
        print(f"Error: {e}")
        logger.exception("Full error details:")