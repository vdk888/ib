#!/usr/bin/env python3
"""
Rebalancing Service Implementation
Wraps src/rebalancer.py functions to provide API interface for portfolio rebalancing
Maintains 100% behavioral compatibility with CLI step9_rebalancer()
"""

import json
import os
import time
import threading
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import asyncio

# Import the legacy rebalancer classes directly
import sys
import os
# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'src')
sys.path.insert(0, src_path)

from rebalancer import IBRebalancerApi, PortfolioRebalancer

from ..interfaces import IRebalancingService


class RebalancingService(IRebalancingService):
    """
    Rebalancing service wrapping legacy PortfolioRebalancer functionality
    Provides API interface while maintaining 100% CLI compatibility
    """

    def __init__(self):
        self.rebalancer = None

    def load_universe_data(self, universe_file: str) -> Dict[str, Any]:
        """
        Load universe data with IBKR details and target quantities

        Args:
            universe_file: Path to universe_with_ibkr.json file

        Returns:
            Dict containing complete universe data structure

        Raises:
            FileNotFoundError: If universe file does not exist
        """
        print("[DATA] Loading universe data...")

        # Ensure absolute path
        if not os.path.isabs(universe_file):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            universe_file = os.path.join(project_root, universe_file)

        if not os.path.exists(universe_file):
            raise FileNotFoundError(f"Universe file not found: {universe_file}")

        with open(universe_file, 'r') as f:
            universe_data = json.load(f)

        print(f"[OK] Loaded universe with {universe_data['metadata']['total_stocks']} stocks")
        print(f"[OK] Screens: {', '.join(universe_data['metadata']['screens'])}")

        return universe_data

    def calculate_target_quantities(self, universe_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Calculate target quantities by aggregating across all screens for each IBKR symbol

        Args:
            universe_data: Complete universe data from load_universe_data()

        Returns:
            Dict mapping IBKR symbol to total target quantity

        Side Effects:
            Prints progress to console for target calculation
        """
        print("\n[TARGET] Calculating target quantities...")

        # Dictionary to accumulate quantities by IBKR symbol
        symbol_quantities = defaultdict(int)
        symbol_details = {}  # Store IBKR details for each symbol

        # Process each screen
        for screen_name, screen_data in universe_data['screens'].items():
            screen_count = len(screen_data['stocks'])
            print(f"  Processing {screen_name}: {screen_count} stocks")

            for stock in screen_data['stocks']:
                # Skip stocks without IBKR details
                if not stock.get('ibkr_details', {}).get('found', False):
                    continue

                ibkr_symbol = stock['ibkr_details']['symbol']
                target_quantity = stock.get('quantity', 0)

                # Add to total quantity for this symbol
                symbol_quantities[ibkr_symbol] += target_quantity

                # Store IBKR details (will be overwritten but should be same for same symbol)
                symbol_details[ibkr_symbol] = {
                    'ticker': stock['ticker'],
                    'name': stock['name'],
                    'currency': stock['currency'],
                    'sector': stock['sector'],
                    'country': stock['country'],
                    'screens': stock.get('screens', []),
                    'ibkr_details': stock['ibkr_details']
                }

        target_quantities = dict(symbol_quantities)

        print(f"[OK] Calculated targets for {len(target_quantities)} unique symbols")

        # Show top 10 targets
        sorted_targets = sorted(target_quantities.items(),
                               key=lambda x: x[1], reverse=True)
        print("  Top 10 targets:")
        for symbol, qty in sorted_targets[:10]:
            screens = ", ".join(symbol_details[symbol]['screens'])
            print(f"    {symbol}: {qty:,} shares ({screens})")

        # Store symbol details for later use
        self.symbol_details = symbol_details

        return target_quantities

    def fetch_current_positions(self) -> Tuple[Dict[str, int], Dict[str, Dict[str, Any]]]:
        """
        Fetch current positions from IBKR account via live API connection

        Returns:
            Tuple of (current_positions, contract_details)
            - current_positions: Dict mapping symbol to current quantity
            - contract_details: Dict mapping symbol to IBKR contract info

        Side Effects:
            - Establishes connection to IBKR Gateway (127.0.0.1:4002)
            - Prints connection status and position data to console
            - Uses threading for IBKR API message processing

        Raises:
            Exception: If connection to IBKR Gateway fails or timeout
        """
        print("\n[FETCH] Fetching current positions from IBKR...")

        # Initialize API client
        app = IBRebalancerApi()

        # Connect to IB Gateway
        app.connect("127.0.0.1", 4002, clientId=10)

        # Start message processing thread
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()

        # Wait for connection
        timeout = 10
        start_time = time.time()
        while not app.connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)

        if not app.connected:
            raise Exception("Failed to connect to IB Gateway")

        # Wait for account ID
        time.sleep(2)
        if not app.account_id:
            raise Exception("No account ID received")

        # Request positions
        app.reqPositions()
        app.reqAccountUpdates(True, app.account_id)

        # Wait for data
        start_time = time.time()
        while not app.data_ready and (time.time() - start_time) < 10:
            time.sleep(0.1)

        if not app.data_ready:
            print("[WARNING] Timeout waiting for position data, using partial data")

        # Store current positions and contract details
        current_positions = app.current_positions.copy()
        current_contract_details = app.contract_details.copy()

        # Cancel subscriptions and disconnect
        app.cancelPositions()
        app.reqAccountUpdates(False, app.account_id)
        app.disconnect()

        print(f"[OK] Current portfolio has {len(current_positions)} positions")
        if current_positions:
            print("  Current positions:")
            for symbol, qty in sorted(current_positions.items()):
                print(f"    {symbol}: {qty:,} shares")

        return current_positions, current_contract_details

    def generate_orders(
        self,
        target_quantities: Dict[str, int],
        current_positions: Dict[str, int],
        symbol_details: Dict[str, Dict[str, Any]],
        current_contract_details: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate buy/sell orders to reach target quantities

        Args:
            target_quantities: Dict mapping symbol to target quantity
            current_positions: Dict mapping symbol to current quantity
            symbol_details: Symbol information from universe data
            current_contract_details: IBKR contract details from fetch_current_positions()

        Returns:
            List of order dictionaries with complete IBKR details structure

        Side Effects:
            Prints order generation progress and summary to console
        """
        print("\n[ORDERS] Generating orders...")

        orders = []
        buy_orders = []
        sell_orders = []

        # Get all symbols that need action (target > 0 or current > 0)
        all_symbols = set(list(target_quantities.keys()) + list(current_positions.keys()))

        for symbol in sorted(all_symbols):
            target_qty = target_quantities.get(symbol, 0)
            current_qty = current_positions.get(symbol, 0)

            diff = target_qty - current_qty

            if diff == 0:
                continue  # No action needed

            # Get IBKR details
            if symbol in symbol_details:
                ibkr_details = symbol_details[symbol]['ibkr_details']
                stock_info = symbol_details[symbol]
            else:
                # For stocks we need to sell but aren't in targets - use real IBKR data
                if symbol in current_contract_details:
                    contract_data = current_contract_details[symbol]
                    ibkr_details = {
                        'symbol': contract_data['symbol'],
                        'exchange': contract_data['exchange'],
                        'primaryExchange': contract_data['primaryExchange'],
                        'conId': contract_data['conId']
                    }
                    stock_info = {
                        'ticker': symbol,
                        'name': f'{symbol} (Current Holding)',
                        'currency': contract_data['currency'],
                        'screens': []
                    }
                else:
                    # Ultimate fallback if somehow we don't have contract data
                    ibkr_details = {
                        'symbol': symbol,
                        'exchange': 'SMART',
                        'primaryExchange': 'NASDAQ',  # Default fallback
                        'conId': None
                    }
                    stock_info = {
                        'ticker': symbol,
                        'name': f'Unknown ({symbol})',
                        'currency': 'USD',  # Default fallback
                        'screens': []
                    }

            order = {
                'symbol': symbol,
                'action': 'BUY' if diff > 0 else 'SELL',
                'quantity': abs(diff),
                'current_quantity': current_qty,
                'target_quantity': target_qty,
                'stock_info': {
                    'ticker': stock_info['ticker'],
                    'name': stock_info['name'],
                    'currency': stock_info['currency'],
                    'screens': stock_info['screens']
                },
                'ibkr_details': ibkr_details
            }

            if diff > 0:
                buy_orders.append(order)
            else:
                sell_orders.append(order)

        # Sort orders by quantity (largest first)
        buy_orders.sort(key=lambda x: x['quantity'], reverse=True)
        sell_orders.sort(key=lambda x: x['quantity'], reverse=True)

        orders = sell_orders + buy_orders  # Sells first, then buys

        # Print summary
        total_buy_qty = sum(o['quantity'] for o in buy_orders)
        total_sell_qty = sum(o['quantity'] for o in sell_orders)
        total_buy_value = len(buy_orders)
        total_sell_value = len(sell_orders)

        print(f"[OK] Generated {len(orders)} orders:")
        print(f"  [BUY] {total_buy_value} BUY orders for {total_buy_qty:,} total shares")
        print(f"  [SELL] {total_sell_value} SELL orders for {total_sell_qty:,} total shares")

        if len(orders) <= 20:  # Show details if not too many
            print("\n  Order details:")
            for i, order in enumerate(orders, 1):
                action_emoji = "[BUY]" if order['action'] == 'BUY' else "[SELL]"
                screens = ", ".join(order['stock_info']['screens']) if order['stock_info']['screens'] else "None"
                print(f"    {i:2d}. {action_emoji} {order['action']} {order['quantity']:,} {order['symbol']} "
                      f"(current: {order['current_quantity']:,}, target: {order['target_quantity']:,}) - {screens}")

        return orders

    def save_orders_json(
        self,
        orders: List[Dict[str, Any]],
        output_file: str = "orders.json"
    ) -> None:
        """
        Save orders to JSON file with metadata

        Args:
            orders: List of order dictionaries from generate_orders()
            output_file: Output file path (defaults to "orders.json" in data directory)

        Side Effects:
            Creates data/orders.json with complete metadata structure
        """
        # Save to data directory
        if not os.path.isabs(output_file):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            output_file = os.path.join(project_root, "data", output_file)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        print(f"\n[SAVE] Saving orders to {output_file}...")

        orders_data = {
            'metadata': {
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_orders': len(orders),
                'buy_orders': len([o for o in orders if o['action'] == 'BUY']),
                'sell_orders': len([o for o in orders if o['action'] == 'SELL']),
                'total_buy_quantity': sum(o['quantity'] for o in orders if o['action'] == 'BUY'),
                'total_sell_quantity': sum(o['quantity'] for o in orders if o['action'] == 'SELL')
            },
            'orders': orders
        }

        with open(output_file, 'w') as f:
            json.dump(orders_data, f, indent=2)

        print(f"[OK] Saved {len(orders)} orders to {output_file}")

    def run_rebalancing(self, universe_file: str) -> Dict[str, Any]:
        """
        Execute complete rebalancing process orchestration

        Args:
            universe_file: Path to universe_with_ibkr.json file

        Returns:
            Dict containing:
            - orders: List of generated orders
            - metadata: Summary statistics
            - target_quantities: Dict of calculated targets
            - current_positions: Dict of current positions

        Side Effects:
            - Loads universe data
            - Calculates target quantities
            - Fetches current positions from IBKR
            - Generates orders
            - Saves orders to data/orders.json
            - Prints complete rebalancing summary to console
        """
        print("[REBALANCE] Starting Portfolio Rebalancing")
        print("=" * 50)

        # Print current working directory for debugging
        print(f"[DEBUG] Working directory: {os.getcwd()}")
        print(f"[DEBUG] Universe file path: {universe_file}")

        try:
            # Step 1: Load universe data
            universe_data = self.load_universe_data(universe_file)

            # Step 2: Calculate target quantities
            target_quantities = self.calculate_target_quantities(universe_data)

            # Step 3: Fetch current positions
            current_positions, current_contract_details = self.fetch_current_positions()

            # Step 4: Generate orders
            orders = self.generate_orders(
                target_quantities,
                current_positions,
                self.symbol_details,
                current_contract_details
            )

            # Step 5: Save orders to JSON
            self.save_orders_json(orders)

            print("\n" + "=" * 50)
            print("[SUCCESS] Rebalancing analysis complete!")
            print(f"   Orders saved to 'data/orders.json'")
            print("   Review the orders before executing them.")

            # Prepare return data
            return {
                'orders': orders,
                'metadata': {
                    'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'total_orders': len(orders),
                    'buy_orders': len([o for o in orders if o['action'] == 'BUY']),
                    'sell_orders': len([o for o in orders if o['action'] == 'SELL']),
                    'total_buy_quantity': sum(o['quantity'] for o in orders if o['action'] == 'BUY'),
                    'total_sell_quantity': sum(o['quantity'] for o in orders if o['action'] == 'SELL')
                },
                'target_quantities': target_quantities,
                'current_positions': current_positions
            }

        except Exception as e:
            print(f"\n[ERROR] Error during rebalancing: {str(e)}")
            raise

    def run_legacy_rebalancer(self, universe_file: str = None) -> bool:
        """
        Run the legacy rebalancer for 100% CLI compatibility

        Args:
            universe_file: Optional universe file path, defaults to data/universe_with_ibkr.json

        Returns:
            bool: True if successful
        """
        if universe_file is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            universe_file = os.path.join(project_root, "data", "universe_with_ibkr.json")

        rebalancer = PortfolioRebalancer(universe_file)
        rebalancer.run_rebalancing()
        return True