"""
Portfolio optimization API endpoints
Implements REST API for portfolio optimization functionality
Following fintech best practices for financial data APIs
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging
from ....core.dependencies import get_portfolio_optimizer_service, get_quantity_orchestrator_service
from ....core.exceptions import ValidationError
from ....models.schemas import (
    PortfolioOptimizationResponse,
    QuarterlyReturnsResponse
)
from ....models.errors import ErrorResponse

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["Portfolio Optimization"])


@router.post(
    "/optimize",
    response_model=PortfolioOptimizationResponse,
    summary="Optimize Portfolio Allocation",
    description="Run full portfolio optimization using Sharpe ratio maximization",
    responses={
        200: {
            "description": "Portfolio optimization successful",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "optimization_results": {
                            "optimal_weights": {
                                "screener_1": 0.35,
                                "screener_2": 0.65
                            },
                            "portfolio_stats": {
                                "expected_annual_return": 0.12,
                                "annual_volatility": 0.15,
                                "sharpe_ratio": 0.8
                            }
                        },
                        "universe_updated": True,
                        "message": "Portfolio optimization complete"
                    }
                }
            }
        },
        404: {
            "description": "Universe data not found",
            "model": ErrorResponse
        },
        422: {
            "description": "Invalid universe data or optimization failed",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error during optimization",
            "model": ErrorResponse
        }
    }
)
async def optimize_portfolio(
    portfolio_service=Depends(get_portfolio_optimizer_service)
):
    """
    Run complete portfolio optimization pipeline

    This endpoint replicates the behavior of `python main.py 4`:
    1. Load universe data from data/universe.json
    2. Extract quarterly returns for all screeners
    3. Run Sharpe ratio optimization using SLSQP
    4. Update universe.json with optimization results
    5. Return optimization results

    **Financial Compliance Notes:**
    - Uses modern portfolio theory with Sharpe ratio maximization
    - Implements long-only constraints (no short selling)
    - All calculations maintain precision for financial accuracy
    - Results include full audit trail in universe.json
    """
    try:
        logger.info("Starting portfolio optimization")

        # Run the full optimization pipeline (equivalent to main())
        success = portfolio_service.main()

        if not success:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Portfolio optimization failed"
            )

        # Load the updated universe data to return optimization results
        universe_data = portfolio_service.load_universe_data()
        optimization_data = universe_data['metadata'].get('portfolio_optimization', {})

        logger.info("Portfolio optimization completed successfully")

        return {
            "success": True,
            "optimization_results": optimization_data,
            "universe_updated": True,
            "message": "Portfolio optimization complete"
        }

    except FileNotFoundError as e:
        logger.error(f"Universe file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Universe data not found - run data fetching and parsing steps first"
        )
    except ValidationError as e:
        logger.error(f"Validation error during optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid data for optimization: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during portfolio optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during portfolio optimization"
        )


@router.get(
    "/optimization",
    response_model=Dict[str, Any],
    summary="Get Portfolio Optimization Results",
    description="Retrieve current portfolio optimization results from universe.json",
    responses={
        200: {
            "description": "Portfolio optimization results retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "optimal_allocations": {
                            "screener_1": 0.35,
                            "screener_2": 0.65
                        },
                        "portfolio_performance": {
                            "expected_annual_return": 0.12,
                            "annual_volatility": 0.15,
                            "sharpe_ratio": 0.8
                        },
                        "individual_screener_stats": {},
                        "correlation_matrix": {},
                        "optimization_details": {}
                    }
                }
            }
        },
        404: {
            "description": "No optimization results found",
            "model": ErrorResponse
        }
    }
)
async def get_optimization_results(
    portfolio_service=Depends(get_portfolio_optimizer_service)
):
    """
    Get current portfolio optimization results

    Returns the portfolio_optimization section from universe.json metadata.
    This includes:
    - Optimal portfolio allocations
    - Portfolio performance metrics
    - Individual screener statistics
    - Correlation matrix
    - Optimization method details
    """
    try:
        logger.info("Retrieving portfolio optimization results")

        universe_data = portfolio_service.load_universe_data()

        if 'portfolio_optimization' not in universe_data['metadata']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No portfolio optimization results found - run optimization first"
            )

        optimization_results = universe_data['metadata']['portfolio_optimization']

        logger.info("Portfolio optimization results retrieved successfully")
        return optimization_results

    except FileNotFoundError as e:
        logger.error(f"Universe file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Universe data not found - run data fetching and parsing steps first"
        )
    except Exception as e:
        logger.error(f"Error retrieving optimization results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving optimization results"
        )


@router.get(
    "/returns",
    response_model=QuarterlyReturnsResponse,
    summary="Get Quarterly Returns Data",
    description="Extract and return quarterly returns data for all screeners",
    responses={
        200: {
            "description": "Quarterly returns data retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "returns_data": {
                            "screener_1": [0.05, 0.03, -0.02, 0.08],
                            "screener_2": [0.04, 0.06, -0.01, 0.07]
                        },
                        "quarters": ["2023Q1", "2023Q2", "2023Q3", "2023Q4"],
                        "metadata": {
                            "num_quarters": 4,
                            "num_screeners": 2,
                            "data_range": "2023Q1 to 2023Q4"
                        }
                    }
                }
            }
        },
        404: {
            "description": "Universe data or historical performance not found",
            "model": ErrorResponse
        },
        422: {
            "description": "Invalid historical data format",
            "model": ErrorResponse
        }
    }
)
async def get_quarterly_returns(
    portfolio_service=Depends(get_portfolio_optimizer_service)
):
    """
    Get quarterly returns data for portfolio optimization

    Extracts quarterly returns from the historical_performance section
    of universe.json metadata. This data is used as input for the
    portfolio optimization algorithm.

    **Data Format:**
    - Returns are in decimal format (0.05 = 5%)
    - Quarters are indexed chronologically
    - Only screeners with valid quarterly data are included
    """
    try:
        logger.info("Extracting quarterly returns data")

        universe_data = portfolio_service.load_universe_data()
        returns_df = portfolio_service.extract_quarterly_returns(universe_data)

        # Convert DataFrame to API-friendly format
        returns_dict = returns_df.to_dict('list')
        quarters_list = returns_df.index.tolist()

        response_data = {
            "returns_data": returns_dict,
            "quarters": quarters_list,
            "metadata": {
                "num_quarters": len(returns_df),
                "num_screeners": len(returns_df.columns),
                "screeners": list(returns_df.columns),
                "data_range": f"{returns_df.index[0]} to {returns_df.index[-1]}" if len(returns_df) > 0 else "No data"
            }
        }

        logger.info(f"Quarterly returns extracted: {len(returns_df)} quarters, {len(returns_df.columns)} screeners")
        return response_data

    except FileNotFoundError as e:
        logger.error(f"Universe file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Universe data not found - run data fetching and parsing steps first"
        )
    except KeyError as e:
        logger.error(f"Historical performance data not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Historical performance data not found - run historical data parsing first"
        )
    except Exception as e:
        logger.error(f"Error extracting quarterly returns: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error processing historical data: {str(e)}"
        )


# Add health check endpoint for portfolio optimization service
@router.get(
    "/health",
    summary="Portfolio Service Health Check",
    description="Check if portfolio optimization service is operational"
)
async def portfolio_health_check(
    portfolio_service=Depends(get_portfolio_optimizer_service)
):
    """
    Health check for portfolio optimization service

    Verifies:
    - Service initialization
    - Universe data accessibility
    - Basic data validation
    """
    try:
        # Test basic service functionality
        universe_data = portfolio_service.load_universe_data()

        # Check for required data structure
        has_historical_data = 'historical_performance' in universe_data.get('metadata', {})
        has_portfolio_data = 'portfolio_optimization' in universe_data.get('metadata', {})

        return {
            "status": "healthy",
            "service": "portfolio_optimizer",
            "universe_data_available": True,
            "historical_data_available": has_historical_data,
            "optimization_results_available": has_portfolio_data,
            "timestamp": "2024-01-01T00:00:00Z"  # Will be replaced with actual timestamp
        }

    except FileNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "portfolio_optimizer",
                "error": "Universe data not available",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "portfolio_optimizer",
                "error": str(e),
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )


# Quantity Calculation Endpoints (Step 7)

@router.get(
    "/account/value",
    summary="Get Account Total Value",
    description="Fetch account total value from IBKR paper trading account",
    responses={
        200: {
            "description": "Account value retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "account_value": 10000.0,
                        "currency": "EUR",
                        "rounded_account_value": 10000.0,
                        "rounding_note": "Rounded DOWN from €10,000.00 to €10,000.00 for conservative calculations"
                    }
                }
            }
        },
        503: {
            "description": "IBKR connection failed or account data unavailable",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error during account value fetch",
            "model": ErrorResponse
        }
    }
)
async def get_account_value(
    orchestrator_service=Depends(get_quantity_orchestrator_service)
):
    """
    Get account total value from IBKR

    This endpoint replicates the behavior of get_account_total_value() from qty.py:
    1. Connect to IBKR paper trading gateway (127.0.0.1:4002)
    2. Fetch NetLiquidation value from account summary
    3. Return account value with conservative rounding information

    **IBKR Integration Details:**
    - Uses paper trading port 4002
    - 10-second connection timeout
    - Threading-based message processing
    - Graceful handling of connection failures

    **Risk Management:**
    - Rounds DOWN to nearest 100€ for conservative allocation calculations
    - Prevents over-allocation beyond account capacity
    """
    try:
        logger.info("Fetching account value from IBKR")

        account_info = await orchestrator_service.get_account_info()

        if not account_info["success"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=account_info["error"]
            )

        logger.info(f"Account value retrieved: €{account_info['account_value']:,.2f}")
        return account_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching account value: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error fetching account value"
        )


@router.post(
    "/quantities/calculate",
    summary="Calculate Stock Quantities",
    description="Calculate stock quantities based on account value and target allocations",
    responses={
        200: {
            "description": "Quantity calculation completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "account_value_used": 9800.0,
                        "original_account_value": 9847.32,
                        "currency": "EUR",
                        "stocks_processed": 0,
                        "universe_updated": True,
                        "message": "Stock quantities calculated and universe.json updated"
                    }
                }
            }
        },
        404: {
            "description": "Universe data not found",
            "model": ErrorResponse
        },
        503: {
            "description": "IBKR connection failed",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error during quantity calculation",
            "model": ErrorResponse
        }
    }
)
async def calculate_quantities(
    orchestrator_service=Depends(get_quantity_orchestrator_service)
):
    """
    Calculate stock quantities based on IBKR account value

    This endpoint replicates the behavior of `python main.py 7`:
    1. Fetch account total value from IBKR
    2. Round DOWN to nearest 100€ for conservative calculations
    3. Calculate EUR prices and quantities for all stocks
    4. Update universe.json with account_total_value section and calculated quantities

    **Processing Logic:**
    - Integrates with portfolio optimization results (optimal_allocations)
    - Handles both "screens" and "all_stocks" categories
    - Applies Japanese stock lot size rounding (100 shares) for JPY stocks
    - Adds calculated fields: eur_price, target_value_eur, quantity

    **Financial Precision:**
    - EUR price precision: 6 decimal places
    - Target value precision: 2 decimal places
    - Conservative Japanese stock lot rounding (DOWN to nearest 100)

    **Risk Management:**
    - Conservative account value rounding prevents over-allocation
    - Graceful error handling for missing data
    - Minimal allocation flagging for transparency
    """
    try:
        logger.info("Starting quantity calculation with IBKR account value")

        # Run the full quantity calculation pipeline (equivalent to qty.py main())
        success = await orchestrator_service.main()

        if not success:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Quantity calculation failed - check IBKR connection or universe data"
            )

        # Get account info for response details
        account_info = await orchestrator_service.get_account_info()

        logger.info("Quantity calculation completed successfully")

        return {
            "success": True,
            "account_value_used": account_info.get("rounded_account_value", 0),
            "original_account_value": account_info.get("account_value", 0),
            "currency": account_info.get("currency", "EUR"),
            "stocks_processed": 0,  # Could be enhanced to return actual count
            "universe_updated": True,
            "message": "Stock quantities calculated and universe.json updated"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during quantity calculation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during quantity calculation"
        )


@router.post(
    "/quantities/calculate-with-value",
    summary="Calculate Quantities with Custom Account Value",
    description="Calculate stock quantities using provided account value instead of fetching from IBKR",
    responses={
        200: {
            "description": "Quantity calculation with custom value completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "account_value_used": 10000.0,
                        "original_account_value": 10000.0,
                        "currency": "EUR",
                        "stocks_processed": 0,
                        "universe_updated": True,
                        "message": "Stock quantities calculated with custom account value"
                    }
                }
            }
        },
        400: {
            "description": "Invalid account value provided",
            "model": ErrorResponse
        },
        404: {
            "description": "Universe data not found",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error during quantity calculation",
            "model": ErrorResponse
        }
    }
)
async def calculate_quantities_with_value(
    account_value: float,
    currency: str = "EUR",
    orchestrator_service=Depends(get_quantity_orchestrator_service)
):
    """
    Calculate stock quantities using provided account value

    This endpoint allows calculating quantities without connecting to IBKR,
    useful for testing, simulation, or when using external account data.

    **Parameters:**
    - account_value: Account value in EUR to use for calculations
    - currency: Account currency (default: EUR)

    **Same Processing Logic as main endpoint:**
    - Conservative rounding DOWN to nearest 100€
    - EUR price and quantity calculations
    - Japanese stock lot size handling
    - Universe.json updates with account_total_value section
    """
    try:
        if account_value <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account value must be positive"
            )

        logger.info(f"Calculating quantities with provided account value: €{account_value:,.2f}")

        # Calculate quantities without fetching from IBKR
        success, stocks_processed = await orchestrator_service.calculate_quantities_only(
            account_value=account_value,
            currency=currency
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Quantity calculation failed - check universe data"
            )

        # Apply conservative rounding for response
        rounded_value = orchestrator_service.quantity_service.round_account_value_conservatively(account_value)

        logger.info("Quantity calculation with custom value completed successfully")

        return {
            "success": True,
            "account_value_used": rounded_value,
            "original_account_value": account_value,
            "currency": currency,
            "stocks_processed": stocks_processed,
            "universe_updated": True,
            "message": "Stock quantities calculated with custom account value"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during custom quantity calculation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during quantity calculation"
        )


@router.get(
    "/quantities",
    summary="Get Stock Quantities Data",
    description="Retrieve calculated stock quantities from universe.json",
    responses={
        200: {
            "description": "Stock quantities data retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "account_total_value": {
                            "value": 10000.0,
                            "currency": "EUR",
                            "timestamp": "2024-01-01 12:00:00"
                        },
                        "stocks_with_quantities": 150,
                        "total_stocks": 200,
                        "sample_stocks": [
                            {
                                "ticker": "AAPL",
                                "eur_price": 150.25,
                                "target_value_eur": 500.0,
                                "quantity": 3,
                                "final_target": 0.05
                            }
                        ]
                    }
                }
            }
        },
        404: {
            "description": "Universe data or account value not found",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error retrieving quantities data",
            "model": ErrorResponse
        }
    }
)
async def get_quantities_data(
    orchestrator_service=Depends(get_quantity_orchestrator_service)
):
    """
    Get calculated stock quantities from universe.json

    Returns:
    - Account total value information
    - Summary of stocks with calculated quantities
    - Sample of stocks with their quantity calculations
    - Metadata about quantity calculation status

    **Useful for:**
    - Verifying quantity calculations
    - Debugging allocation issues
    - Monitoring portfolio composition
    - Frontend display of calculated positions
    """
    try:
        logger.info("Retrieving stock quantities data")

        # Load universe data to extract quantity information
        universe_service = orchestrator_service.quantity_service
        universe_path = universe_service.universe_path

        if not universe_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Universe data not found - run data parsing first"
            )

        import json
        with open(universe_path, 'r', encoding='utf-8') as f:
            universe_data = json.load(f)

        # Check for account value data
        if "account_total_value" not in universe_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account value not found - run quantity calculation first"
            )

        account_value_info = universe_data["account_total_value"]

        # Count stocks with quantities
        stocks_with_quantities = 0
        total_stocks = 0
        sample_stocks = []

        # Process screens
        for screen_name, screen_data in universe_data.get("screens", {}).items():
            if isinstance(screen_data, dict) and "stocks" in screen_data:
                for stock in screen_data["stocks"]:
                    if isinstance(stock, dict):
                        total_stocks += 1
                        if "quantity" in stock:
                            stocks_with_quantities += 1
                            # Add to sample (first 5 stocks with quantities)
                            if len(sample_stocks) < 5:
                                sample_stocks.append({
                                    "ticker": stock.get("ticker", "Unknown"),
                                    "screen": screen_name,
                                    "eur_price": stock.get("eur_price", 0),
                                    "target_value_eur": stock.get("target_value_eur", 0),
                                    "quantity": stock.get("quantity", 0),
                                    "final_target": stock.get("final_target", 0),
                                    "currency": stock.get("currency", "Unknown"),
                                    "allocation_note": stock.get("allocation_note")
                                })

        # Process all_stocks if present
        for ticker, stock in universe_data.get("all_stocks", {}).items():
            if isinstance(stock, dict):
                total_stocks += 1
                if "quantity" in stock:
                    stocks_with_quantities += 1

        response_data = {
            "account_total_value": account_value_info,
            "stocks_with_quantities": stocks_with_quantities,
            "total_stocks": total_stocks,
            "sample_stocks": sample_stocks,
            "calculation_coverage": f"{stocks_with_quantities}/{total_stocks} stocks have calculated quantities",
            "last_updated": account_value_info.get("timestamp", "Unknown")
        }

        logger.info(f"Quantities data retrieved: {stocks_with_quantities}/{total_stocks} stocks with quantities")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving quantities data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving quantities data"
        )