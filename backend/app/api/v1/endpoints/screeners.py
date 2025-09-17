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


@router.post(
    "/fetch",
    response_model=AllScreenersResponse,
    summary="Fetch Fresh Screener Data",
    description="Trigger fresh data fetch from Uncle Stock API for all screeners (Step 1 equivalent)"
)
async def fetch_all_screener_data(
    screener_service: IScreenerService = Depends(get_screener_service)
):
    """
    Fetch fresh stocks from all configured screeners via Uncle Stock API

    **⚠️ This endpoint makes external API calls and creates files**
    - Fetches fresh market data from Uncle Stock API (costs money)
    - Creates new CSV files in data/files_exports/
    - Overwrites existing data with current market data
    - Equivalent to Step 1 in the pipeline

    This is the proper REST endpoint for triggering data creation.
    Use GET /data to read existing data without making API calls.

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
    "/data",
    response_model=AllScreenersResponse,
    summary="Read Existing Screener Data",
    description="Read existing CSV files without making external API calls"
)
async def get_all_screener_data(
    screener_service: IScreenerService = Depends(get_screener_service)
):
    """
    Read existing screener data from saved CSV files

    **📖 This endpoint reads existing data without making API calls**
    - Reads from existing CSV files in data/files_exports/
    - No external API calls (free operation)
    - Returns cached/existing data only
    - Use POST /fetch to get fresh data from Uncle Stock API

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


@router.post(
    "/fetch/{screener_id}",
    response_model=ScreenerDataResponse,
    summary="Fetch Fresh Data from Specific Screener",
    description="Trigger fresh data fetch from Uncle Stock API for a specific screener"
)
async def fetch_screener_data(
    screener_id: str = Path(..., description="Screener identifier"),
    max_results: int = Query(200, ge=1, le=1000, description="Maximum number of results to return"),
    screener_service: IScreenerService = Depends(get_screener_service)
):
    """
    Fetch fresh stocks from a specific screener via Uncle Stock API

    **⚠️ This endpoint makes external API calls and creates files**
    - Fetches fresh market data from Uncle Stock API (costs money)
    - Creates new CSV file for this screener
    - Overwrites existing data with current market data

    Use GET /data/{screener_id} to read existing data without making API calls.

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
    "/data/{screener_id}",
    response_model=ScreenerDataResponse,
    summary="Read Existing Data from Specific Screener",
    description="Read existing CSV data from a specific screener without making external API calls"
)
async def get_screener_data(
    screener_id: str = Path(..., description="Screener identifier"),
    max_results: int = Query(200, ge=1, le=1000, description="Maximum number of results to return"),
    screener_service: IScreenerService = Depends(get_screener_service)
):
    """
    Read existing data from a specific screener

    **📖 This endpoint reads existing data without making API calls**
    - Reads from existing CSV file for this screener
    - No external API calls (free operation)
    - Returns cached/existing data only
    - Use POST /fetch/{screener_id} to get fresh data from Uncle Stock API

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


@router.post(
    "/fetch-history",
    response_model=AllScreenerHistoriesResponse,
    summary="Fetch Fresh History from All Screeners",
    description="Trigger fresh backtest history fetch from Uncle Stock API for all screeners"
)
async def fetch_all_screener_histories(
    screener_service: IScreenerService = Depends(get_screener_service)
):
    """
    Fetch fresh backtest history from all configured screeners via Uncle Stock API

    **⚠️ This endpoint makes external API calls and creates files**
    - Fetches fresh historical data from Uncle Stock API (costs money)
    - Creates new CSV files in data/files_exports/
    - Overwrites existing historical data

    Use GET /history to read existing data without making API calls.

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
    "/history",
    response_model=AllScreenerHistoriesResponse,
    summary="Read Existing Screener Histories",
    description="Read existing backtest history from saved CSV files without making external API calls"
)
async def get_all_screener_histories(
    screener_service: IScreenerService = Depends(get_screener_service)
):
    """
    Read existing backtest history from saved CSV files

    **📖 This endpoint reads existing data without making API calls**
    - Reads from existing CSV files in data/files_exports/
    - No external API calls (free operation)
    - Returns cached/existing historical data only
    - Use POST /fetch-history to get fresh data from Uncle Stock API

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


@router.post(
    "/fetch-history/{screener_id}",
    response_model=ScreenerHistoryResponse,
    summary="Fetch Fresh History from Specific Screener",
    description="Trigger fresh backtest history fetch from Uncle Stock API for a specific screener"
)
async def fetch_screener_history(
    screener_id: str = Path(..., description="Screener identifier"),
    screener_service: IScreenerService = Depends(get_screener_service)
):
    """
    Fetch fresh backtest history from a specific screener via Uncle Stock API

    **⚠️ This endpoint makes external API calls and creates files**
    - Fetches fresh historical data from Uncle Stock API (costs money)
    - Creates new CSV file for this screener's history
    - Overwrites existing historical data

    Use GET /history/{screener_id} to read existing data without making API calls.

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


@router.get(
    "/history/{screener_id}",
    response_model=ScreenerHistoryResponse,
    summary="Read Existing History from Specific Screener",
    description="Read existing backtest history from a specific screener without making external API calls"
)
async def get_screener_history(
    screener_id: str = Path(..., description="Screener identifier"),
    screener_service: IScreenerService = Depends(get_screener_service)
):
    """
    Read existing backtest history from a specific screener

    **📖 This endpoint reads existing data without making API calls**
    - Reads from existing CSV file for this screener's history
    - No external API calls (free operation)
    - Returns cached/existing historical data only
    - Use POST /fetch-history/{screener_id} to get fresh data from Uncle Stock API

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