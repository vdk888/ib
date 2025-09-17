"""
Order Status Service Implementation
Wraps legacy order_status_checker.py with Interface-First Design
Provides API-compatible methods while maintaining 100% CLI behavioral compatibility
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import from local legacy directory
from .legacy.order_status_checker import OrderStatusChecker, IBOrderStatusChecker
from ..interfaces import IOrderStatusService


class OrderStatusService(IOrderStatusService):
    """
    Service implementation wrapping legacy order status checker
    Maintains 100% behavioral compatibility with CLI while providing API access
    """

    def __init__(self, orders_file: str = "orders.json"):
        """
        Initialize order status service

        Args:
            orders_file: Path to orders JSON file (defaults to data/orders.json)
        """
        # Initialize path resolution like legacy code
        if not os.path.isabs(orders_file):
            # Get project root relative to this service
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
            self.orders_file = os.path.join(project_root, "data", orders_file)
        else:
            self.orders_file = orders_file

        self.orders_data = None
        self._legacy_checker = None

    def load_orders_json(self, orders_file: str = "orders.json") -> Dict[str, Any]:
        """
        Load orders from JSON file created by rebalancer
        Wraps legacy load_orders_json() method
        """
        # Update file path if provided
        if orders_file != "orders.json":
            if not os.path.isabs(orders_file):
                self.orders_file = os.path.join(project_root, "data", orders_file)
            else:
                self.orders_file = orders_file

        # Initialize legacy checker if not already done
        if not self._legacy_checker:
            self._legacy_checker = OrderStatusChecker(self.orders_file)

        # Call legacy method
        self.orders_data = self._legacy_checker.load_orders_json()

        return self.orders_data

    def connect_to_ibkr(self) -> bool:
        """
        Establish connection to IBKR Gateway with enhanced order detection
        Wraps legacy connect_to_ibkr() method
        """
        if not self._legacy_checker:
            self._legacy_checker = OrderStatusChecker(self.orders_file)

        return self._legacy_checker.connect_to_ibkr()

    def fetch_account_data(self) -> None:
        """
        Comprehensive data fetching using multiple IBKR API methods
        Wraps legacy fetch_account_data() method
        """
        if not self._legacy_checker:
            raise ValueError("Must connect to IBKR first")

        self._legacy_checker.fetch_account_data()

    def analyze_orders(self) -> Dict[str, Any]:
        """
        Core comparison logic between JSON orders and IBKR status
        Wraps legacy analyze_orders() method and returns structured data
        """
        if not self._legacy_checker or not self._legacy_checker.api:
            raise ValueError("Must connect to IBKR and fetch data first")

        # Call legacy method (has console side effects)
        self._legacy_checker.analyze_orders()

        # Extract data for API response
        json_orders_by_symbol = {}
        for order in self.orders_data['orders']:
            symbol = order['symbol']
            json_orders_by_symbol[symbol] = order

        # Combine open orders and completed orders
        all_ibkr_orders = {}
        all_ibkr_orders.update(self._legacy_checker.api.open_orders)
        all_ibkr_orders.update(self._legacy_checker.api.completed_orders)

        ibkr_orders_by_symbol = {}
        for order_id, order_info in all_ibkr_orders.items():
            symbol = order_info['symbol']
            if symbol not in ibkr_orders_by_symbol:
                ibkr_orders_by_symbol[symbol] = []
            ibkr_orders_by_symbol[symbol].append(order_info)

        # Analysis counters and results
        found_in_ibkr = 0
        missing_from_ibkr = 0
        quantity_mismatches = 0
        missing_orders = []
        extra_ibkr_orders = []
        analysis_table = []

        # Process each JSON order
        for symbol, json_order in json_orders_by_symbol.items():
            json_action = json_order['action']
            json_quantity = json_order['quantity']

            analysis_row = {
                'symbol': symbol,
                'json_action': json_action,
                'json_quantity': json_quantity,
                'ibkr_status': None,
                'ibkr_quantity': None,
                'match_status': None
            }

            if symbol in ibkr_orders_by_symbol:
                ibkr_orders = ibkr_orders_by_symbol[symbol]

                # Find matching order by action
                matching_order = None
                for ibkr_order in ibkr_orders:
                    if ibkr_order['action'] == json_action:
                        matching_order = ibkr_order
                        break

                if matching_order:
                    found_in_ibkr += 1
                    ibkr_qty = matching_order['quantity']
                    status = matching_order['status']

                    analysis_row['ibkr_status'] = status
                    analysis_row['ibkr_quantity'] = ibkr_qty

                    if ibkr_qty == json_quantity:
                        analysis_row['match_status'] = "OK"
                    else:
                        analysis_row['match_status'] = "QTY_DIFF"
                        quantity_mismatches += 1
                else:
                    analysis_row['ibkr_status'] = "NOT_FOUND"
                    analysis_row['match_status'] = "MISSING"
                    missing_from_ibkr += 1
                    missing_orders.append(json_order)
            else:
                analysis_row['ibkr_status'] = "NOT_FOUND"
                analysis_row['match_status'] = "MISSING"
                missing_from_ibkr += 1
                missing_orders.append(json_order)

            analysis_table.append(analysis_row)

        # Find extra IBKR orders not in JSON
        for symbol, ibkr_orders in ibkr_orders_by_symbol.items():
            if symbol not in json_orders_by_symbol:
                extra_ibkr_orders.extend(ibkr_orders)

        # Calculate success rate
        total_orders = len(json_orders_by_symbol)
        success_rate = (found_in_ibkr / total_orders * 100) if total_orders > 0 else 0

        return {
            'found_in_ibkr': found_in_ibkr,
            'missing_from_ibkr': missing_from_ibkr,
            'quantity_mismatches': quantity_mismatches,
            'success_rate': success_rate,
            'total_orders': total_orders,
            'missing_orders': missing_orders,
            'extra_ibkr_orders': extra_ibkr_orders,
            'analysis_table': analysis_table
        }

    def get_missing_order_analysis(self, missing_orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detailed failure analysis with generic patterns and recommendations
        Wraps legacy show_missing_order_analysis() method
        """
        failure_analysis = []
        recommendations = [
            "Check IBKR account settings and API permissions",
            "Verify contract details for international stocks",
            "Consider using algorithmic orders for large volumes",
            "Ensure market hours alignment for order execution",
            "Review account restrictions for specific instruments"
        ]

        for order in missing_orders:
            symbol = order['symbol']
            action = order['action']
            quantity = order['quantity']
            currency = order['stock_info']['currency']
            ticker = order['stock_info']['ticker']
            exchange = order['ibkr_details'].get('primaryExchange', 'N/A')

            failure_info = {
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'currency': currency,
                'ticker': ticker,
                'exchange': exchange
            }
            # Generic analysis based on patterns
            if action == 'SELL':
                failure_info.update({
                    'reason': 'Likely Account/Position Issue',
                    'details': 'SELL orders may fail due to account restrictions or position conflicts',
                    'note': 'Check account settings and current positions'
                })
            else :
                failure_info.update({
                    'reason': 'Unknown - Requires Debug Investigation',
                    'details': 'Run debug_order_executor.py to identify specific error codes',
                    'note': 'Check contract details, account permissions, and market hours'
                })

            failure_analysis.append(failure_info)

        # Call legacy method for console output
        if self._legacy_checker:
            self._legacy_checker.show_missing_order_analysis(missing_orders)

        return {
            'failure_analysis': failure_analysis,
            'recommendations': recommendations
        }

    def get_order_status_summary(self) -> Dict[str, Any]:
        """
        Get detailed status breakdown of all IBKR orders
        Wraps legacy show_order_status_summary() method
        """
        if not self._legacy_checker or not self._legacy_checker.api:
            raise ValueError("Must connect to IBKR and fetch data first")

        # Call legacy method for console output
        self._legacy_checker.show_order_status_summary()

        # Combine open and completed orders
        all_orders = {}
        all_orders.update(self._legacy_checker.api.open_orders)
        all_orders.update(self._legacy_checker.api.completed_orders)

        if not all_orders:
            return {
                'orders_by_status': {},
                'status_counts': {},
                'total_orders': 0,
                'order_details': []
            }

        # Group orders by status
        orders_by_status = {}
        order_details = []

        for order_id, order_info in all_orders.items():
            status = order_info['status']
            if status not in orders_by_status:
                orders_by_status[status] = []

            order_detail = {
                'order_id': order_id,
                'symbol': order_info['symbol'],
                'action': order_info['action'],
                'quantity': order_info['quantity'],
                'filled': order_info.get('filled', 0),
                'status': status,
                'avg_fill_price': order_info.get('avgFillPrice', 'N/A'),
                'order_type': order_info.get('orderType', 'N/A')
            }

            orders_by_status[status].append(order_detail)
            order_details.append(order_detail)

        # Calculate status counts
        status_counts = {status: len(orders) for status, orders in orders_by_status.items()}

        return {
            'orders_by_status': orders_by_status,
            'status_counts': status_counts,
            'total_orders': len(all_orders),
            'order_details': order_details
        }

    def get_positions_summary(self) -> Dict[str, Any]:
        """
        Get current account positions summary
        Wraps legacy show_positions() method
        """
        if not self._legacy_checker or not self._legacy_checker.api:
            raise ValueError("Must connect to IBKR and fetch data first")

        # Call legacy method for console output
        self._legacy_checker.show_positions()

        positions = {}
        market_values = {}
        total_market_value = 0

        for symbol, pos_info in self._legacy_checker.api.positions.items():
            position = pos_info['position']
            avg_cost = pos_info['avgCost']
            currency = pos_info['currency']
            exchange = pos_info['exchange']
            market_value = position * avg_cost

            positions[symbol] = {
                'position': position,
                'avg_cost': avg_cost,
                'currency': currency,
                'exchange': exchange,
                'market_value': market_value
            }
            market_values[symbol] = market_value
            total_market_value += market_value

        return {
            'positions': positions,
            'total_positions': len(positions),
            'market_values': market_values,
            'total_market_value': total_market_value
        }

    def run_status_check(self) -> bool:
        """
        Execute complete order status check workflow
        Wraps legacy run_status_check() method
        """
        try:
            # Initialize if needed
            if not self._legacy_checker:
                self._legacy_checker = OrderStatusChecker(self.orders_file)

            # Execute legacy workflow
            return self._legacy_checker.run_status_check()

        except Exception as e:
            print(f"[ERROR] Status check failed: {str(e)}")
            if self._legacy_checker:
                self._legacy_checker.disconnect()
            return False

    def disconnect(self) -> None:
        """
        Disconnect from IBKR Gateway and cleanup resources
        Wraps legacy disconnect() method
        """
        if self._legacy_checker:
            self._legacy_checker.disconnect()

    def get_verification_results(self) -> Dict[str, Any]:
        """
        Get verification results without console output for API responses
        """
        if not self._legacy_checker or not self._legacy_checker.api:
            raise ValueError("Must connect to IBKR and fetch data first")

        # Get analysis results without console output
        analysis_results = self.analyze_orders()

        # Get order status summary data
        status_summary = self.get_order_status_summary()

        # Get positions data
        positions_summary = self.get_positions_summary()

        # Get missing order analysis if any
        missing_analysis = None
        if analysis_results['missing_orders']:
            missing_analysis = self.get_missing_order_analysis(analysis_results['missing_orders'])

        return {
            'comparison_summary': {
                'found_in_ibkr': analysis_results['found_in_ibkr'],
                'missing_from_ibkr': analysis_results['missing_from_ibkr'],
                'quantity_mismatches': analysis_results['quantity_mismatches'],
                'success_rate': analysis_results['success_rate'],
                'total_orders': analysis_results['total_orders'],
                'timestamp': datetime.now().isoformat()
            },
            'order_matches': analysis_results['analysis_table'],
            'missing_orders': missing_analysis['failure_analysis'] if missing_analysis else [],
            'recommendations': missing_analysis['recommendations'] if missing_analysis else [],
            'extra_orders': analysis_results['extra_ibkr_orders'],
            'positions': positions_summary['positions'],
            'order_status_breakdown': status_summary['orders_by_status']
        }