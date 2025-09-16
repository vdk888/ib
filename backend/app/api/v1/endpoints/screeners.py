"""
Screener API endpoints
Provides REST API interface for screener data fetching operations
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging

from ....models.schemas import (
    ScreenerDataResponse,
    ScreenerHistoryResponse,
    AllScreenersResponse,
    AllScreenerHistoriesResponse,
    AvailableScreenersResponse,
    ScreenerRequest,
    LegacyScreenerResponse
)
from ....models.errors import ErrorResponse
from ....services.interfaces import IScreenerService
from ....services.implementations.screener_service import ScreenerService
from ....core.exceptions import (
    UncleStockInvalidQueryError,
    UncleStockTimeoutError,
    UncleStockRateLimitError,
    UncleStockAPIError
)
from ....core.dependencies import get_screener_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screeners", tags=["screeners"])


@router.get(
    "/available",
    response_model=AvailableScreenersResponse,
    summary="Get Available Screeners",
    description="Retrieve list of all available screener configurations"
)
async def get_available_screeners(
    screener_service: IScreenerService = Depends(get_screener_service)
):
    """
    Get list of available screener configurations

    Returns:
        List of screener IDs and their display names
    """
    try:
        screeners = screener_service.get_available_screeners()
        return AvailableScreenersResponse(screeners=screeners)

    except Exception as e:
        logger.error(f"Failed to get available screeners: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve available screeners"
        )


@router.get(
    "/data",
    response_model=AllScreenersResponse,
    summary="Get All Screener Data",
    description="Fetch current stocks from all configured screeners (equivalent to get_all_screeners())"
)
async def get_all_screener_data(
    screener_service: IScreenerService = Depends(get_screener_service)
):
    """
    Fetch current stocks from all configured screeners

    This endpoint replicates the exact behavior of the legacy get_all_screeners() function,
    including console output for CLI compatibility when used in testing.

    Returns:
        Results for all screeners with metadata and summary statistics
    """
    try:
        # Fetch data from all screeners
        results = await screener_service.fetch_all_screener_data()

        # Convert to response format with enhanced metadata
        screener_responses = {}
        for screener_id, result in results.items():
            screener_responses[screener_id] = ScreenerDataResponse(
                success=result.get("success", False),
                data=result.get("data"),
                raw_response=result.get("raw_response"),
                csv_file=result.get("csv_file"),
                screener_name=result.get("screener_name")
            )

        # Calculate summary statistics
        total_screeners = len(screener_responses)
        successful_screeners = sum(1 for r in screener_responses.values() if r.success)

        return AllScreenersResponse(
            screeners=screener_responses,
            total_screeners=total_screeners,
            successful_screeners=successful_screeners
        )

    except UncleStockTimeoutError as e:
        logger.warning(f"Uncle Stock API timeout: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Uncle Stock API temporarily unavailable - timeout occurred"
        )
    except UncleStockRateLimitError as e:
        logger.warning(f"Uncle Stock API rate limit: {str(e)}")
        raise HTTPException(
            status_code=429,
            detail="Uncle Stock API rate limit exceeded"
        )
    except Exception as e:
        logger.error(f"Failed to fetch all screener data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch screener data"
        )


@router.get(
    "/data/{screener_id}",
    response_model=ScreenerDataResponse,
    summary="Get Specific Screener Data",
    description="Fetch current stocks from a specific screener (equivalent to get_current_stocks())"
)
async def get_screener_data(
    screener_id: str = Path(..., description="Screener identifier"),
    max_results: int = Query(200, ge=1, le=1000, description="Maximum number of results to return"),
    screener_service: IScreenerService = Depends(get_screener_service)
):
    """
    Fetch current stocks from a specific screener

    This endpoint replicates the exact behavior of the legacy get_current_stocks() function.

    Args:
        screener_id: Screener identifier from available configurations
        max_results: Maximum number of stocks to return (1-1000, default 200)

    Returns:
        Screener data with stock symbols, CSV file path, and metadata

    Raises:
        404: If screener_id is not found in configuration
        429: If Uncle Stock API rate limit is exceeded
        503: If Uncle Stock API times out
    """
    try:
        result = await screener_service.fetch_screener_data(
            screener_id=screener_id,
            max_results=max_results
        )

        return ScreenerDataResponse(
            success=result.get("success", False),
            data=result.get("data"),
            raw_response=result.get("raw_response"),
            csv_file=result.get("csv_file"),
            screener_name=result.get("screener_name")
        )

    except UncleStockInvalidQueryError as e:
        logger.warning(f"Invalid screener ID: {screener_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Screener not found: {screener_id}"
        )
    except UncleStockTimeoutError as e:
        logger.warning(f"Uncle Stock API timeout for {screener_id}: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Uncle Stock API temporarily unavailable - timeout occurred"
        )
    except UncleStockRateLimitError as e:
        logger.warning(f"Uncle Stock API rate limit for {screener_id}: {str(e)}")
        raise HTTPException(
            status_code=429,
            detail="Uncle Stock API rate limit exceeded"
        )
    except Exception as e:
        logger.error(f"Failed to fetch screener data for {screener_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch data for screener: {screener_id}"
        )


@router.get(
    "/history",
    response_model=AllScreenerHistoriesResponse,
    summary="Get All Screener Histories",
    description="Fetch backtest history from all configured screeners (equivalent to get_all_screener_histories())"
)
async def get_all_screener_histories(
    screener_service: IScreenerService = Depends(get_screener_service)
):
    """
    Fetch backtest history from all configured screeners

    This endpoint replicates the exact behavior of the legacy get_all_screener_histories() function,
    including console output for CLI compatibility when used in testing.

    Returns:
        Historical data for all screeners with metadata and summary statistics
    """
    try:
        # Fetch history from all screeners
        results = await screener_service.fetch_all_screener_histories()

        # Convert to response format with enhanced metadata
        screener_responses = {}
        for screener_id, result in results.items():
            screener_responses[screener_id] = ScreenerHistoryResponse(
                success=result.get("success", False),
                data=result.get("data"),
                raw_response=result.get("raw_response"),
                csv_file=result.get("csv_file"),
                screener_name=result.get("screener_name")
            )

        # Calculate summary statistics
        total_screeners = len(screener_responses)
        successful_screeners = sum(1 for r in screener_responses.values() if r.success)

        return AllScreenerHistoriesResponse(
            screeners=screener_responses,
            total_screeners=total_screeners,
            successful_screeners=successful_screeners
        )

    except UncleStockTimeoutError as e:
        logger.warning(f"Uncle Stock API timeout: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Uncle Stock API temporarily unavailable - timeout occurred"
        )
    except UncleStockRateLimitError as e:
        logger.warning(f"Uncle Stock API rate limit: {str(e)}")
        raise HTTPException(
            status_code=429,
            detail="Uncle Stock API rate limit exceeded"
        )
    except Exception as e:
        logger.error(f"Failed to fetch all screener histories: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch screener histories"
        )


@router.get(
    "/history/{screener_id}",
    response_model=ScreenerHistoryResponse,
    summary="Get Specific Screener History",
    description="Fetch backtest history from a specific screener (equivalent to get_screener_history())"
)
async def get_screener_history(
    screener_id: str = Path(..., description="Screener identifier"),
    screener_service: IScreenerService = Depends(get_screener_service)
):
    """
    Fetch backtest history from a specific screener

    This endpoint replicates the exact behavior of the legacy get_screener_history() function.

    Args:
        screener_id: Screener identifier from available configurations

    Returns:
        Historical backtest data with CSV file path and metadata

    Raises:
        404: If screener_id is not found in configuration
        429: If Uncle Stock API rate limit is exceeded
        503: If Uncle Stock API times out
    """
    try:
        result = await screener_service.fetch_screener_history(screener_id=screener_id)

        return ScreenerHistoryResponse(
            success=result.get("success", False),
            data=result.get("data"),
            raw_response=result.get("raw_response"),
            csv_file=result.get("csv_file"),
            screener_name=result.get("screener_name")
        )

    except UncleStockInvalidQueryError as e:
        logger.warning(f"Invalid screener ID: {screener_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Screener not found: {screener_id}"
        )
    except UncleStockTimeoutError as e:
        logger.warning(f"Uncle Stock API timeout for {screener_id}: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Uncle Stock API temporarily unavailable - timeout occurred"
        )
    except UncleStockRateLimitError as e:
        logger.warning(f"Uncle Stock API rate limit for {screener_id}: {str(e)}")
        raise HTTPException(
            status_code=429,
            detail="Uncle Stock API rate limit exceeded"
        )
    except Exception as e:
        logger.error(f"Failed to fetch screener history for {screener_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch history for screener: {screener_id}"
        )


# Legacy compatibility endpoints - exact format matching
@router.get(
    "/legacy/data/{screener_id}",
    response_model=LegacyScreenerResponse,
    summary="Get Screener Data (Legacy Format)",
    description="Legacy endpoint returning exact format as original get_current_stocks() function"
)
async def get_screener_data_legacy(
    screener_id: str = Path(..., description="Screener identifier"),
    max_results: int = Query(200, ge=1, le=1000, description="Maximum number of results to return"),
    screener_service: IScreenerService = Depends(get_screener_service)
):
    """
    Legacy compatibility endpoint for exact format matching

    Returns the exact same dict structure as the original get_current_stocks() function
    for 100% backward compatibility during migration testing.
    """
    try:
        result = await screener_service.fetch_screener_data(
            screener_id=screener_id,
            max_results=max_results
        )

        # Return in exact legacy format
        return LegacyScreenerResponse(
            success=result.get("success", False),
            data=result.get("data"),
            raw_response=result.get("raw_response"),
            csv_file=result.get("csv_file")
        )

    except UncleStockInvalidQueryError:
        return LegacyScreenerResponse(
            success=False,
            data=f"Unknown screener ID: {screener_id}",
            raw_response=None
        )
    except Exception as e:
        return LegacyScreenerResponse(
            success=False,
            data=str(e),
            raw_response=None
        )


@router.get(
    "/legacy/history/{screener_id}",
    response_model=LegacyScreenerResponse,
    summary="Get Screener History (Legacy Format)",
    description="Legacy endpoint returning exact format as original get_screener_history() function"
)
async def get_screener_history_legacy(
    screener_id: str = Path(..., description="Screener identifier"),
    screener_service: IScreenerService = Depends(get_screener_service)
):
    """
    Legacy compatibility endpoint for exact format matching

    Returns the exact same dict structure as the original get_screener_history() function
    for 100% backward compatibility during migration testing.
    """
    try:
        result = await screener_service.fetch_screener_history(screener_id=screener_id)

        # Return in exact legacy format
        return LegacyScreenerResponse(
            success=result.get("success", False),
            data=result.get("data"),
            raw_response=result.get("raw_response"),
            csv_file=result.get("csv_file")
        )

    except UncleStockInvalidQueryError:
        return LegacyScreenerResponse(
            success=False,
            data=f"Unknown screener ID: {screener_id}",
            raw_response=None
        )
    except Exception as e:
        return LegacyScreenerResponse(
            success=False,
            data=str(e),
            raw_response=None
        )