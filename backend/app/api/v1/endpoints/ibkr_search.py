"""
IBKR Search Service API Endpoints
High-performance concurrent stock search with progress tracking
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field
import uuid
import time

from ....services.implementations.ibkr_search_service import IBKRSearchService
from ....models.errors import ErrorResponse

# Set up logging
logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/ibkr", tags=["IBKR Search"])

# Global service instance and task tracking
_ibkr_service: Optional[IBKRSearchService] = None
_running_tasks: Dict[str, Dict[str, Any]] = {}


def get_ibkr_service() -> IBKRSearchService:
    """Get or create IBKR service instance"""
    global _ibkr_service
    if _ibkr_service is None:
        _ibkr_service = IBKRSearchService(
            max_connections=5,
            cache_enabled=True
        )
    return _ibkr_service


# Request/Response Models
class StockSearchRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")
    isin: Optional[str] = Field(None, description="ISIN code")
    name: str = Field(..., description="Company name")
    currency: str = Field(..., description="Currency code (EUR, USD, etc.)")
    sector: Optional[str] = Field(None, description="Sector")
    country: Optional[str] = Field(None, description="Country")


class MultipleStockSearchRequest(BaseModel):
    stocks: List[StockSearchRequest] = Field(..., description="List of stocks to search")
    max_concurrent: int = Field(5, ge=1, le=10, description="Maximum concurrent connections")
    use_cache: bool = Field(True, description="Whether to use cached results")


class UniverseSearchRequest(BaseModel):
    universe_path: str = Field("data/universe.json", description="Path to universe.json file")
    output_path: str = Field("data/universe_with_ibkr.json", description="Output file path")
    max_concurrent: int = Field(5, ge=1, le=10, description="Maximum concurrent connections")
    use_cache: bool = Field(True, description="Whether to use cached results")


class IBKRContractDetails(BaseModel):
    symbol: str = Field(..., description="IBKR symbol")
    longName: str = Field(..., description="Full company name")
    currency: str = Field(..., description="Currency")
    exchange: str = Field(..., description="Exchange")
    primaryExchange: str = Field(..., description="Primary exchange")
    conId: int = Field(..., description="IBKR contract ID")
    search_method: str = Field(..., description="Search method used (isin/ticker/name)")
    match_score: float = Field(..., ge=0.0, le=1.0, description="Match confidence score")


class StockSearchResult(BaseModel):
    ticker: str = Field(..., description="Original ticker")
    found: bool = Field(..., description="Whether stock was found")
    contract_details: Optional[IBKRContractDetails] = Field(None, description="IBKR contract details if found")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Name similarity score")


class SearchTaskStatus(BaseModel):
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task status (running/completed/failed)")
    progress: Dict[str, Any] = Field(..., description="Progress information")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    started_at: float = Field(..., description="Task start timestamp")
    completed_at: Optional[float] = Field(None, description="Task completion timestamp")


class CacheStatistics(BaseModel):
    cache_hits: int = Field(..., description="Number of cache hits")
    cache_misses: int = Field(..., description="Number of cache misses")
    hit_rate: float = Field(..., ge=0.0, le=1.0, description="Cache hit rate")
    total_cached_symbols: int = Field(..., description="Total symbols in cache")


class ConnectionPoolStatus(BaseModel):
    total_connections: int = Field(..., description="Total connections in pool")
    available_connections: int = Field(..., description="Available connections")
    max_connections: int = Field(..., description="Maximum allowed connections")
    connections_healthy: int = Field(..., description="Number of healthy connections")


# Progress tracking for long-running tasks
class TaskProgressTracker:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.current = 0
        self.total = 0
        self.current_stock = ""

    def __call__(self, current: int, total: int, current_stock: str):
        self.current = current
        self.total = total
        self.current_stock = current_stock

        # Update global task tracking
        if self.task_id in _running_tasks:
            _running_tasks[self.task_id]["progress"] = {
                "current": current,
                "total": total,
                "current_stock": current_stock,
                "percentage": (current / total * 100) if total > 0 else 0
            }


@router.post("/search/stock", response_model=StockSearchResult)
async def search_single_stock(
    request: StockSearchRequest,
    use_cache: bool = Query(True, description="Whether to use cached results"),
    service: IBKRSearchService = Depends(get_ibkr_service)
):
    """
    Search for a single stock using comprehensive multi-strategy approach

    Uses ISIN → Ticker variations → Company name fallback strategy
    """
    try:
        stock_dict = request.dict()
        match, score = await service.search_single_stock(stock_dict, use_cache=use_cache)

        if match:
            contract_details = IBKRContractDetails(
                symbol=match["symbol"],
                longName=match["longName"],
                currency=match["currency"],
                exchange=match["exchange"],
                primaryExchange=match.get("primaryExchange", ""),
                conId=match.get("conId", 0),
                search_method=match.get("search_method", "unknown"),
                match_score=match.get("match_score", score)
            )

            return StockSearchResult(
                ticker=request.ticker,
                found=True,
                contract_details=contract_details,
                similarity_score=score
            )
        else:
            return StockSearchResult(
                ticker=request.ticker,
                found=False,
                contract_details=None,
                similarity_score=0.0
            )

    except Exception as e:
        logger.error(f"Error searching for stock {request.ticker}: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/search/batch", response_model=Dict[str, StockSearchResult])
async def search_multiple_stocks(
    request: MultipleStockSearchRequest,
    service: IBKRSearchService = Depends(get_ibkr_service)
):
    """
    Search for multiple stocks concurrently with optimized performance

    Returns results for all stocks with concurrent processing
    """
    try:
        stocks_list = [stock.dict() for stock in request.stocks]

        results = await service.search_multiple_stocks(
            stocks_list,
            max_concurrent=request.max_concurrent,
            use_cache=request.use_cache
        )

        formatted_results = {}
        for stock in request.stocks:
            ticker = stock.ticker
            match, score = results.get(ticker, (None, 0.0))

            if match:
                contract_details = IBKRContractDetails(
                    symbol=match["symbol"],
                    longName=match["longName"],
                    currency=match["currency"],
                    exchange=match["exchange"],
                    primaryExchange=match.get("primaryExchange", ""),
                    conId=match.get("conId", 0),
                    search_method=match.get("search_method", "unknown"),
                    match_score=match.get("match_score", score)
                )

                formatted_results[ticker] = StockSearchResult(
                    ticker=ticker,
                    found=True,
                    contract_details=contract_details,
                    similarity_score=score
                )
            else:
                formatted_results[ticker] = StockSearchResult(
                    ticker=ticker,
                    found=False,
                    contract_details=None,
                    similarity_score=0.0
                )

        return formatted_results

    except Exception as e:
        logger.error(f"Error in batch search: {e}")
        raise HTTPException(status_code=500, detail=f"Batch search failed: {str(e)}")


@router.post("/search/universe", response_model=Dict[str, str])
async def start_universe_search(
    request: UniverseSearchRequest,
    background_tasks: BackgroundTasks,
    service: IBKRSearchService = Depends(get_ibkr_service)
):
    """
    Start asynchronous search of all stocks in universe.json

    Returns task ID for tracking progress. This is the optimized version
    that should complete in under 5 minutes instead of 30+ minutes.
    """
    try:
        task_id = str(uuid.uuid4())

        # Initialize task tracking
        _running_tasks[task_id] = {
            "status": "running",
            "progress": {"current": 0, "total": 0, "current_stock": "", "percentage": 0},
            "result": None,
            "error": None,
            "started_at": time.time(),
            "completed_at": None
        }

        # Start background task
        async def run_universe_search():
            try:
                progress_tracker = TaskProgressTracker(task_id)

                result = await service.process_universe_stocks(
                    universe_path=request.universe_path,
                    output_path=request.output_path,
                    max_concurrent=request.max_concurrent,
                    use_cache=request.use_cache
                )

                # Mark as completed
                _running_tasks[task_id].update({
                    "status": "completed",
                    "result": result,
                    "completed_at": time.time()
                })

            except Exception as e:
                logger.error(f"Universe search task {task_id} failed: {e}")
                _running_tasks[task_id].update({
                    "status": "failed",
                    "error": str(e),
                    "completed_at": time.time()
                })

        background_tasks.add_task(run_universe_search)

        return {"task_id": task_id, "message": "Universe search started"}

    except Exception as e:
        logger.error(f"Error starting universe search: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start search: {str(e)}")


@router.get("/search/progress/{task_id}", response_model=SearchTaskStatus)
async def get_search_progress(task_id: str):
    """
    Get progress and status of a running search task
    """
    if task_id not in _running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task_info = _running_tasks[task_id]

    return SearchTaskStatus(
        task_id=task_id,
        status=task_info["status"],
        progress=task_info["progress"],
        result=task_info["result"],
        error=task_info["error"],
        started_at=task_info["started_at"],
        completed_at=task_info["completed_at"]
    )


@router.get("/search/results/{task_id}")
async def get_search_results(task_id: str):
    """
    Get final results of a completed search task
    """
    if task_id not in _running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task_info = _running_tasks[task_id]

    if task_info["status"] == "running":
        raise HTTPException(status_code=202, detail="Task still running")
    elif task_info["status"] == "failed":
        raise HTTPException(status_code=500, detail=task_info["error"])
    elif task_info["status"] == "completed":
        return task_info["result"]
    else:
        raise HTTPException(status_code=500, detail="Unknown task status")


@router.get("/cache/stats", response_model=CacheStatistics)
async def get_cache_statistics(service: IBKRSearchService = Depends(get_ibkr_service)):
    """
    Get cache performance statistics
    """
    try:
        stats = service.get_cache_statistics()
        return CacheStatistics(**stats)
    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.delete("/cache")
async def clear_cache(service: IBKRSearchService = Depends(get_ibkr_service)):
    """
    Clear all cached search results
    """
    try:
        success = await service.clear_cache()
        return {"success": success, "message": "Cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.get("/connections/status", response_model=ConnectionPoolStatus)
async def get_connection_pool_status(service: IBKRSearchService = Depends(get_ibkr_service)):
    """
    Get status of IBKR connection pool
    """
    try:
        status = await service.get_connection_pool_status()
        return ConnectionPoolStatus(**status)
    except Exception as e:
        logger.error(f"Error getting connection pool status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get connection status: {str(e)}")


@router.get("/universe/with-ibkr")
async def get_universe_with_ibkr(file_path: str = Query("data/universe_with_ibkr.json")):
    """
    Get the universe data with IBKR details
    """
    try:
        import json
        import os

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Universe file not found")

        with open(file_path, 'r', encoding='utf-8') as f:
            universe_data = json.load(f)

        return universe_data

    except Exception as e:
        logger.error(f"Error reading universe file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read universe file: {str(e)}")


@router.delete("/tasks/{task_id}")
async def cleanup_task(task_id: str):
    """
    Clean up a completed task from memory
    """
    if task_id not in _running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task_info = _running_tasks[task_id]
    if task_info["status"] == "running":
        raise HTTPException(status_code=400, detail="Cannot cleanup running task")

    del _running_tasks[task_id]
    return {"message": "Task cleaned up successfully"}


@router.get("/tasks")
async def list_tasks():
    """
    List all tracked tasks
    """
    return {
        "tasks": [
            {
                "task_id": task_id,
                "status": info["status"],
                "started_at": info["started_at"],
                "completed_at": info["completed_at"]
            }
            for task_id, info in _running_tasks.items()
        ]
    }