"""
QuantityService implementation wrapping legacy qty.py calculation functionality
Maintains 100% behavioral compatibility with CLI step7_calculate_quantities()
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

from ..interfaces import IQuantityCalculator


class QuantityService(IQuantityCalculator):
    """
    Portfolio quantity calculation service
    Wraps legacy qty.py calculation functions with interface compliance
    """

    def __init__(self):
        """Initialize QuantityService with path configuration"""
        self.universe_path = Path(__file__).parent.parent.parent.parent.parent / "data" / "universe.json"

    def calculate_stock_quantities(
        self,
        universe_data: Dict[str, Any],
        account_value: float
    ) -> int:
        """
        Calculate EUR prices and quantities for all stocks based on account value and target allocations
        Exact copy of legacy calculate_stock_quantities function
        """
        print("Calculating stock quantities...")

        total_stocks_processed = 0
        minimal_allocation_count = 0
        meaningful_allocation_count = 0

        # Get screen allocations from portfolio optimization
        screen_allocations = {}
        if ("metadata" in universe_data and
            "portfolio_optimization" in universe_data["metadata"] and
            "optimal_allocations" in universe_data["metadata"]["portfolio_optimization"]):
            screen_allocations = universe_data["metadata"]["portfolio_optimization"]["optimal_allocations"]

        # Process all stock categories
        stock_categories = ["screens", "all_stocks"] if "all_stocks" in universe_data else ["screens"]

        for category in stock_categories:
            if category == "screens":
                # Process each screen
                for screen_name, screen_data in universe_data["screens"].items():
                    print(f"Processing screen: {screen_name}")
                    if isinstance(screen_data, dict) and "stocks" in screen_data:
                        # Get the correct screen allocation for this screen
                        screen_allocation = screen_allocations.get(screen_name, 0)

                        for stock in screen_data["stocks"]:
                            if isinstance(stock, dict):  # Make sure it's a stock dictionary
                                self.calculate_stock_fields(stock, account_value, screen_allocation)
                                total_stocks_processed += 1

                                # Count allocation types
                                final_target = float(stock.get("final_target", 0))
                                if final_target < 1e-10 and final_target > 0:
                                    minimal_allocation_count += 1
                                elif final_target > 0:
                                    meaningful_allocation_count += 1
                            else:
                                print(f"Warning: Non-dict stock found in {screen_name}: {stock}")
                    else:
                        print(f"Warning: Screen {screen_name} has no stocks or is not a dict: {type(screen_data)}")

            elif category == "all_stocks":
                # Process all_stocks category - it's a dict with ticker keys
                print(f"Processing all_stocks category")
                for ticker, stock in universe_data["all_stocks"].items():
                    if isinstance(stock, dict):  # Make sure it's a stock dictionary
                        # For all_stocks, use the stored final_target
                        self.calculate_stock_fields(stock, account_value, None)
                        total_stocks_processed += 1
                    else:
                        print(f"Warning: Non-dict stock found in all_stocks: {ticker}: {stock}")

        print(f"Processed {total_stocks_processed} stocks with quantity calculations")
        print(f"  - {meaningful_allocation_count} stocks with meaningful allocations (>1e-10)")
        print(f"  - {minimal_allocation_count} stocks with minimal allocations (<1e-10)")
        return total_stocks_processed

    def calculate_stock_fields(
        self,
        stock: Dict[str, Any],
        account_value: float,
        screen_allocation: Optional[float] = None
    ) -> None:
        """
        Calculate EUR price, target value, and quantity for a single stock
        Exact copy of legacy calculate_stock_fields function
        """
        try:
            # Get stock price and exchange rate
            price = float(stock.get("price", 0))
            eur_exchange_rate = float(stock.get("eur_exchange_rate", 1))

            # Calculate final_target based on context
            if screen_allocation is not None:
                # We're in a screen context - calculate final_target using this screen's allocation
                allocation_target = float(stock.get("allocation_target", 0))
                final_target = allocation_target * screen_allocation
                # Update the screen_target field to reflect the current screen
                stock["screen_target"] = screen_allocation
            else:
                # We're in all_stocks context - use the stored final_target
                final_target = float(stock.get("final_target", 0))

            # Update the final_target in the stock
            stock["final_target"] = final_target

            # Calculate EUR equivalent price
            eur_price = price / eur_exchange_rate

            # Calculate target value in EUR
            target_value_eur = account_value * final_target

            # Calculate quantity (shares to buy)
            quantity = target_value_eur / eur_price if eur_price > 0 else 0

            # Apply Japanese stock lot size rounding (100 shares minimum)
            currency = stock.get("currency", "").upper()
            if currency == "JPY" and quantity > 0:
                original_quantity = quantity
                # For Japanese stocks: always round to nearest 100 shares
                # For buying: round DOWN to nearest 100 (conservative approach)
                # For selling: round UP to nearest 100 (sell enough to meet lot requirements)
                # Since we can't distinguish buy/sell here, we'll round DOWN (conservative for buying)
                quantity = (int(quantity) // 100) * 100

                if original_quantity != quantity:
                    print(f"Japanese stock {stock.get('ticker', 'Unknown')}: adjusted quantity from {original_quantity:.1f} to {quantity} (lot size 100)")

            # Add new fields to the stock
            stock["eur_price"] = round(eur_price, 6)
            stock["target_value_eur"] = round(target_value_eur, 2)
            stock["quantity"] = int(round(quantity))

            # Add a flag for very small allocations for transparency
            if final_target < 1e-10 and final_target > 0:
                stock["allocation_note"] = "minimal_allocation"
            elif "allocation_note" in stock:
                # Remove the note if allocation is no longer minimal
                del stock["allocation_note"]

        except (ValueError, TypeError, ZeroDivisionError) as e:
            # Handle missing or invalid data
            stock["eur_price"] = 0
            stock["target_value_eur"] = 0
            stock["quantity"] = 0
            print(f"Warning: Error calculating for {stock.get('ticker', 'Unknown')}: {e}")

    def update_universe_json(
        self,
        account_value: float,
        currency: str
    ) -> bool:
        """
        Update universe.json with account value and calculate all stock quantities
        Exact copy of legacy update_universe_json function
        """
        if not self.universe_path.exists():
            print(f"Universe file not found at: {self.universe_path}")
            return False

        try:
            # Read current universe.json
            with open(self.universe_path, 'r', encoding='utf-8') as f:
                universe_data = json.load(f)

            # Add account value at the top level
            universe_data["account_total_value"] = {
                "value": account_value,
                "currency": currency,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            # Calculate stock quantities for all stocks
            stocks_processed = self.calculate_stock_quantities(universe_data, account_value)

            # Write back to file
            with open(self.universe_path, 'w', encoding='utf-8') as f:
                json.dump(universe_data, f, indent=2, ensure_ascii=False)

            print(f"Updated universe.json with account value: ${account_value:,.2f}")
            print(f"Added quantity calculations for {stocks_processed} stocks")
            return True

        except Exception as e:
            print(f"Error updating universe.json: {e}")
            return False

    def round_account_value_conservatively(self, account_value: float) -> float:
        """
        Round account value DOWN to nearest 100€ for conservative allocation calculations
        Exact copy of legacy main() function rounding logic
        """
        return (account_value // 100) * 100