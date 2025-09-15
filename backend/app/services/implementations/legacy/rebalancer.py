#!/usr/bin/env python3
"""
Portfolio Rebalancer for Interactive Brokers
Fetches target quantities from universe data, gets current holdings from IBKR,
and generates orders to rebalance the portfolio to target allocations.
"""

import json
import time
import threading
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract


class IBRebalancerApi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connected = False
        self.account_id = None
        self.current_positions = {}  # symbol -> quantity
        self.portfolio_items = []
        self.contract_details = {}  # symbol -> contract details
        self.data_ready = False
        
    def connectAck(self):
        super().connectAck()
        print("[OK] Connected to IB Gateway")
        self.connected = True
        
    def connectionClosed(self):
        super().connectionClosed()
        print("[CLOSED] Connection closed")
        self.connected = False
        
    def managedAccounts(self, accountsList: str):
        super().managedAccounts(accountsList)
        accounts = accountsList.split(",")
        self.account_id = accounts[0]
        print(f"[OK] Account ID: {self.account_id}")
        
    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        super().position(account, contract, position, avgCost)
        if position != 0:
            # Use the symbol from IBKR
            symbol = contract.symbol
            self.current_positions[symbol] = int(position)
            
            # Store contract details for later use
            self.contract_details[symbol] = {
                'symbol': contract.symbol,
                'conId': contract.conId,
                'exchange': contract.exchange,
                'primaryExchange': contract.primaryExchange,
                'currency': contract.currency,
                'secType': contract.secType
            }
            
            print(f"  Position: {symbol} = {int(position)} shares (conId: {contract.conId})")
            
    def positionEnd(self):
        super().positionEnd()
        print(f"[OK] Fetched {len(self.current_positions)} positions")
        self.data_ready = True
        
    def updatePortfolio(self, contract: Contract, position: float, marketPrice: float, 
                       marketValue: float, averageCost: float, unrealizedPNL: float, 
                       realizedPNL: float, accountName: str):
        super().updatePortfolio(contract, position, marketPrice, marketValue, 
                               averageCost, unrealizedPNL, realizedPNL, accountName)
        if position != 0:
            portfolio_item = {
                "symbol": contract.symbol,
                "position": int(position),
                "marketPrice": marketPrice,
                "marketValue": marketValue,
                "averageCost": averageCost,
                "unrealizedPNL": unrealizedPNL
            }
            self.portfolio_items.append(portfolio_item)
            
    def accountDownloadEnd(self, accountName: str):
        super().accountDownloadEnd(accountName)
        print("[OK] Account data download complete")
        
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158, 2107]:  # Ignore common info messages
            print(f"Error {errorCode}: {errorString}")


class PortfolioRebalancer:
    def __init__(self, universe_file: str):
        self.universe_file = universe_file
        self.universe_data = None
        self.target_quantities = {}  # symbol -> total_quantity
        self.current_positions = {}  # symbol -> current_quantity
        self.current_contract_details = {}  # symbol -> contract details from IBKR
        self.orders = []
        
    def load_universe_data(self):
        """Load the universe data with IBKR details and target quantities"""
        print("[DATA] Loading universe data...")
        with open(self.universe_file, 'r') as f:
            self.universe_data = json.load(f)
            
        print(f"[OK] Loaded universe with {self.universe_data['metadata']['total_stocks']} stocks")
        print(f"[OK] Screens: {', '.join(self.universe_data['metadata']['screens'])}")
        
    def calculate_target_quantities(self):
        """Calculate target quantities by summing across all screens where stock appears"""
        print("\n[TARGET] Calculating target quantities...")
        
        # Dictionary to accumulate quantities by IBKR symbol
        symbol_quantities = defaultdict(int)
        symbol_details = {}  # Store IBKR details for each symbol
        
        # Process each screen
        for screen_name, screen_data in self.universe_data['screens'].items():
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
        
        self.target_quantities = dict(symbol_quantities)
        self.symbol_details = symbol_details
        
        print(f"[OK] Calculated targets for {len(self.target_quantities)} unique symbols")
        
        # Show top 10 targets
        sorted_targets = sorted(self.target_quantities.items(), 
                               key=lambda x: x[1], reverse=True)
        print("  Top 10 targets:")
        for symbol, qty in sorted_targets[:10]:
            screens = ", ".join(self.symbol_details[symbol]['screens'])
            print(f"    {symbol}: {qty:,} shares ({screens})")
            
    def fetch_current_positions(self):
        """Fetch current positions from IBKR account"""
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
        self.current_positions = app.current_positions.copy()
        self.current_contract_details = app.contract_details.copy()
        
        # Cancel subscriptions and disconnect
        app.cancelPositions()
        app.reqAccountUpdates(False, app.account_id)
        app.disconnect()
        
        print(f"[OK] Current portfolio has {len(self.current_positions)} positions")
        if self.current_positions:
            print("  Current positions:")
            for symbol, qty in sorted(self.current_positions.items()):
                print(f"    {symbol}: {qty:,} shares")
                
    def generate_orders(self):
        """Generate buy/sell orders to reach target quantities"""
        print("\n[ORDERS] Generating orders...")
        
        self.orders = []
        buy_orders = []
        sell_orders = []
        
        # Get all symbols that need action (target > 0 or current > 0)
        all_symbols = set(list(self.target_quantities.keys()) + list(self.current_positions.keys()))
        
        for symbol in sorted(all_symbols):
            target_qty = self.target_quantities.get(symbol, 0)
            current_qty = self.current_positions.get(symbol, 0)
            
            diff = target_qty - current_qty
            
            if diff == 0:
                continue  # No action needed
                
            # Get IBKR details
            if symbol in self.symbol_details:
                ibkr_details = self.symbol_details[symbol]['ibkr_details']
                stock_info = self.symbol_details[symbol]
            else:
                # For stocks we need to sell but aren't in targets - use real IBKR data
                if symbol in self.current_contract_details:
                    contract_data = self.current_contract_details[symbol]
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
        
        self.orders = sell_orders + buy_orders  # Sells first, then buys
        
        # Print summary
        total_buy_qty = sum(o['quantity'] for o in buy_orders)
        total_sell_qty = sum(o['quantity'] for o in sell_orders)
        total_buy_value = len(buy_orders)
        total_sell_value = len(sell_orders)
        
        print(f"[OK] Generated {len(self.orders)} orders:")
        print(f"  [BUY] {total_buy_value} BUY orders for {total_buy_qty:,} total shares")
        print(f"  [SELL] {total_sell_value} SELL orders for {total_sell_qty:,} total shares")
        
        if len(self.orders) <= 20:  # Show details if not too many
            print("\n  Order details:")
            for i, order in enumerate(self.orders, 1):
                action_emoji = "[BUY]" if order['action'] == 'BUY' else "[SELL]"
                screens = ", ".join(order['stock_info']['screens']) if order['stock_info']['screens'] else "None"
                print(f"    {i:2d}. {action_emoji} {order['action']} {order['quantity']:,} {order['symbol']} "
                      f"(current: {order['current_quantity']:,}, target: {order['target_quantity']:,}) - {screens}")
        
    def save_orders_json(self, output_file: str = "orders.json"):
        """Save orders to JSON file"""
        import os
        # Save to data directory
        if not os.path.isabs(output_file):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_file = os.path.join(project_root, "data", output_file)
            
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        print(f"\n[SAVE] Saving orders to {output_file}...")
        
        orders_data = {
            'metadata': {
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_orders': len(self.orders),
                'buy_orders': len([o for o in self.orders if o['action'] == 'BUY']),
                'sell_orders': len([o for o in self.orders if o['action'] == 'SELL']),
                'total_buy_quantity': sum(o['quantity'] for o in self.orders if o['action'] == 'BUY'),
                'total_sell_quantity': sum(o['quantity'] for o in self.orders if o['action'] == 'SELL')
            },
            'orders': self.orders
        }
        
        with open(output_file, 'w') as f:
            json.dump(orders_data, f, indent=2)
            
        print(f"[OK] Saved {len(self.orders)} orders to {output_file}")
        
    def run_rebalancing(self):
        """Run the complete rebalancing process"""
        print("[REBALANCE] Starting Portfolio Rebalancing")
        print("=" * 50)
        
        # Print current working directory for debugging
        import os
        print(f"[DEBUG] Working directory: {os.getcwd()}")
        print(f"[DEBUG] Universe file path: {self.universe_file}")
        
        try:
            # Step 1: Load universe data
            self.load_universe_data()
            
            # Step 2: Calculate target quantities
            self.calculate_target_quantities()
            
            # Step 3: Fetch current positions
            self.fetch_current_positions()
            
            # Step 4: Generate orders
            self.generate_orders()
            
            # Step 5: Save orders to JSON
            self.save_orders_json()
            
            print("\n" + "=" * 50)
            print("[SUCCESS] Rebalancing analysis complete!")
            print(f"   Orders saved to 'data/orders.json'")
            print("   Review the orders before executing them.")
            
        except Exception as e:
            print(f"\n[ERROR] Error during rebalancing: {str(e)}")
            raise


def main():
    """Main function to run the rebalancer"""
    import os
    # Get the project root directory (parent of src)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    universe_file = os.path.join(project_root, "data", "universe_with_ibkr.json")
    
    rebalancer = PortfolioRebalancer(universe_file)
    rebalancer.run_rebalancing()


if __name__ == "__main__":
    main()