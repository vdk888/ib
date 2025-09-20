"""
Alpaca account information utilities.

This module provides functions to fetch account information from Alpaca Markets API,
including account value, buying power, positions, and trading status.
"""

import os
import logging
from typing import Dict, Any, Optional
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import AssetClass
from alpaca.common.exceptions import APIError

logger = logging.getLogger(__name__)


class AlpacaAccountClient:
    """Client for interacting with Alpaca account information."""

    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None, paper: bool = True):
        """
        Initialize Alpaca trading client.

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
            logger.info(f"Alpaca client initialized (paper mode: {self.paper})")
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca client: {e}")
            raise

    def get_account_info(self) -> Dict[str, Any]:
        """
        Get comprehensive account information.

        Returns:
            Dict containing account details including balance, buying power, etc.
        """
        try:
            account = self.trading_client.get_account()

            # Calculate daily portfolio change
            balance_change = float(account.equity) - float(account.last_equity)
            balance_change_percent = (balance_change / float(account.last_equity)) * 100 if float(account.last_equity) > 0 else 0

            account_info = {
                'account_id': account.id,
                'account_number': account.account_number,
                'status': account.status.value,
                'currency': account.currency,

                # Balances
                'equity': float(account.equity),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'last_equity': float(account.last_equity),

                # Daily changes
                'balance_change': balance_change,
                'balance_change_percent': balance_change_percent,

                # Trading status
                'trading_blocked': account.trading_blocked,
                'transfers_blocked': account.transfers_blocked,
                'account_blocked': account.account_blocked,
                'pattern_day_trader': account.pattern_day_trader,

                # Day trading
                'daytrade_count': account.daytrade_count,
                'daytrading_buying_power': float(account.daytrading_buying_power),

                # Account type info
                'created_at': account.created_at.isoformat() if account.created_at else None,
                'crypto_status': account.crypto_status.value if account.crypto_status else None,
                'options_trading_level': account.options_trading_level,

                # Paper trading indicator
                'paper_trading': self.paper
            }

            logger.info(f"Retrieved account info - Equity: ${account.equity}, Buying Power: ${account.buying_power}")
            return account_info

        except APIError as e:
            logger.error(f"Alpaca API error getting account info: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting account info: {e}")
            raise

    def get_positions(self) -> Dict[str, Any]:
        """
        Get all current positions.

        Returns:
            Dict containing positions information
        """
        try:
            positions = self.trading_client.get_all_positions()

            positions_data = {
                'total_positions': len(positions),
                'positions': []
            }

            total_market_value = 0

            for position in positions:
                position_data = {
                    'symbol': position.symbol,
                    'asset_id': position.asset_id,
                    'asset_class': position.asset_class.value,
                    'quantity': float(position.qty),
                    'market_value': float(position.market_value),
                    'cost_basis': float(position.cost_basis),
                    'unrealized_pl': float(position.unrealized_pl),
                    'unrealized_plpc': float(position.unrealized_plpc),
                    'side': position.side.value,
                    'avg_entry_price': float(position.avg_entry_price),
                    'current_price': float(position.current_price) if position.current_price else None
                }
                positions_data['positions'].append(position_data)
                total_market_value += float(position.market_value)

            positions_data['total_market_value'] = total_market_value

            logger.info(f"Retrieved {len(positions)} positions with total market value: ${total_market_value}")
            return positions_data

        except APIError as e:
            logger.error(f"Alpaca API error getting positions: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting positions: {e}")
            raise

    def get_account_summary(self) -> Dict[str, Any]:
        """
        Get a summary combining account info and positions.

        Returns:
            Dict containing comprehensive account summary
        """
        try:
            account_info = self.get_account_info()
            positions_info = self.get_positions()

            summary = {
                'account': account_info,
                'positions': positions_info,
                'summary': {
                    'total_equity': account_info['equity'],
                    'available_cash': account_info['cash'],
                    'buying_power': account_info['buying_power'],
                    'positions_value': positions_info['total_market_value'],
                    'positions_count': positions_info['total_positions'],
                    'daily_change': account_info['balance_change'],
                    'daily_change_percent': account_info['balance_change_percent'],
                    'trading_allowed': not account_info['trading_blocked']
                }
            }

            return summary

        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            raise


def get_alpaca_account_value(paper: bool = True) -> float:
    """
    Simple function to get Alpaca account value.

    Args:
        paper: Whether to use paper trading (default True for safety)

    Returns:
        Current account equity value
    """
    try:
        client = AlpacaAccountClient(paper=paper)
        account_info = client.get_account_info()
        return account_info['equity']
    except Exception as e:
        logger.error(f"Error getting Alpaca account value: {e}")
        raise


if __name__ == "__main__":
    # Test the account client
    logging.basicConfig(level=logging.INFO)

    try:
        # Initialize client (paper trading by default)
        client = AlpacaAccountClient(paper=True)

        # Get account summary
        summary = client.get_account_summary()

        print("=== Alpaca Account Summary ===")
        print(f"Account Status: {summary['account']['status']}")
        print(f"Total Equity: ${summary['summary']['total_equity']:,.2f}")
        print(f"Available Cash: ${summary['summary']['available_cash']:,.2f}")
        print(f"Buying Power: ${summary['summary']['buying_power']:,.2f}")
        print(f"Positions Value: ${summary['summary']['positions_value']:,.2f}")
        print(f"Number of Positions: {summary['summary']['positions_count']}")
        print(f"Daily Change: ${summary['summary']['daily_change']:,.2f} ({summary['summary']['daily_change_percent']:.2f}%)")
        print(f"Trading Allowed: {summary['summary']['trading_allowed']}")
        print(f"Paper Trading: {summary['account']['paper_trading']}")

        if summary['positions']['positions']:
            print("\n=== Current Positions ===")
            for pos in summary['positions']['positions']:
                print(f"{pos['symbol']}: {pos['quantity']} shares @ ${pos['current_price']:.2f} = ${pos['market_value']:,.2f}")

    except Exception as e:
        print(f"Error: {e}")