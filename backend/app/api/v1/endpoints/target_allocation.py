"""
Target Allocation API endpoints
Handles final stock allocation calculations based on screener targets and performance ranking
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import ValidationError

from ....core.dependencies import get_target_allocation_service
from ....services.interfaces import ITargetAllocationService
from ....models.schemas import (
    TargetAllocationResponse,
    AllocationSummaryResponse,
    ScreenerAllocationsResponse,
    ScreenerRankingsResponse,
    CalculateTargetsRequest,
    UniverseAllocationUpdateResponse,
    StockAllocationData,
    AllocationSummaryData,
    AllocationSummaryStats,
    Top10Allocation,
    ScreenerAllocation,
    StockRanking,
    UniverseAllocationUpdate
)
from ....models.errors import ErrorResponse
from ....core.exceptions import (
    BaseServiceError,
    ValidationError as ServiceValidationError,
    ConfigurationError
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/calculate",
    response_model=TargetAllocationResponse,
    summary="Calculate final stock allocations",
    description="""
    Calculate final stock allocations based on:
    1. Screener allocations from portfolio optimizer
    2. Stock performance ranking within each screener (180d price change)
    3. Linear allocation within screener (best: MAX_ALLOCATION%, worst: MIN_ALLOCATION%)

    This is the main endpoint equivalent to CLI `step6_calculate_targets()`.
    """,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request or missing data"},
        404: {"model": ErrorResponse, "description": "Universe file not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def calculate_target_allocations(
    request: CalculateTargetsRequest,
    service: ITargetAllocationService = Depends(get_target_allocation_service)
):
    """
    Calculate final stock allocations and optionally update universe.json
    """
    try:
        logger.info(f"Starting target allocation calculation (force_recalculate={request.force_recalculate})")

        # Run the main allocation calculation process
        success = service.main()

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Target allocation calculation failed"
            )

        # Load the updated universe data to get allocation results
        universe_data = service.load_universe_data()
        final_allocations = service.calculate_final_allocations(universe_data)

        # Convert to response format
        allocation_data = {}
        for ticker, alloc_info in final_allocations.items():
            allocation_data[ticker] = StockAllocationData(
                ticker=alloc_info['ticker'],
                screener=alloc_info['screener'],
                rank=alloc_info['rank'],
                performance_180d=alloc_info['performance_180d'],
                pocket_allocation=alloc_info['pocket_allocation'],
                screener_target=alloc_info['screener_target'],
                final_allocation=alloc_info['final_allocation']
            )

        logger.info(f"Successfully calculated allocations for {len(allocation_data)} stocks")

        return TargetAllocationResponse(
            success=True,
            message=f"Successfully calculated target allocations for {len(allocation_data)} stocks",
            allocation_data=allocation_data,
            universe_updated=request.save_to_universe
        )

    except FileNotFoundError as e:
        logger.error(f"Universe file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Universe file not found: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Data validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in target allocation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/summary",
    response_model=AllocationSummaryResponse,
    summary="Get allocation summary",
    description="""
    Get formatted allocation summary data (JSON equivalent of display_allocation_summary).
    Includes:
    - All allocations sorted by final allocation
    - Total allocation percentage
    - Top 10 allocations
    - Summary statistics
    """,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request or no allocation data"},
        404: {"model": ErrorResponse, "description": "Universe file not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_allocation_summary(
    service: ITargetAllocationService = Depends(get_target_allocation_service)
):
    """
    Get allocation summary data in JSON format
    """
    try:
        logger.info("Retrieving allocation summary")

        # Load universe and calculate allocations
        universe_data = service.load_universe_data()
        final_allocations = service.calculate_final_allocations(universe_data)

        if not final_allocations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No allocation data available. Run target calculation first."
            )

        # Get summary data from service
        summary_data = service.get_allocation_summary(final_allocations)

        # Convert to response format
        sorted_allocations = []
        for alloc in summary_data['sorted_allocations']:
            sorted_allocations.append(StockAllocationData(
                ticker=alloc['ticker'],
                screener=alloc['screener'],
                rank=alloc['screener_rank'],
                performance_180d=alloc['performance_180d'],
                pocket_allocation=alloc['pocket_allocation'],
                screener_target=alloc['screener_target'],
                final_allocation=alloc['final_allocation']
            ))

        top_10_allocations = []
        for top_alloc in summary_data['top_10_allocations']:
            top_10_allocations.append(Top10Allocation(
                rank_overall=top_alloc['rank_overall'],
                ticker=top_alloc['ticker'],
                final_allocation=top_alloc['final_allocation'],
                screener=top_alloc['screener'],
                screener_rank=top_alloc['screener_rank'],
                performance_180d=top_alloc['performance_180d']
            ))

        summary_stats = AllocationSummaryStats(
            total_stocks=summary_data['summary_stats']['total_stocks'],
            total_allocation_pct=summary_data['summary_stats']['total_allocation_pct'],
            stocks_with_allocation=summary_data['summary_stats']['stocks_with_allocation']
        )

        allocation_summary = AllocationSummaryData(
            sorted_allocations=sorted_allocations,
            total_allocation=summary_data['total_allocation'],
            top_10_allocations=top_10_allocations,
            summary_stats=summary_stats
        )

        logger.info(f"Generated allocation summary for {len(sorted_allocations)} stocks")

        return AllocationSummaryResponse(
            success=True,
            summary=allocation_summary
        )

    except FileNotFoundError as e:
        logger.error(f"Universe file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Universe file not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error generating allocation summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate allocation summary: {str(e)}"
        )


@router.get(
    "/screener-allocations",
    response_model=ScreenerAllocationsResponse,
    summary="Get screener allocations from portfolio optimizer",
    description="""
    Extract screener target allocations from portfolio optimization results.
    These are used as the basis for individual stock allocations within each screener.
    """,
    responses={
        400: {"model": ErrorResponse, "description": "No portfolio optimization data available"},
        404: {"model": ErrorResponse, "description": "Universe file not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_screener_allocations(
    service: ITargetAllocationService = Depends(get_target_allocation_service)
):
    """
    Get screener allocations from portfolio optimization results
    """
    try:
        logger.info("Retrieving screener allocations")

        # Load universe data
        universe_data = service.load_universe_data()

        # Extract screener allocations
        screener_allocations = service.extract_screener_allocations(universe_data)

        # Build detailed screener data
        screeners_data = []
        screens_config = universe_data.get('screens', {})

        for screener_id, allocation in screener_allocations.items():
            # Find screener display name
            screener_name = screener_id
            for screen_key, screen_data in screens_config.items():
                if screen_key == screener_id or screen_key.replace('_', ' ').lower() == screener_id.lower():
                    screener_name = screen_data.get('name', screener_id)
                    break

            screeners_data.append(ScreenerAllocation(
                screener_id=screener_id,
                screener_name=screener_name,
                allocation=allocation
            ))

        logger.info(f"Retrieved allocations for {len(screener_allocations)} screeners")

        return ScreenerAllocationsResponse(
            success=True,
            screener_allocations=screener_allocations,
            screeners_data=screeners_data
        )

    except FileNotFoundError as e:
        logger.error(f"Universe file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Universe file not found: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Portfolio optimization data not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Portfolio optimization data not available: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error retrieving screener allocations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve screener allocations: {str(e)}"
        )


@router.get(
    "/rankings/{screener_id}",
    response_model=ScreenerRankingsResponse,
    summary="Get stock rankings for a specific screener",
    description="""
    Get stock rankings within a specific screener based on 180-day performance.
    Shows how stocks are ranked and allocated within each screener.
    """,
    responses={
        404: {"model": ErrorResponse, "description": "Screener not found or universe file missing"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_screener_rankings(
    screener_id: str,
    service: ITargetAllocationService = Depends(get_target_allocation_service)
):
    """
    Get stock rankings for a specific screener
    """
    try:
        logger.info(f"Retrieving rankings for screener: {screener_id}")

        # Load universe data
        universe_data = service.load_universe_data()

        # Find the screener
        screener_data = None
        screener_name = screener_id

        for screen_key, screen_data in universe_data.get('screens', {}).items():
            if screen_key == screener_id or screen_key.replace('_', ' ').lower() == screener_id.lower():
                screener_data = screen_data
                screener_name = screen_data.get('name', screener_id)
                break

        if not screener_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Screener '{screener_id}' not found"
            )

        stocks = screener_data.get('stocks', [])
        if not stocks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No stocks found in screener '{screener_id}'"
            )

        # Rank the stocks
        ranked_stocks = service.rank_stocks_in_screener(stocks)

        # Build response
        rankings = []
        stocks_with_allocation = 0

        for stock, rank, performance in ranked_stocks:
            pocket_allocation = service.calculate_pocket_allocation(rank, len(stocks))

            if pocket_allocation > 0:
                stocks_with_allocation += 1

            rankings.append(StockRanking(
                ticker=stock.get('ticker', 'UNKNOWN'),
                rank=rank,
                performance_180d=performance,
                pocket_allocation=pocket_allocation
            ))

        logger.info(f"Generated rankings for {len(rankings)} stocks in screener {screener_id}")

        return ScreenerRankingsResponse(
            success=True,
            screener_id=screener_id,
            screener_name=screener_name,
            rankings=rankings,
            total_stocks=len(rankings),
            stocks_with_allocation=stocks_with_allocation
        )

    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(f"Universe file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Universe file not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error retrieving screener rankings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve screener rankings: {str(e)}"
        )


@router.get(
    "/",
    response_model=TargetAllocationResponse,
    summary="Get current target allocations from universe",
    description="""
    Get the current target allocations that have been calculated and saved to universe.json.
    This endpoint reads existing allocation data without recalculating.
    """,
    responses={
        400: {"model": ErrorResponse, "description": "No allocation data found"},
        404: {"model": ErrorResponse, "description": "Universe file not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_current_target_allocations(
    service: ITargetAllocationService = Depends(get_target_allocation_service)
):
    """
    Get current target allocations from universe.json
    """
    try:
        logger.info("Retrieving current target allocations from universe")

        # Load universe data
        universe_data = service.load_universe_data()

        # Check if we have allocation data in the universe
        allocation_data = {}
        has_allocation_data = False

        # Check all_stocks for allocation data
        all_stocks = universe_data.get('all_stocks', {})
        for ticker, stock_data in all_stocks.items():
            if 'final_target' in stock_data and stock_data.get('final_target', 0) > 0:
                has_allocation_data = True
                allocation_data[ticker] = StockAllocationData(
                    ticker=ticker,
                    screener=stock_data.get('screens', ['Unknown'])[0] if stock_data.get('screens') else 'Unknown',
                    rank=stock_data.get('rank', 0),
                    performance_180d=0.0,  # This would need to be extracted from price_180d_change
                    pocket_allocation=stock_data.get('allocation_target', 0.0),
                    screener_target=stock_data.get('screen_target', 0.0),
                    final_allocation=stock_data.get('final_target', 0.0)
                )

        if not has_allocation_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No target allocation data found in universe. Run allocation calculation first."
            )

        logger.info(f"Retrieved current allocations for {len(allocation_data)} stocks")

        return TargetAllocationResponse(
            success=True,
            message=f"Retrieved current target allocations for {len(allocation_data)} stocks",
            allocation_data=allocation_data,
            universe_updated=False
        )

    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(f"Universe file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Universe file not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error retrieving current allocations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve current allocations: {str(e)}"
        )