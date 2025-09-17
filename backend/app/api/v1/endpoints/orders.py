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
from ....core.dependencies import get_rebalancing_service, get_order_execution_service, get_order_status_service
from ....core.exceptions import ValidationError
from ....models.schemas import (
    RebalancingResponse,
    OrdersResponse,
    PositionsResponse,
    TargetQuantitiesResponse,
    OrderExecutionWorkflowResponse,
    OrderStatusCheckResponse
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
            # Get absolute path to backend/data/universe_with_ibkr.json
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
            universe_file = os.path.join(backend_root, "data", "universe_with_ibkr.json")

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
        # Get absolute path to backend/data/orders.json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # From backend/app/api/v1/endpoints -> go up to backend/
        backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
        orders_file = os.path.join(backend_root, "data", "orders.json")

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
            # Get absolute path to backend/data/universe_with_ibkr.json
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
            universe_file = os.path.join(backend_root, "data", "universe_with_ibkr.json")

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


@router.post(
    "/execute",
    response_model=OrderExecutionWorkflowResponse,
    summary="Execute Orders through IBKR",
    description="Execute the generated orders through Interactive Brokers API (Step 10)"
)
async def execute_orders(
    orders_file: Optional[str] = None,
    max_orders: Optional[int] = None,
    delay_between_orders: float = 1.0,
    order_type: str = "GTC_MKT",
    order_execution_service = Depends(get_order_execution_service)
):
    """
    Execute orders through Interactive Brokers API.
    This is the API equivalent of step 10 in the legacy pipeline.
    """
    try:
        logger.info("Starting order execution workflow (Step 10)")

        # Use default orders file if not specified
        if orders_file is None:
            # Get absolute path to backend/data/orders.json
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # From backend/app/api/v1/endpoints -> go up to backend/
            backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
            orders_file = os.path.join(backend_root, "data", "orders.json")

        # Run complete execution workflow
        result = await order_execution_service.run_execution(
            orders_file=orders_file,
            max_orders=max_orders,
            delay_between_orders=delay_between_orders,
            order_type=order_type
        )

        logger.info(f"Order execution workflow completed. Success: {result['success']}")

        return OrderExecutionWorkflowResponse(**result)

    except FileNotFoundError as e:
        logger.error(f"Orders file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orders file not found: {str(e)}"
        )
    except ConnectionError as e:
        logger.error(f"IBKR connection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to IBKR: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error executing orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing orders: {str(e)}"
        )


@router.post(
    "/status",
    response_model=OrderStatusCheckResponse,
    summary="Check Order Status (Step 11)",
    description="Validate and check status of executed orders through IBKR API"
)
async def check_order_status(
    orders_file: Optional[str] = None,
    order_status_service = Depends(get_order_status_service)
):
    """
    Check order status and validate execution results.
    This is the API equivalent of step 11 in the legacy pipeline.
    """
    try:
        logger.info("Starting order status check (Step 11)")

        # Use default orders file if not specified
        if orders_file is None:
            # Get absolute path to backend/data/orders.json
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # From backend/app/api/v1/endpoints -> go up to backend/
            backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
            orders_file = os.path.join(backend_root, "data", "orders.json")

        # First set the orders file path
        order_status_service.orders_file = orders_file

        # Run complete status check workflow
        success = order_status_service.run_status_check()

        if success:
            # Get verification results after successful check
            result = order_status_service.get_verification_results()
            result['success'] = True
        else:
            result = {
                'success': False,
                'error_message': 'Order status check failed'
            }

        logger.info(f"Order status check completed. Success: {result['success']}")

        return OrderStatusCheckResponse(**result)

    except FileNotFoundError as e:
        logger.error(f"Orders file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orders file not found: {str(e)}"
        )
    except ConnectionError as e:
        logger.error(f"IBKR connection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to IBKR: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error checking order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking order status: {str(e)}"
        )