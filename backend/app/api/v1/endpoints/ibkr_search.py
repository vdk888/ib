"""
IBKR Search API Endpoints
Implements stock search functionality with IBKR Gateway integration
Exact replication of comprehensive_enhanced_search.py behavior with quantity filtering
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional
import asyncio
from pathlib import Path

from ....core.dependencies import get_ibkr_search_service
from ....services.ibkr_interface import IIBKRSearchService
from ....models.schemas import (
    StockSearchRequest,
    StockSearchResponse,
    UniverseSearchResponse,
    IBKRSearchStats,
    IBKRContractDetails
)
from ....models.errors import ErrorResponse

router = APIRouter(prefix="/ibkr/search", tags=["IBKR Search"])


@router.get(
    "/universe",
    response_model=UniverseSearchResponse,
    summary="Search all universe stocks with quantities > 0",
    description="""
    Processes all stocks from universe.json that have quantities > 0
    using comprehensive IBKR search strategies:

    1. ISIN-based search (most reliable)
    2. Ticker variations search (handles exchange suffixes)
    3. Company name matching search (fallback)

    Exact replication of comprehensive_enhanced_search.py behavior
    but filtered to only process stocks with quantities > 0.

    Expected to process ~123 stocks instead of all 439.
    """,
    responses={
        200: {"description": "Search completed successfully"},
        500: {"description": "IBKR connection or processing error"},
        503: {"description": "IBKR Gateway not available"}
    }
)
async def search_universe_stocks(
    max_concurrent: int = 5,
    use_cache: bool = True,
    ibkr_service: IIBKRSearchService = Depends(get_ibkr_search_service)
) -> UniverseSearchResponse:
    """
    Search all universe stocks with quantities > 0 using comprehensive IBKR search.

    This endpoint replicates the exact behavior of comprehensive_enhanced_search.py
    but filters the universe to only process stocks with quantities > 0.

    Args:
        max_concurrent: Maximum concurrent IBKR connections (default: 5)
        use_cache: Whether to use cached results if available (default: True)

    Returns:
        Complete search results with statistics and found/not found stocks
    """
    try:
        # Process universe stocks with filtering for quantities > 0
        universe_path = 'data/universe.json'
        output_path = 'data/universe_with_ibkr_filtered.json'

        stats = ibkr_service.process_universe_stocks(
            universe_path=universe_path,
            output_path=output_path,
            max_concurrent=max_concurrent,
            use_cache=use_cache,
            quantity_filter=True  # NEW: Filter for quantities > 0
        )

        return UniverseSearchResponse(
            success=True,
            message="Universe search completed successfully",
            statistics=IBKRSearchStats(**stats),
            output_file=output_path
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Universe file not found: {e}"
        )
    except ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"IBKR Gateway connection failed: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Universe search failed: {e}"
        )


@router.post(
    "/stock",
    response_model=StockSearchResponse,
    summary="Search individual stock using comprehensive strategies",
    description="""
    Search for a single stock using the same comprehensive search strategies
    as the legacy comprehensive_enhanced_search.py implementation:

    1. ISIN search if available
    2. Ticker variations (handles exchange suffixes like .PA, .L, .T)
    3. Company name matching as fallback

    Includes sophisticated validation using name similarity and word overlap.
    """,
    responses={
        200: {"description": "Search completed (may or may not find match)"},
        400: {"description": "Invalid stock data provided"},
        503: {"description": "IBKR Gateway not available"}
    }
)
async def search_stock(
    stock_request: StockSearchRequest,
    use_cache: bool = True,
    ibkr_service: IIBKRSearchService = Depends(get_ibkr_search_service)
) -> StockSearchResponse:
    """
    Search for individual stock using comprehensive IBKR search strategies.

    Replicates the exact search logic from comprehensive_enhanced_search.py
    including all ticker variations, name matching, and validation rules.

    Args:
        stock_request: Stock details (ticker, isin, name, currency, etc.)
        use_cache: Whether to use cached results if available

    Returns:
        Search result with match details or not found status
    """
    try:
        # Convert request to stock dictionary format expected by service
        stock_dict = {
            "ticker": stock_request.ticker,
            "isin": stock_request.isin,
            "name": stock_request.name,
            "currency": stock_request.currency,
            "sector": stock_request.sector,
            "country": stock_request.country
        }

        # Perform comprehensive search
        match, similarity_score = ibkr_service.search_single_stock(
            stock=stock_dict,
            use_cache=use_cache
        )

        if match:
            return StockSearchResponse(
                success=True,
                found=True,
                message=f"Stock found via {match.get('search_method', 'unknown')} search",
                stock=stock_request,
                ibkr_details=IBKRContractDetails(
                    symbol=match['symbol'],
                    longName=match['longName'],
                    currency=match['currency'],
                    exchange=match['exchange'],
                    primaryExchange=match.get('primaryExchange', ''),
                    conId=match.get('conId', 0),
                    search_method=match.get('search_method', 'unknown'),
                    match_score=similarity_score
                )
            )
        else:
            return StockSearchResponse(
                success=True,
                found=False,
                message="Stock not found in IBKR",
                stock=stock_request,
                ibkr_details=None
            )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stock data: {e}"
        )
    except ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"IBKR Gateway connection failed: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Stock search failed: {e}"
        )


@router.get(
    "/cache/stats",
    response_model=Dict[str, Any],
    summary="Get cache performance statistics",
    description="Returns cache hit rates and performance metrics for IBKR search operations"
)
async def get_cache_stats(
    ibkr_service: IIBKRSearchService = Depends(get_ibkr_search_service)
) -> Dict[str, Any]:
    """Get cache performance statistics"""
    try:
        return ibkr_service.get_cache_statistics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache statistics: {e}"
        )


@router.delete(
    "/cache",
    response_model=Dict[str, bool],
    summary="Clear search cache",
    description="Clears all cached IBKR search results"
)
async def clear_cache(
    ibkr_service: IIBKRSearchService = Depends(get_ibkr_search_service)
) -> Dict[str, bool]:
    """Clear all cached search results"""
    try:
        success = ibkr_service.clear_cache()
        return {"cleared": success}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {e}"
        )


@router.get(
    "/connections/status",
    response_model=Dict[str, Any],
    summary="Get IBKR connection pool status",
    description="Returns status and health information for IBKR Gateway connections"
)
async def get_connection_status(
    ibkr_service: IIBKRSearchService = Depends(get_ibkr_search_service)
) -> Dict[str, Any]:
    """Get IBKR connection pool status and health"""
    try:
        return ibkr_service.get_connection_pool_status()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get connection status: {e}"
        )