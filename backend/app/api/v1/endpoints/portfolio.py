"""
Portfolio optimization API endpoints
Implements REST API for portfolio optimization functionality
Following fintech best practices for financial data APIs
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging
from ....core.dependencies import get_portfolio_optimizer_service
from ....core.exceptions import ValidationError
from ....models.schemas import (
    ErrorResponse,
    PortfolioOptimizationResponse,
    QuarterlyReturnsResponse
)

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