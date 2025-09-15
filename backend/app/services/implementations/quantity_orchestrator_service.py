"""
QuantityOrchestratorService that combines account and quantity services
Provides main() function with exact behavioral compatibility to legacy qty.py main()
"""

from typing import Dict, Any, Tuple, Optional

from .account_service import AccountService
from .quantity_service import QuantityService
from ..interfaces import IAccountService, IQuantityCalculator


class QuantityOrchestratorService:
    """
    Orchestrates account value fetching and quantity calculations
    Maintains exact behavioral compatibility with legacy qty.py main() function
    """

    def __init__(
        self,
        account_service: IAccountService = None,
        quantity_service: IQuantityCalculator = None
    ):
        """Initialize with service dependencies"""
        self.account_service = account_service or AccountService()
        self.quantity_service = quantity_service or QuantityService()

    async def main(self) -> bool:
        """
        Main function to get account value and update universe.json
        Exact behavioral compatibility with legacy qty.py main() function
        """
        print("Starting quantity calculator...")

        # Get account total value from IBKR
        account_value, currency = await self.account_service.get_account_total_value()

        if account_value is None or currency is None:
            print("Failed to get account value from IBKR")
            return False

        # Round down to nearest 100€ for calculations
        rounded_account_value = self.quantity_service.round_account_value_conservatively(account_value)
        print(f"Original account value: €{account_value:,.2f}")
        print(f"Rounded account value for calculations: €{rounded_account_value:,.2f}")

        # Update universe.json with the rounded account value
        success = self.quantity_service.update_universe_json(rounded_account_value, currency)

        if success:
            print("Successfully updated universe.json with account total value")
            return True
        else:
            print("Failed to update universe.json")
            return False

    async def calculate_quantities_only(
        self,
        account_value: float,
        currency: str = "EUR"
    ) -> Tuple[bool, int]:
        """
        Calculate quantities without fetching account value from IBKR
        Useful for API endpoints that want to provide custom account values

        Args:
            account_value: Account value to use for calculations
            currency: Account currency

        Returns:
            Tuple of (success: bool, stocks_processed: int)
        """
        rounded_account_value = self.quantity_service.round_account_value_conservatively(account_value)
        print(f"Using provided account value: €{account_value:,.2f}")
        print(f"Rounded account value for calculations: €{rounded_account_value:,.2f}")

        success = self.quantity_service.update_universe_json(rounded_account_value, currency)

        if success:
            print(f"Successfully calculated quantities with account value: €{rounded_account_value:,.2f}")
            # Return success and estimated stocks processed (we could enhance this to return actual count)
            return True, 0
        else:
            print("Failed to calculate quantities")
            return False, 0

    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information without updating universe.json
        Useful for API endpoints that just want account data
        """
        account_value, currency = await self.account_service.get_account_total_value()

        if account_value is None:
            return {
                "success": False,
                "error": "Failed to fetch account value from IBKR"
            }

        rounded_value = self.quantity_service.round_account_value_conservatively(account_value)

        return {
            "success": True,
            "account_value": account_value,
            "currency": currency,
            "rounded_account_value": rounded_value,
            "rounding_note": f"Rounded DOWN from €{account_value:,.2f} to €{rounded_value:,.2f} for conservative calculations"
        }