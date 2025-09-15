"""
Orders and Rebalancing API endpoints
Implements REST API for portfolio rebalancing and order generation
Following fintech best practices for trading system APIs
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import logging
import os
import json
import time
from ....core.dependencies import get_rebalancing_service
from ....core.exceptions import ValidationError
from ....models.schemas import (
    RebalancingResponse,
    OrdersResponse,
    PositionsResponse,
    TargetQuantitiesResponse
)
from ....models.errors import ErrorResponse

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["Orders & Rebalancing"])


@router.post(
    "/generate",
    response_model=RebalancingResponse,
    summary="Generate Rebalancing Orders",
    description="Generate buy/sell orders to rebalance portfolio to target allocations"
)
async def generate_orders(
    universe_file: Optional[str] = None,
    rebalancing_service = Depends(get_rebalancing_service)
):
    """
    Generate rebalancing orders based on target quantities vs current IBKR positions.
    """
    try:
        logger.info("Starting rebalancing order generation")

        # Use default universe file if not specified
        if universe_file is None:
            universe_file = "data/universe_with_ibkr.json"

        # Run rebalancing process
        results = rebalancing_service.run_rebalancing(universe_file)

        logger.info(f"Generated {results['metadata']['total_orders']} orders")

        return RebalancingResponse(
            success=True,
            orders=results['orders'],
            metadata=results['metadata'],
            target_quantities=results['target_quantities'],
            current_positions=results['current_positions'],
            message="Rebalancing orders generated successfully"
        )

    except FileNotFoundError as e:
        logger.error(f"Universe file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Universe file not found: {str(e)}"
        )
    except ConnectionError as e:
        logger.error(f"IBKR connection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to IBKR: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error generating orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating rebalancing orders: {str(e)}"
        )


@router.get(
    "",
    response_model=OrdersResponse,
    summary="Get Generated Orders",
    description="Retrieve the most recently generated orders from data/orders.json"
)
async def get_orders():
    """
    Get the most recently generated orders from the orders.json file.
    """
    try:
        # Get project root and orders file path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))
        orders_file = os.path.join(project_root, "data", "orders.json")

        if not os.path.exists(orders_file):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No orders found. Run order generation first."
            )

        with open(orders_file, 'r') as f:
            orders_data = json.load(f)

        return OrdersResponse(
            success=True,
            orders=orders_data['orders'],
            metadata=orders_data['metadata']
        )

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing orders file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error reading orders file"
        )
    except Exception as e:
        logger.error(f"Error retrieving orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving orders: {str(e)}"
        )


@router.get(
    "/positions/current",
    response_model=PositionsResponse,
    summary="Get Current IBKR Positions",
    description="Fetch current positions from IBKR account"
)
async def get_current_positions(rebalancing_service = Depends(get_rebalancing_service)):
    """
    Fetch current positions from IBKR account without generating orders.
    """
    try:
        logger.info("Fetching current IBKR positions")

        current_positions, contract_details = rebalancing_service.fetch_current_positions()

        return PositionsResponse(
            success=True,
            positions=current_positions,
            contract_details=contract_details,
            message="Current positions retrieved from IBKR"
        )

    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching current positions: {str(e)}"
        )


@router.get(
    "/positions/targets",
    response_model=TargetQuantitiesResponse,
    summary="Get Target Quantities",
    description="Calculate target quantities from universe data"
)
async def get_target_quantities(
    universe_file: Optional[str] = None,
    rebalancing_service = Depends(get_rebalancing_service)
):
    """
    Calculate target quantities from universe data without connecting to IBKR.
    """
    try:
        logger.info("Calculating target quantities")

        # Use default universe file if not specified
        if universe_file is None:
            universe_file = "data/universe_with_ibkr.json"

        # Load universe data
        universe_data = rebalancing_service.load_universe_data(universe_file)

        # Calculate target quantities
        target_quantities = rebalancing_service.calculate_target_quantities(universe_data)

        return TargetQuantitiesResponse(
            success=True,
            target_quantities=target_quantities,
            total_symbols=len(target_quantities),
            total_shares=sum(target_quantities.values()),
            message="Target quantities calculated successfully"
        )

    except FileNotFoundError as e:
        logger.error(f"Universe file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Universe file not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error calculating targets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating target quantities: {str(e)}"
        )