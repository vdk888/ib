"""
Currency Exchange API Endpoints
Provides REST API for currency exchange rate management
Maintains 100% compatibility with CLI behavior
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict

from ....services.interfaces import ICurrencyService
from ....core.dependencies import get_currency_service
from ....models.schemas import (
    ExchangeRatesResponse,
    UniverseCurrenciesResponse,
    UniverseUpdateResponse,
    CurrencyUpdateWorkflowResponse,
    ExchangeRatesData,
    UniverseUpdateStats
)


router = APIRouter(tags=["currency"])


@router.get("/currency/rates", response_model=ExchangeRatesResponse)
async def fetch_exchange_rates(
    currency_service: ICurrencyService = Depends(get_currency_service)
):
    """
    Fetch current EUR-based exchange rates from external API

    This endpoint wraps the legacy fetch_exchange_rates() function and provides
    identical behavior including:
    - HTTP request to exchangerate-api.com with 10-second timeout
    - EUR as base currency with rate 1.0
    - Console output with + and X prefixes
    - Empty dict return on failures

    Returns:
        ExchangeRatesResponse: Exchange rates data or error information
    """
    try:
        # Call legacy function through service wrapper
        rates = currency_service.fetch_exchange_rates()

        if rates:
            # Success - create structured response
            exchange_rates_data = ExchangeRatesData(
                rates=rates,
                base_currency="EUR"
            )

            return ExchangeRatesResponse(
                success=True,
                exchange_rates=exchange_rates_data
            )
        else:
            # Failure - API call failed (maintains CLI behavior)
            return ExchangeRatesResponse(
                success=False,
                error_message="Failed to fetch exchange rates from external API"
            )

    except Exception as e:
        # Unexpected error - maintain CLI error handling behavior
        return ExchangeRatesResponse(
            success=False,
            error_message=f"Unexpected error fetching exchange rates: {str(e)}"
        )


@router.get("/universe/currencies", response_model=UniverseCurrenciesResponse)
async def get_currencies_from_universe(
    currency_service: ICurrencyService = Depends(get_currency_service)
):
    """
    Extract all unique currency codes from universe.json file

    This endpoint wraps the legacy get_currencies_from_universe() function with
    identical behavior including:
    - Reading from "data/universe.json" with UTF-8 encoding
    - Extracting from both "screens" and "all_stocks" sections
    - Console output with currency count and sorted list
    - Empty set return on file missing or JSON errors

    Returns:
        UniverseCurrenciesResponse: Currencies found in universe or error information
    """
    try:
        # Call legacy function through service wrapper
        currencies_set = currency_service.get_currencies_from_universe()

        # Convert set to sorted list for API response
        currencies_list = sorted(list(currencies_set))

        return UniverseCurrenciesResponse(
            success=len(currencies_list) > 0,
            currencies=currencies_list
        )

    except Exception as e:
        # Unexpected error - maintain CLI error handling behavior
        return UniverseCurrenciesResponse(
            success=False,
            currencies=[],
            currency_count=0
        )


@router.post("/currency/update-universe", response_model=UniverseUpdateResponse)
async def update_universe_with_exchange_rates(
    exchange_rates: Dict[str, float],
    currency_service: ICurrencyService = Depends(get_currency_service)
):
    """
    Update universe.json by adding EUR exchange rates to all stock objects

    This endpoint wraps the legacy update_universe_with_exchange_rates() function
    with identical behavior including:
    - Reading and writing "data/universe.json" with UTF-8 encoding
    - Updating both "screens" and "all_stocks" sections
    - Adding "eur_exchange_rate" field to each stock
    - Console output with progress counts and warnings
    - Pretty JSON formatting

    Args:
        exchange_rates: Dictionary with currency codes and EUR exchange rates

    Returns:
        UniverseUpdateResponse: Update results or error information
    """
    try:
        # Call legacy function through service wrapper
        success = currency_service.update_universe_with_exchange_rates(exchange_rates)

        if success:
            # Success - create structured response (stats would need to be captured from legacy)
            # For now, we indicate success but detailed stats are in console output
            return UniverseUpdateResponse(
                success=True,
                update_stats=UniverseUpdateStats(
                    updated_stocks_screens=0,  # Legacy function doesn't return these values
                    updated_stocks_all=0,      # They're only printed to console
                    missing_rates=[]           # Would need to modify legacy to capture
                )
            )
        else:
            # Failure - file error or JSON issues
            return UniverseUpdateResponse(
                success=False,
                error_message="Failed to update universe.json with exchange rates"
            )

    except Exception as e:
        # Unexpected error - maintain CLI error handling behavior
        return UniverseUpdateResponse(
            success=False,
            error_message=f"Unexpected error updating universe: {str(e)}"
        )


@router.post("/currency/update", response_model=CurrencyUpdateWorkflowResponse)
async def run_currency_update_workflow(
    currency_service: ICurrencyService = Depends(get_currency_service)
):
    """
    Execute complete 3-step currency update workflow

    This endpoint wraps the legacy main() function with identical behavior:
    1. Analyze currencies in universe.json
    2. Fetch current exchange rates from external API
    3. Update universe.json with EUR exchange rates

    Maintains all console output, error handling, and file operations exactly
    as in the original CLI implementation.

    Returns:
        CurrencyUpdateWorkflowResponse: Complete workflow results
    """
    try:
        # Call legacy main function through service wrapper
        success = currency_service.run_currency_update()

        if success:
            return CurrencyUpdateWorkflowResponse(
                success=True,
                workflow_message="Currency exchange rates successfully added to universe.json! Each stock now has an 'eur_exchange_rate' field"
            )
        else:
            return CurrencyUpdateWorkflowResponse(
                success=False,
                workflow_message="Currency update workflow failed",
                error_step="Unknown - check console output for details"
            )

    except Exception as e:
        # Top-level exception handler matching legacy behavior
        return CurrencyUpdateWorkflowResponse(
            success=False,
            workflow_message=f"Error in currency exchange rate updater: {str(e)}",
            error_step="Exception during workflow execution"
        )