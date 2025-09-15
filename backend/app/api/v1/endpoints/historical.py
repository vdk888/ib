"""
Historical Data API endpoints
Provides REST API interface for historical performance data operations
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging

from ....models.schemas import (
    HistoricalDataResponse,
    BacktestDataResponse,
    PerformanceSummaryResponse,
    UpdateUniverseResponse
)
from ....models.errors import ErrorResponse
from ....services.interfaces import IHistoricalDataService
from ....services.implementations.historical_data_service import HistoricalDataService
from ....core.exceptions import (
    ValidationError,
    ConfigurationError,
    BaseServiceError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/historical", tags=["historical-data"])


def get_historical_data_service() -> IHistoricalDataService:
    """Dependency injection for historical data service"""
    return HistoricalDataService()


@router.get(
    "/screeners/backtest",
    response_model=BacktestDataResponse,
    summary="Get All Backtest Data",
    description="Parse and return backtest data for all configured screeners"
)
async def get_all_backtest_data(
    historical_service: IHistoricalDataService = Depends(get_historical_data_service)
):
    """
    Get backtest data for all configured screeners

    Returns:
        Dict mapping screener IDs to their parsed performance data
        Each screener entry contains metadata, quarterly_performance, and statistics
    """
    try:
        logger.info("Fetching all backtest data")

        backtest_data = await historical_service.get_all_backtest_data()

        # Count successful vs failed parsings
        successful_screeners = sum(1 for data in backtest_data.values() if "error" not in data)
        failed_screeners = len(backtest_data) - successful_screeners

        return BacktestDataResponse(
            success=True,
            data=backtest_data,
            metadata={
                "total_screeners": len(backtest_data),
                "successful_parsings": successful_screeners,
                "failed_parsings": failed_screeners
            }
        )

    except Exception as e:
        logger.error(f"Error fetching all backtest data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="BACKTEST_DATA_FETCH_ERROR",
                message="Failed to fetch backtest data for all screeners",
                details={"error": str(e)}
            ).dict()
        )


@router.get(
    "/screeners/backtest/{screener_id}",
    response_model=HistoricalDataResponse,
    summary="Get Screener Backtest Data",
    description="Parse and return backtest data for a specific screener"
)
async def get_screener_backtest_data(
    screener_id: str = Path(..., description="Screener ID from configuration"),
    debug: bool = Query(False, description="Enable debug output"),
    historical_service: IHistoricalDataService = Depends(get_historical_data_service)
):
    """
    Get backtest data for a specific screener

    Args:
        screener_id: Screener identifier from UNCLE_STOCK_SCREENS config
        debug: Enable debug console output

    Returns:
        Dict containing parsed backtest data or error information
    """
    try:
        logger.info(f"Fetching backtest data for screener: {screener_id}")

        backtest_data = await historical_service.get_screener_backtest_data(screener_id)

        if "error" in backtest_data:
            raise HTTPException(
                status_code=404 if "not found" in backtest_data["error"].lower() else 400,
                detail=ErrorResponse(
                    error_code="SCREENER_BACKTEST_ERROR",
                    message=f"Failed to get backtest data for screener {screener_id}",
                    details=backtest_data
                ).dict()
            )

        return HistoricalDataResponse(
            success=True,
            screener_id=screener_id,
            data=backtest_data,
            metadata={
                "quarters_parsed": len(backtest_data.get("quarterly_performance", [])),
                "statistics_available": len(backtest_data.get("statistics", {})) > 0,
                "metadata_available": len(backtest_data.get("metadata", {})) > 0
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching backtest data for screener {screener_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="SCREENER_BACKTEST_FETCH_ERROR",
                message=f"Internal error while fetching backtest data for screener {screener_id}",
                details={"error": str(e)}
            ).dict()
        )


@router.get(
    "/performance/summary",
    response_model=PerformanceSummaryResponse,
    summary="Get Performance Summary",
    description="Get formatted performance summary for all screeners (JSON equivalent of CLI display)"
)
async def get_performance_summary(
    historical_service: IHistoricalDataService = Depends(get_historical_data_service)
):
    """
    Get formatted performance summary for all screeners

    Returns:
        Dict containing structured performance data suitable for API responses
        Equivalent to display_performance_summary() but returns JSON instead of console output
    """
    try:
        logger.info("Generating performance summary")

        summary_data = await historical_service.get_performance_summary()

        return PerformanceSummaryResponse(
            success=True,
            summary=summary_data,
            metadata={
                "screeners_count": len(summary_data.get("screeners", {})),
                "generated_at": "2023-12-01T00:00:00Z"  # This would be current timestamp in real implementation
            }
        )

    except Exception as e:
        logger.error(f"Error generating performance summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="PERFORMANCE_SUMMARY_ERROR",
                message="Failed to generate performance summary",
                details={"error": str(e)}
            ).dict()
        )


@router.post(
    "/universe/update",
    response_model=UpdateUniverseResponse,
    summary="Update Universe with History",
    description="Update universe.json with historical performance data in metadata section"
)
async def update_universe_with_history(
    historical_service: IHistoricalDataService = Depends(get_historical_data_service)
):
    """
    Update universe.json with historical performance data

    Side Effects:
        - Reads data/universe.json
        - Adds metadata.historical_performance section with comprehensive metrics
        - Writes updated universe.json back to disk
        - Console output for success/error status

    Returns:
        Success status and operation metadata
    """
    try:
        logger.info("Updating universe.json with historical performance data")

        success = await historical_service.update_universe_with_history()

        if not success:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="UNIVERSE_UPDATE_FAILED",
                    message="Failed to update universe.json with historical data",
                    details={"possible_causes": [
                        "universe.json file not found",
                        "CSV backtest files not found",
                        "Permission issues writing to universe.json",
                        "Invalid JSON structure in universe.json"
                    ]}
                ).dict()
            )

        return UpdateUniverseResponse(
            success=True,
            message="Universe.json successfully updated with historical performance data",
            metadata={
                "operation": "universe_history_update",
                "file_updated": "data/universe.json",
                "section_added": "metadata.historical_performance"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating universe with history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="UNIVERSE_UPDATE_ERROR",
                message="Internal error while updating universe with historical data",
                details={"error": str(e)}
            ).dict()
        )