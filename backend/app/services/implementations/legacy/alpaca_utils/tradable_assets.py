"""
Alpaca tradable assets fetcher.

This module fetches all tradable assets from Alpaca Markets API and saves them to JSON files
for use in the multi-broker routing system. Includes stocks, ETFs, and crypto assets.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetStatus
from alpaca.common.exceptions import APIError

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class AlpacaTradableAssetsFetcher:
    """Fetcher for all tradable assets on Alpaca Markets."""

    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None, paper: bool = True):
        """
        Initialize Alpaca trading client for asset fetching.

        Args:
            api_key: Alpaca API key (defaults to ALPACA_API_KEY env var)
            secret_key: Alpaca secret key (defaults to ALPACA_SECRET_KEY env var)
            paper: Whether to use paper trading (default True)
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
            logger.info(f"Alpaca assets client initialized (paper mode: {self.paper})")
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca client: {e}")
            raise

    def get_us_equity_assets(self) -> List[Dict[str, Any]]:
        """
        Get all US equity assets (stocks and ETFs).

        Returns:
            List of dictionaries containing asset information
        """
        try:
            search_params = GetAssetsRequest(
                asset_class=AssetClass.US_EQUITY,
                status=AssetStatus.ACTIVE
            )
            assets = self.trading_client.get_all_assets(search_params)

            assets_data = []
            for asset in assets:
                asset_data = {
                    'asset_id': str(asset.id),
                    'symbol': asset.symbol,
                    'name': asset.name,
                    'asset_class': asset.asset_class.value,
                    'exchange': asset.exchange.value if asset.exchange else None,
                    'status': asset.status.value,
                    'tradable': asset.tradable,
                    'marginable': asset.marginable,
                    'shortable': asset.shortable,
                    'easy_to_borrow': asset.easy_to_borrow,
                    'fractionable': asset.fractionable,
                }

                # Add optional numeric fields if they exist
                if hasattr(asset, 'min_order_size') and asset.min_order_size:
                    asset_data['min_order_size'] = float(asset.min_order_size)
                if hasattr(asset, 'min_trade_increment') and asset.min_trade_increment:
                    asset_data['min_trade_increment'] = float(asset.min_trade_increment)
                if hasattr(asset, 'price_increment') and asset.price_increment:
                    asset_data['price_increment'] = float(asset.price_increment)
                if hasattr(asset, 'maintenance_margin_requirement') and asset.maintenance_margin_requirement:
                    asset_data['maintenance_margin_requirement'] = float(asset.maintenance_margin_requirement)
                if hasattr(asset, 'attributes'):
                    asset_data['attributes'] = asset.attributes

                assets_data.append(asset_data)

            logger.info(f"Retrieved {len(assets_data)} US equity assets from Alpaca")
            return assets_data

        except APIError as e:
            logger.error(f"Alpaca API error getting US equity assets: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting US equity assets: {e}")
            raise

    def get_crypto_assets(self) -> List[Dict[str, Any]]:
        """
        Get all crypto assets.

        Returns:
            List of dictionaries containing crypto asset information
        """
        try:
            search_params = GetAssetsRequest(
                asset_class=AssetClass.CRYPTO,
                status=AssetStatus.ACTIVE
            )
            assets = self.trading_client.get_all_assets(search_params)

            assets_data = []
            for asset in assets:
                asset_data = {
                    'asset_id': str(asset.id),
                    'symbol': asset.symbol,
                    'name': asset.name,
                    'asset_class': asset.asset_class.value,
                    'exchange': asset.exchange.value if asset.exchange else None,
                    'status': asset.status.value,
                    'tradable': asset.tradable,
                    'marginable': asset.marginable,
                    'shortable': asset.shortable,
                    'easy_to_borrow': asset.easy_to_borrow,
                    'fractionable': asset.fractionable,
                }

                # Add optional numeric fields if they exist
                if hasattr(asset, 'min_order_size') and asset.min_order_size:
                    asset_data['min_order_size'] = float(asset.min_order_size)
                if hasattr(asset, 'min_trade_increment') and asset.min_trade_increment:
                    asset_data['min_trade_increment'] = float(asset.min_trade_increment)
                if hasattr(asset, 'price_increment') and asset.price_increment:
                    asset_data['price_increment'] = float(asset.price_increment)
                if hasattr(asset, 'attributes'):
                    asset_data['attributes'] = asset.attributes

                assets_data.append(asset_data)

            logger.info(f"Retrieved {len(assets_data)} crypto assets from Alpaca")
            return assets_data

        except APIError as e:
            logger.error(f"Alpaca API error getting crypto assets: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting crypto assets: {e}")
            raise

    def get_all_assets(self) -> Dict[str, Any]:
        """
        Get all tradable assets (US equity + crypto).

        Returns:
            Dictionary containing all assets organized by type
        """
        try:
            us_equity_assets = self.get_us_equity_assets()
            crypto_assets = self.get_crypto_assets()

            all_assets = {
                'metadata': {
                    'fetch_timestamp': datetime.now().isoformat(),
                    'paper_trading': self.paper,
                    'total_us_equity_assets': len(us_equity_assets),
                    'total_crypto_assets': len(crypto_assets),
                    'total_assets': len(us_equity_assets) + len(crypto_assets)
                },
                'us_equity': us_equity_assets,
                'crypto': crypto_assets
            }

            logger.info(f"Retrieved total of {all_assets['metadata']['total_assets']} assets from Alpaca")
            return all_assets

        except Exception as e:
            logger.error(f"Error getting all assets: {e}")
            raise

    def save_assets_to_json(self, output_path: Optional[str] = None) -> str:
        """
        Fetch all assets and save to JSON file.

        Args:
            output_path: Path to save JSON file (defaults to data directory)

        Returns:
            Path to the saved JSON file
        """
        try:
            # Get all assets
            all_assets = self.get_all_assets()

            # Determine output path
            if output_path is None:
                # Save to backend/data directory (not backend/app/data)
                # Path: backend/app/services/implementations/legacy/alpaca_utils/ -> backend/data/
                backend_dir = Path(__file__).parent.parent.parent.parent.parent.parent
                data_dir = backend_dir / 'data'
                data_dir.mkdir(exist_ok=True)
                output_path = data_dir / 'alpaca_tradable_assets.json'
            else:
                output_path = Path(output_path)

            # Save to JSON file
            with open(output_path, 'w') as f:
                json.dump(all_assets, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {all_assets['metadata']['total_assets']} assets to {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error saving assets to JSON: {e}")
            raise

    def get_asset_symbols_by_type(self) -> Dict[str, List[str]]:
        """
        Get simple lists of symbols by asset type.

        Returns:
            Dictionary with symbol lists for each asset type
        """
        try:
            all_assets = self.get_all_assets()

            symbols_by_type = {
                'us_equity_symbols': [asset['symbol'] for asset in all_assets['us_equity']],
                'crypto_symbols': [asset['symbol'] for asset in all_assets['crypto']],
                'tradable_us_equity': [asset['symbol'] for asset in all_assets['us_equity'] if asset['tradable']],
                'tradable_crypto': [asset['symbol'] for asset in all_assets['crypto'] if asset['tradable']],
                'fractionable_stocks': [asset['symbol'] for asset in all_assets['us_equity'] if asset['fractionable']],
                'marginable_stocks': [asset['symbol'] for asset in all_assets['us_equity'] if asset['marginable']],
                'shortable_stocks': [asset['symbol'] for asset in all_assets['us_equity'] if asset['shortable']]
            }

            return symbols_by_type

        except Exception as e:
            logger.error(f"Error getting asset symbols by type: {e}")
            raise


def fetch_and_save_alpaca_assets(output_path: Optional[str] = None, paper: bool = True) -> str:
    """
    Convenience function to fetch and save all Alpaca tradable assets.

    Args:
        output_path: Path to save JSON file
        paper: Whether to use paper trading

    Returns:
        Path to the saved JSON file
    """
    try:
        fetcher = AlpacaTradableAssetsFetcher(paper=paper)
        return fetcher.save_assets_to_json(output_path)
    except Exception as e:
        logger.error(f"Error in fetch_and_save_alpaca_assets: {e}")
        raise


if __name__ == "__main__":
    # Test the assets fetcher
    logging.basicConfig(level=logging.INFO)

    try:
        print("=== Alpaca Tradable Assets Fetcher ===")

        # Initialize fetcher (paper trading by default)
        fetcher = AlpacaTradableAssetsFetcher(paper=True)

        # Get asset counts by type
        print("\nFetching asset counts...")
        us_equity = fetcher.get_us_equity_assets()
        crypto = fetcher.get_crypto_assets()

        print(f"US Equity Assets (stocks/ETFs): {len(us_equity)}")
        print(f"Crypto Assets: {len(crypto)}")

        # Show some examples
        print(f"\nSample US Equity Assets:")
        for asset in us_equity[:5]:
            print(f"  {asset['symbol']}: {asset['name']} (tradable: {asset['tradable']}, fractionable: {asset['fractionable']})")

        print(f"\nSample Crypto Assets:")
        for asset in crypto[:5]:
            print(f"  {asset['symbol']}: {asset['name']} (tradable: {asset['tradable']})")

        # Save to JSON
        print(f"\nSaving all assets to JSON file...")
        output_file = fetcher.save_assets_to_json()
        print(f"Assets saved to: {output_file}")

        # Get symbols by type
        symbols_by_type = fetcher.get_asset_symbols_by_type()
        print(f"\nAsset Symbol Summary:")
        print(f"  Total US Equity Symbols: {len(symbols_by_type['us_equity_symbols'])}")
        print(f"  Total Crypto Symbols: {len(symbols_by_type['crypto_symbols'])}")
        print(f"  Tradable US Equity: {len(symbols_by_type['tradable_us_equity'])}")
        print(f"  Tradable Crypto: {len(symbols_by_type['tradable_crypto'])}")
        print(f"  Fractionable Stocks: {len(symbols_by_type['fractionable_stocks'])}")
        print(f"  Marginable Stocks: {len(symbols_by_type['marginable_stocks'])}")
        print(f"  Shortable Stocks: {len(symbols_by_type['shortable_stocks'])}")

    except Exception as e:
        print(f"Error: {e}")
        logger.exception("Full error details:")