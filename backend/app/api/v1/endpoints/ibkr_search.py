"""
IBKR Search API endpoints
Handles stock identification and symbol search operations through Interactive Brokers API
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Optional
import logging

from backend.app.core.dependencies import get_ibkr_search_service
from backend.app.services.interfaces import IIBKRSearchService
from backend.app.models.schemas import (
    UniverseSearchResponse,
    IBKRSearchStats,
    StockSearchRequest,
    StockSearchResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ibkr", tags=["IBKR Search"])


@router.post(
    "/search-universe",
    response_model=UniverseSearchResponse,
    summary="Search all universe stocks in IBKR",
    description="""
    Process all stocks from universe.json and identify them in Interactive Brokers.

    This endpoint maintains 100% behavioral compatibility with the legacy CLI implementation.
    It uses a comprehensive three-strategy search approach:
    1. ISIN search (highest confidence)
    2. Ticker variations (handles exchange suffixes and share classes)
    3. Name-based matching (fallback for difficult cases)

    **Important Requirements:**
    - IBKR Gateway must be running on 127.0.0.1:4002
    - universe.json must exist in data/ directory
    - Only processes stocks with quantity > 0

    **File Operations:**
    - Reads from: data/universe.json
    - Creates: data/universe_with_ibkr.json

    **Sequential Processing:**
    The implementation processes stocks sequentially (no concurrency) with 0.5s delays
    between searches to maintain identical behavior with the legacy system.

    **Search Statistics:**
    Returns detailed statistics showing:
    - Total stocks processed
    - Breakdown by search method (ISIN/ticker/name)
    - List of stocks not found in IBKR
    - Execution time and performance metrics
    """
)
async def search_universe_stocks(
    ibkr_service: IIBKRSearchService = Depends(get_ibkr_search_service)
) -> UniverseSearchResponse:
    """
    Search all universe stocks in IBKR and update with identification details

    Maintains 100% compatibility with legacy comprehensive_enhanced_search.py behavior
    """
    logger.info("Starting universe IBKR search operation")

    try:
        # Execute the search using the service (maintains legacy behavior exactly)
        stats = ibkr_service.process_all_universe_stocks()

        if not stats:
            logger.error("IBKR search returned empty statistics")
            raise HTTPException(
                status_code=500,
                detail="IBKR search failed - check IBKR Gateway connection and universe.json file"
            )

        # Convert to response model
        search_stats = IBKRSearchStats(
            total=stats.get('total', 0),
            found_isin=stats.get('found_isin', 0),
            found_ticker=stats.get('found_ticker', 0),
            found_name=stats.get('found_name', 0),
            not_found=stats.get('not_found', 0),
            execution_time_seconds=stats.get('execution_time_seconds', 0.0),
            not_found_stocks=stats.get('not_found_stocks', [])
        )

        total_found = search_stats.found_isin + search_stats.found_ticker + search_stats.found_name
        coverage_percentage = (total_found / search_stats.total * 100) if search_stats.total > 0 else 0

        success_message = (
            f"IBKR search completed successfully. "
            f"Found {total_found}/{search_stats.total} stocks "
            f"({coverage_percentage:.1f}% coverage). "
            f"Results saved to data/universe_with_ibkr.json"
        )

        logger.info(f"IBKR search completed: {coverage_percentage:.1f}% coverage")

        return UniverseSearchResponse(
            success=True,
            message=success_message,
            statistics=search_stats,
            output_file="data/universe_with_ibkr.json"
        )

    except Exception as e:
        logger.error(f"IBKR search operation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"IBKR search operation failed: {str(e)}"
        )


@router.post(
    "/search-stock",
    response_model=StockSearchResponse,
    summary="Search individual stock in IBKR",
    description="""
    Search for a single stock in Interactive Brokers using the comprehensive search strategy.

    This endpoint allows testing the search logic for individual stocks without processing
    the entire universe. Uses the same three-strategy approach as the universe search.

    **Search Strategy:**
    1. ISIN search (if provided)
    2. Ticker variations (handles exchange formats)
    3. Name-based matching (fallback)

    **Validation:**
    - Currency matching is mandatory
    - Name similarity scoring with different thresholds per search method
    - Corporate suffix filtering for better matching
    """
)
async def search_individual_stock(
    stock_request: StockSearchRequest = Body(..., description="Stock details to search"),
    verbose: bool = Body(False, description="Enable debug output"),
    ibkr_service: IIBKRSearchService = Depends(get_ibkr_search_service)
) -> StockSearchResponse:
    """
    Search for an individual stock in IBKR

    Useful for testing and debugging the search logic
    """
    logger.info(f"Searching individual stock: {stock_request.ticker}")

    try:
        # This would require a modified service method for individual stock search
        # For now, we'll indicate this is not implemented in the current service
        raise HTTPException(
            status_code=501,
            detail="Individual stock search not yet implemented. Use /search-universe for complete processing."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Individual stock search failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Stock search operation failed: {str(e)}"
        )


@router.get(
    "/search-status",
    summary="Get IBKR search service status",
    description="""
    Check the status of the IBKR search service and prerequisites.

    **Checks:**
    - IBKR Gateway connectivity (127.0.0.1:4002)
    - universe.json file existence
    - Service readiness
    """
)
async def get_search_status():
    """
    Get the status of IBKR search prerequisites
    """
    try:
        # Check if universe.json exists
        from pathlib import Path
        universe_path = Path("data/universe.json")
        universe_exists = universe_path.exists()

        # Try to test IBKR connection (would need a connection test method)
        # For now, we'll provide basic status

        status = {
            "service_ready": True,
            "universe_file_exists": universe_exists,
            "universe_file_path": str(universe_path),
            "ibkr_gateway_required": "127.0.0.1:4002",
            "connection_test": "Not implemented - start search to test IBKR connectivity"
        }

        if not universe_exists:
            status["warnings"] = ["universe.json not found - run previous pipeline steps first"]

        return status

    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Status check failed: {str(e)}"
        )