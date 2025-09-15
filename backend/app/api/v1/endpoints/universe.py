"""
Universe API endpoints
Handles universe data parsing, retrieval, and field operations
"""
import time
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from fastapi.responses import JSONResponse
from typing import Optional

from ....core.dependencies import get_universe_service
from ....models.schemas import (
    UniverseResponse,
    ParseUniverseRequest,
    ParseUniverseResponse,
    StockFieldRequest,
    StockFieldResponse,
    AvailableFieldsResponse
)
from ....services.interfaces import IUniverseRepository
from ....core.exceptions import ValidationError, ConfigurationError

router = APIRouter(prefix="/universe", tags=["universe"])


@router.post("/parse", response_model=ParseUniverseResponse)
async def parse_universe(
    request: ParseUniverseRequest,
    universe_service: IUniverseRepository = Depends(get_universe_service)
) -> ParseUniverseResponse:
    """
    Parse all screener CSV files and create universe.json

    This endpoint wraps the legacy create_universe() + save_universe() functions
    to maintain 100% behavioral compatibility with CLI step2_parse_data()
    """
    try:
        start_time = time.time()

        # Create universe from CSV files (identical to CLI behavior)
        universe = universe_service.create_universe()

        # Save universe to JSON file (identical to CLI behavior)
        universe_service.save_universe(universe, request.output_path)

        processing_time = time.time() - start_time

        # Extract metadata for response
        metadata = universe_service.get_universe_metadata(universe)

        return ParseUniverseResponse(
            success=True,
            message=f"Universe created successfully with {metadata.get('unique_stocks', 0)} unique stocks",
            universe_path=request.output_path,
            metadata=metadata,
            processing_time=processing_time
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Required CSV files not found: {str(e)}"
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied when writing universe file: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create universe: {str(e)}"
        )


@router.get("", response_model=UniverseResponse)
async def get_universe(
    universe_path: str = Query(
        default="data/universe.json",
        description="Path to the universe.json file"
    ),
    universe_service: IUniverseRepository = Depends(get_universe_service)
) -> UniverseResponse:
    """
    Load and return universe data from JSON file

    Returns the complete universe structure including metadata,
    screens, and all unique stocks data
    """
    try:
        universe = universe_service.load_universe(universe_path)

        if universe is None:
            raise HTTPException(
                status_code=404,
                detail=f"Universe file not found at {universe_path}"
            )

        return UniverseResponse(**universe)

    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail=f"Universe file not found: {str(e)}"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load universe: {str(e)}"
        )


@router.get("/stock/{ticker}/field", response_model=StockFieldResponse)
async def get_stock_field(
    ticker: str = Path(..., description="Stock ticker symbol (e.g., 'AAPL')"),
    request: StockFieldRequest = Depends(),
    universe_service: IUniverseRepository = Depends(get_universe_service)
) -> StockFieldResponse:
    """
    Get specific field value for a stock from screener data

    Searches across CSV files to find the requested field for the given ticker.
    This wraps the legacy get_stock_field() function for compatibility.
    """
    try:
        result = universe_service.get_stock_field(
            ticker=ticker,
            header_name=request.header_name,
            subtitle_pattern=request.subtitle_pattern,
            screen_name=request.screen_name
        )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Field '{request.header_name}' with pattern '{request.subtitle_pattern}' not found for ticker '{ticker}'"
            )

        return StockFieldResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stock field: {str(e)}"
        )


@router.get("/fields/available", response_model=AvailableFieldsResponse)
async def get_available_fields(
    csv_path: Optional[str] = Query(
        default=None,
        description="Optional path to specific CSV file. If not provided, uses first available screen."
    ),
    universe_service: IUniverseRepository = Depends(get_universe_service)
) -> AvailableFieldsResponse:
    """
    Discover all available header/subtitle combinations in CSV files

    This wraps the legacy find_available_fields() function to help
    users understand what field combinations they can query for.
    """
    try:
        # Get the data parser from universe service (we need to access it)
        # For now, we'll use the legacy function directly
        from ....services.implementations.legacy.parser import find_available_fields

        raw_fields = find_available_fields(csv_path)

        # Convert to API response format
        fields = [
            {
                "header": header,
                "subtitle": subtitle,
                "column_index": column_index
            }
            for header, subtitle, column_index in raw_fields
        ]

        return AvailableFieldsResponse(
            fields=fields,
            total_count=len(fields),
            csv_file=csv_path
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve available fields: {str(e)}"
        )


@router.get("/metadata")
async def get_universe_metadata(
    universe_path: str = Query(
        default="data/universe.json",
        description="Path to the universe.json file"
    ),
    universe_service: IUniverseRepository = Depends(get_universe_service)
):
    """
    Get universe metadata without loading all stock data

    Useful for getting quick stats about the universe size and configuration
    """
    try:
        universe = universe_service.load_universe(universe_path)

        if universe is None:
            raise HTTPException(
                status_code=404,
                detail=f"Universe file not found at {universe_path}"
            )

        metadata = universe_service.get_universe_metadata(universe)
        return metadata

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load universe metadata: {str(e)}"
        )


@router.get("/stocks/{ticker}")
async def get_stock_by_ticker(
    ticker: str = Path(..., description="Stock ticker symbol"),
    universe_path: str = Query(
        default="data/universe.json",
        description="Path to the universe.json file"
    ),
    universe_service: IUniverseRepository = Depends(get_universe_service)
):
    """
    Get detailed information for a specific stock

    Returns all available data for the given ticker from the universe
    """
    try:
        universe = universe_service.load_universe(universe_path)

        if universe is None:
            raise HTTPException(
                status_code=404,
                detail=f"Universe file not found at {universe_path}"
            )

        stock_data = universe_service.search_stocks_by_ticker(universe, ticker)

        if stock_data is None:
            raise HTTPException(
                status_code=404,
                detail=f"Stock '{ticker}' not found in universe"
            )

        return stock_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stock data: {str(e)}"
        )


@router.get("/stocks/multi-screen")
async def get_multi_screen_stocks(
    universe_path: str = Query(
        default="data/universe.json",
        description="Path to the universe.json file"
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of stocks to return"
    ),
    universe_service: IUniverseRepository = Depends(get_universe_service)
):
    """
    Get stocks that appear in multiple screens

    Returns stocks that are present in more than one screener,
    which often indicates higher quality or consensus picks
    """
    try:
        universe = universe_service.load_universe(universe_path)

        if universe is None:
            raise HTTPException(
                status_code=404,
                detail=f"Universe file not found at {universe_path}"
            )

        multi_screen_stocks = universe_service.get_stocks_in_multiple_screens(universe)

        # Apply limit
        limited_stocks = multi_screen_stocks[:limit]

        return {
            "stocks": [
                {
                    "ticker": ticker,
                    "screens": data.get("screens", []),
                    "screen_count": len(data.get("screens", [])),
                    "data": data
                }
                for ticker, data in limited_stocks
            ],
            "total_multi_screen_stocks": len(multi_screen_stocks),
            "returned_count": len(limited_stocks)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve multi-screen stocks: {str(e)}"
        )