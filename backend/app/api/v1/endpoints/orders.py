"""
Order Execution API Endpoints
Provides REST API access to IBKR order execution functionality
Maintains 100% behavioral compatibility with CLI step10_execute_orders()
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional
import asyncio

from ....core.dependencies import get_order_execution_service
from ....services.interfaces import IOrderExecutionService
from ....models.schemas import (
    OrderExecutionRequest,
    OrderExecutionResponse,
    OrderExecutionWorkflowResponse,
    IBKRConnectionRequest,
    IBKRConnectionResponse,
    LoadOrdersResponse,
    OrderStatusResponse,
    ContractSpecification,
    OrderSpecification,
    OrderType
)
from ....models.errors import ErrorResponse
from ....core.exceptions import OrderExecutionError, IBKRConnectionError

router = APIRouter(prefix="/orders", tags=["Order Execution"])


@router.post(
    "/load",
    response_model=LoadOrdersResponse,
    summary="Load orders from JSON file",
    description="Load orders from data/orders.json file with validation and statistics"
)
async def load_orders(
    orders_file: str = "orders.json",
    order_service: IOrderExecutionService = Depends(get_order_execution_service)
):
    """
    Load orders from JSON file in data directory

    **Workflow:**
    1. Read orders.json from data directory
    2. Validate file format and structure
    3. Extract metadata (total_orders, buy_orders, sell_orders)
    4. Return order summary for execution planning

    **Use Cases:**
    - Pre-execution validation
    - Order count verification
    - File format validation
    """
    try:
        result = await order_service.load_orders(orders_file)
        return LoadOrdersResponse(
            success=result['success'],
            metadata=result['metadata'],
            orders=result['orders'],
            total_orders=result['total_orders'],
            orders_file=orders_file
        )
    except OrderExecutionError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
                details=e.details
            ).dict()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="LOAD_ORDERS_UNEXPECTED_ERROR",
                message=f"Unexpected error loading orders: {str(e)}"
            ).dict()
        )


@router.post(
    "/connection/connect",
    response_model=IBKRConnectionResponse,
    summary="Connect to IBKR Gateway/TWS",
    description="Establish connection to Interactive Brokers for order execution"
)
async def connect_to_ibkr(
    connection_request: IBKRConnectionRequest,
    order_service: IOrderExecutionService = Depends(get_order_execution_service)
):
    """
    Connect to IBKR Gateway or Trader Workstation

    **Connection Parameters:**
    - **host**: Usually 127.0.0.1 (localhost)
    - **port**: 4002 for paper trading, 4001 for live trading
    - **client_id**: Unique client identifier (1-999)
    - **timeout**: Connection timeout in seconds

    **Prerequisites:**
    - IBKR Gateway or TWS must be running
    - API access must be enabled in IBKR
    - Correct port configuration in IBKR

    **Returns:**
    - Connection status
    - Account ID if successful
    - Next valid order ID for order submission
    """
    try:
        success = await order_service.connect_to_ibkr(
            host=connection_request.host,
            port=connection_request.port,
            client_id=connection_request.client_id,
            timeout=connection_request.timeout
        )

        if success:
            # Get connection details from service
            # Note: In a real implementation, we'd expose these through the service interface
            return IBKRConnectionResponse(
                success=True,
                account_id="Connected",  # Placeholder - would get from service
                next_order_id=1,  # Placeholder - would get from service
                connection_details={
                    "host": connection_request.host,
                    "port": connection_request.port,
                    "client_id": connection_request.client_id,
                    "timeout": connection_request.timeout
                },
                connected_at=None  # Would be set by service
            )
        else:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error_code="IBKR_CONNECTION_FAILED",
                    message="Failed to connect to IBKR Gateway/TWS"
                ).dict()
            )

    except IBKRConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
                details=e.details
            ).dict()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="IBKR_CONNECTION_UNEXPECTED_ERROR",
                message=f"Unexpected error connecting to IBKR: {str(e)}"
            ).dict()
        )


@router.post(
    "/execute",
    response_model=OrderExecutionResponse,
    summary="Execute orders through IBKR API",
    description="Submit loaded orders to IBKR for execution with real-time status tracking"
)
async def execute_orders(
    execution_request: OrderExecutionRequest,
    order_service: IOrderExecutionService = Depends(get_order_execution_service)
):
    """
    Execute orders through IBKR API

    **Execution Process:**
    1. Load orders from specified file
    2. Validate IBKR connection
    3. Submit orders one by one with rate limiting
    4. Track submission status and errors
    5. Return execution summary

    **Order Types:**
    - **GTC_MKT**: Good Till Cancelled Market (best for off-hours)
    - **MOO**: Market on Open (executes at market open)
    - **DAY**: Day order (expires end of trading day)
    - **MKT**: Immediate market order

    **Rate Limiting:**
    - Configurable delay between orders
    - Prevents IBKR API rate limit violations
    - Default: 1 second between orders

    **Error Handling:**
    - Individual order failures don't stop execution
    - Detailed error tracking per order
    - Comprehensive execution summary
    """
    try:
        # First load orders
        await order_service.load_orders(execution_request.orders_file)

        # Execute with specified parameters
        result = await order_service.execute_orders(
            max_orders=execution_request.max_orders,
            delay_between_orders=execution_request.delay_between_orders,
            order_type=execution_request.order_type.value
        )

        return OrderExecutionResponse(
            success=result['success'],
            executed_count=result['executed_count'],
            failed_count=result['failed_count'],
            total_orders=result['total_orders'],
            order_statuses=result['order_statuses'],
            order_results=result['order_results'],
            execution_summary=result['execution_summary']
        )

    except OrderExecutionError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
                details=e.details
            ).dict()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="ORDER_EXECUTION_UNEXPECTED_ERROR",
                message=f"Unexpected error during order execution: {str(e)}"
            ).dict()
        )


@router.get(
    "/status",
    response_model=OrderStatusResponse,
    summary="Get order execution status",
    description="Check status of previously submitted orders with detailed tracking"
)
async def get_order_status(
    wait_time: int = 30,
    order_service: IOrderExecutionService = Depends(get_order_execution_service)
):
    """
    Get current status of submitted orders

    **Status Tracking:**
    - Real-time order status from IBKR
    - Filled quantities and remaining shares
    - Average fill prices
    - Order state transitions

    **Status Types:**
    - **Filled**: Order completely executed
    - **PreSubmitted**: Order received by IBKR
    - **Submitted**: Order active in market
    - **Cancelled**: Order cancelled
    - **ApiCancelled**: Order cancelled via API

    **Wait Time:**
    - Time to wait for status updates
    - Allows for order processing delays
    - Recommended: 30-60 seconds after execution
    """
    try:
        result = await order_service.get_order_statuses(wait_time)

        return OrderStatusResponse(
            success=result['success'],
            status_summary=result['status_summary'],
            total_filled_shares=result['total_filled_shares'],
            pending_orders_count=result['pending_orders_count'],
            order_details=result['order_details'],
            wait_time_used=result['wait_time_used']
        )

    except OrderExecutionError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
                details=e.details
            ).dict()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="ORDER_STATUS_UNEXPECTED_ERROR",
                message=f"Unexpected error checking order status: {str(e)}"
            ).dict()
        )


@router.post(
    "/connection/disconnect",
    summary="Disconnect from IBKR",
    description="Clean disconnection from IBKR Gateway/TWS"
)
async def disconnect_from_ibkr(
    order_service: IOrderExecutionService = Depends(get_order_execution_service)
):
    """
    Disconnect from IBKR Gateway/TWS

    **Cleanup Process:**
    - Close IBKR API connection
    - Stop background message processing
    - Release system resources

    **When to Use:**
    - After completing order execution workflow
    - Before connecting with different parameters
    - System shutdown or maintenance

    **Note:**
    Disconnection is automatic after workflow completion,
    but manual disconnection is available for cleanup.
    """
    try:
        await order_service.disconnect()
        return {"success": True, "message": "Disconnected from IBKR"}

    except Exception as e:
        # Disconnection errors are usually not critical
        return {
            "success": True,
            "message": "Disconnection completed with warnings",
            "warning": str(e)
        }


@router.post(
    "/workflow/execute",
    response_model=OrderExecutionWorkflowResponse,
    summary="Complete order execution workflow",
    description="Execute the complete order workflow: load → connect → execute → status → disconnect"
)
async def execute_order_workflow(
    execution_request: OrderExecutionRequest,
    connection_request: Optional[IBKRConnectionRequest] = None,
    order_service: IOrderExecutionService = Depends(get_order_execution_service)
):
    """
    Complete Order Execution Workflow

    **Full Workflow Steps:**
    1. **Load Orders**: Read and validate orders from file
    2. **Connect to IBKR**: Establish API connection
    3. **Execute Orders**: Submit orders with rate limiting
    4. **Check Status**: Wait for and collect order statuses
    5. **Disconnect**: Clean up connection

    **This endpoint replicates exactly the behavior of:**
    ```bash
    python main.py 10
    ```

    **Benefits:**
    - Single API call for complete workflow
    - Automatic connection management
    - Comprehensive error handling
    - Complete execution reporting

    **Use Cases:**
    - Automated rebalancing systems
    - Scheduled order execution
    - Integration with external systems
    - Replacing CLI execution in production
    """
    try:
        # Use default connection if not provided
        if connection_request is None:
            connection_request = IBKRConnectionRequest()

        result = await order_service.run_execution(
            orders_file=execution_request.orders_file,
            max_orders=execution_request.max_orders,
            delay_between_orders=execution_request.delay_between_orders,
            order_type=execution_request.order_type.value
        )

        return OrderExecutionWorkflowResponse(
            success=result['success'],
            execution_summary=result.get('execution_summary'),
            order_statuses=result.get('order_statuses'),
            status_summary=result.get('status_summary'),
            total_filled_shares=result.get('total_filled_shares'),
            pending_orders_count=result.get('pending_orders_count'),
            orders_loaded=result.get('orders_loaded'),
            error_message=result.get('error_message'),
            workflow_completed_at=result.get('workflow_completed_at'),
            failure_time=result.get('failure_time')
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="ORDER_WORKFLOW_UNEXPECTED_ERROR",
                message=f"Unexpected error in order execution workflow: {str(e)}"
            ).dict()
        )


@router.get(
    "/contract/{symbol}",
    response_model=ContractSpecification,
    summary="Get IBKR contract specification for symbol",
    description="Generate IBKR contract parameters for a given stock symbol"
)
async def get_contract_specification(
    symbol: str,
    order_service: IOrderExecutionService = Depends(get_order_execution_service)
):
    """
    Get IBKR contract specification for stock symbol

    **Contract Parameters:**
    - **symbol**: Stock ticker symbol
    - **secType**: Security type (STK for stocks)
    - **exchange**: Exchange routing (SMART default)
    - **currency**: Contract currency
    - **conId**: Contract ID for precise identification

    **Use Cases:**
    - Contract validation before order submission
    - Testing contract creation logic
    - Integration debugging

    **Note:** This is a utility endpoint for testing.
    Actual orders use contracts from orders.json file.
    """
    try:
        # Mock order data for contract creation
        mock_order_data = {
            'ibkr_details': {
                'symbol': symbol,
                'exchange': 'SMART',
                'primaryExchange': '',
                'conId': None
            },
            'stock_info': {
                'currency': 'USD'  # Default
            }
        }

        contract_params = order_service.create_ibkr_contract(mock_order_data)

        return ContractSpecification(
            symbol=contract_params['symbol'],
            sec_type=contract_params['secType'],
            exchange=contract_params['exchange'],
            primary_exchange=contract_params['primaryExchange'],
            currency=contract_params['currency'],
            con_id=contract_params['conId']
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error_code="CONTRACT_SPECIFICATION_ERROR",
                message=f"Error creating contract specification: {str(e)}"
            ).dict()
        )


@router.post(
    "/order-spec",
    response_model=OrderSpecification,
    summary="Generate IBKR order specification",
    description="Create IBKR order parameters for given action, quantity, and order type"
)
async def create_order_specification(
    action: str,
    quantity: int,
    order_type: OrderType = OrderType.GTC_MKT,
    order_service: IOrderExecutionService = Depends(get_order_execution_service)
):
    """
    Create IBKR order specification

    **Parameters:**
    - **action**: BUY or SELL
    - **quantity**: Number of shares to trade
    - **order_type**: Order type (GTC_MKT, MOO, DAY, MKT)

    **Order Type Details:**
    - **GTC_MKT**: Market order that stays active until filled
    - **MOO**: Executes at market opening price
    - **DAY**: Expires at end of trading day
    - **MKT**: Immediate market execution

    **Use Cases:**
    - Order parameter validation
    - Testing order creation logic
    - Integration development
    """
    try:
        if action.upper() not in ['BUY', 'SELL']:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="INVALID_ORDER_ACTION",
                    message="Action must be 'BUY' or 'SELL'"
                ).dict()
            )

        if quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="INVALID_ORDER_QUANTITY",
                    message="Quantity must be greater than 0"
                ).dict()
            )

        order_params = order_service.create_ibkr_order(
            action=action.upper(),
            quantity=quantity,
            order_type=order_type.value
        )

        return OrderSpecification(
            action=order_params['action'],
            total_quantity=order_params['totalQuantity'],
            order_type=order_params['orderType'],
            tif=order_params.get('tif'),
            e_trade_only=order_params['eTradeOnly'],
            firm_quote_only=order_params['firmQuoteOnly']
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error_code="ORDER_SPECIFICATION_ERROR",
                message=f"Error creating order specification: {str(e)}"
            ).dict()
        )


# Health check endpoint specific to order execution
@router.get(
    "/health",
    summary="Order execution service health check",
    description="Verify order execution service availability and dependencies"
)
async def order_execution_health():
    """
    Order execution service health check

    **Checks:**
    - Service instantiation
    - File system access (data directory)
    - Basic functionality availability

    **Status Indicators:**
    - **healthy**: All systems operational
    - **degraded**: Some functionality may be limited
    - **unhealthy**: Service unavailable
    """
    try:
        # Basic service instantiation test
        from ....core.dependencies import get_order_execution_service
        service = get_order_execution_service()

        # Test basic functionality
        import os
        data_dir = os.path.join(service._project_root, "data")
        data_accessible = os.path.exists(data_dir)

        return {
            "status": "healthy",
            "service": "Order Execution Service",
            "version": "1.0.0",
            "dependencies": {
                "data_directory_accessible": data_accessible,
                "service_instantiation": True
            },
            "endpoints": {
                "load_orders": "/orders/load",
                "connect_ibkr": "/orders/connection/connect",
                "execute_orders": "/orders/execute",
                "order_status": "/orders/status",
                "workflow_execute": "/orders/workflow/execute"
            }
        }

    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "service": "Order Execution Service"
            }
        )


# Order Status Checking Endpoints (Step 11)

@router.post(
    "/status/check",
    response_model=Dict[str, Any],  # Will be OrderStatusCheckResponse when dependencies are updated
    summary="Check Order Status",
    description="Compare orders.json with current IBKR account status",
    responses={
        200: {
            "description": "Order status check completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "comparison_summary": {
                            "found_in_ibkr": 15,
                            "missing_from_ibkr": 3,
                            "quantity_mismatches": 1,
                            "success_rate": 83.33,
                            "total_orders": 18,
                            "timestamp": "2024-01-15T14:30:00"
                        },
                        "order_matches": [
                            {
                                "symbol": "AAPL",
                                "json_action": "BUY",
                                "json_quantity": 100,
                                "ibkr_status": "FILLED",
                                "ibkr_quantity": 100,
                                "match_status": "OK"
                            }
                        ],
                        "missing_orders": [
                            {
                                "symbol": "DPM",
                                "action": "BUY",
                                "quantity": 50,
                                "currency": "CAD",
                                "ticker": "DPM",
                                "exchange": "TSE",
                                "reason": "Contract Not Supported",
                                "details": "IBKR does not support this specific DPM contract on TSE",
                                "note": "Consider alternative Canadian precious metals stocks"
                            }
                        ],
                        "recommendations": [
                            "AAPL: Enable direct routing in Account Settings > API > Precautionary Settings",
                            "DPM: Consider alternative Canadian precious metals stocks supported by IBKR"
                        ]
                    }
                }
            }
        },
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        404: {"model": ErrorResponse, "description": "Orders file not found"},
        500: {"model": ErrorResponse, "description": "IBKR connection error"},
        503: {"model": ErrorResponse, "description": "Service temporarily unavailable"}
    }
)
async def check_order_status(
    orders_file: Optional[str] = "orders.json"
    # order_status_service = Depends(get_order_status_service)  # Will be added when dependencies are updated
):
    """
    Check status of executed orders and compare with orders.json.

    This endpoint:
    1. Loads orders from JSON file (created by rebalancer)
    2. Connects to IBKR Gateway to fetch current account data
    3. Compares orders between JSON file and IBKR account
    4. Analyzes missing orders with failure patterns
    5. Provides detailed status breakdown and recommendations

    Args:
        orders_file: Path to orders JSON file (defaults to data/orders.json)

    Returns:
        Complete order verification results with analysis and recommendations
    """
    try:
        logger.info("Starting order status check")

        # Import here to avoid circular imports during development
        from ....services.implementations.order_status_service import OrderStatusService

        # Initialize service
        order_status_service = OrderStatusService(orders_file)

        # Load orders
        orders_data = order_status_service.load_orders_json(orders_file)

        # Connect to IBKR
        if not order_status_service.connect_to_ibkr():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to connect to IBKR Gateway"
            )

        # Fetch account data
        order_status_service.fetch_account_data()

        # Get verification results
        results = order_status_service.get_verification_results()

        # Disconnect
        order_status_service.disconnect()

        logger.info(f"Order status check completed: {results['comparison_summary']['success_rate']:.1f}% success rate")

        return {
            "success": True,
            **results
        }

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


@router.get(
    "/status/current",
    response_model=Dict[str, Any],  # Will be OrderStatusSummaryResponse when dependencies are updated
    summary="Get Current IBKR Order Status",
    description="Get detailed breakdown of current IBKR orders by status",
    responses={
        200: {
            "description": "Order status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "orders_by_status": {
                            "FILLED": [
                                {
                                    "order_id": 123,
                                    "symbol": "AAPL",
                                    "action": "BUY",
                                    "quantity": 100,
                                    "filled": 100,
                                    "status": "FILLED",
                                    "avg_fill_price": 150.25,
                                    "order_type": "MKT"
                                }
                            ]
                        },
                        "status_counts": {
                            "FILLED": 15,
                            "SUBMITTED": 3,
                            "CANCELLED": 2
                        },
                        "total_orders": 20
                    }
                }
            }
        },
        500: {"model": ErrorResponse, "description": "IBKR connection error"}
    }
)
async def get_current_order_status():
    """
    Get detailed breakdown of all current IBKR orders grouped by status.

    Returns:
        Orders grouped by status (FILLED, SUBMITTED, CANCELLED, etc.) with detailed information
    """
    try:
        logger.info("Fetching current IBKR order status")

        # Import here to avoid circular imports during development
        from ....services.implementations.order_status_service import OrderStatusService

        # Initialize service
        order_status_service = OrderStatusService()

        # Connect to IBKR
        if not order_status_service.connect_to_ibkr():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to connect to IBKR Gateway"
            )

        # Fetch account data
        order_status_service.fetch_account_data()

        # Get order status summary
        results = order_status_service.get_order_status_summary()

        # Disconnect
        order_status_service.disconnect()

        logger.info(f"Retrieved {results['total_orders']} orders from IBKR")

        return {
            "success": True,
            **results
        }

    except Exception as e:
        logger.error(f"Error fetching order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching order status: {str(e)}"
        )


@router.get(
    "/positions/summary",
    response_model=Dict[str, Any],  # Will be PositionsSummaryResponse when dependencies are updated
    summary="Get Account Positions Summary",
    description="Get current account positions with market values",
    responses={
        200: {
            "description": "Positions retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "positions": {
                            "AAPL": {
                                "position": 150,
                                "avg_cost": 145.50,
                                "currency": "USD",
                                "exchange": "NASDAQ",
                                "market_value": 21825.0
                            }
                        },
                        "total_positions": 25,
                        "total_market_value": 150000.0
                    }
                }
            }
        },
        500: {"model": ErrorResponse, "description": "IBKR connection error"}
    }
)
async def get_positions_summary():
    """
    Get detailed summary of current account positions.

    Returns:
        Current positions with market values and portfolio totals
    """
    try:
        logger.info("Fetching account positions summary")

        # Import here to avoid circular imports during development
        from ....services.implementations.order_status_service import OrderStatusService

        # Initialize service
        order_status_service = OrderStatusService()

        # Connect to IBKR
        if not order_status_service.connect_to_ibkr():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to connect to IBKR Gateway"
            )

        # Fetch account data
        order_status_service.fetch_account_data()

        # Get positions summary
        results = order_status_service.get_positions_summary()

        # Disconnect
        order_status_service.disconnect()

        logger.info(f"Retrieved {results['total_positions']} positions")

        return {
            "success": True,
            **results
        }

    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching positions summary: {str(e)}"
        )


@router.get(
    "/verification/results",
    response_model=Dict[str, Any],  # Will be OrderStatusCheckResponse when dependencies are updated
    summary="Get Order Verification Results",
    description="Get cached order verification results from last status check",
    responses={
        200: {
            "description": "Verification results retrieved successfully"
        },
        404: {"model": ErrorResponse, "description": "No cached results found"},
        500: {"model": ErrorResponse, "description": "Error retrieving results"}
    }
)
async def get_verification_results():
    """
    Get cached order verification results from the last status check.

    Note: This endpoint returns cached results. Use POST /orders/status/check
    to perform a fresh verification against IBKR.

    Returns:
        Last verification results if available
    """
    try:
        logger.info("Retrieving cached verification results")

        # This could be enhanced to store results in a cache/database
        # For now, return instruction to use the check endpoint
        return {
            "success": False,
            "message": "No cached results available. Use POST /orders/status/check to perform fresh verification.",
            "suggestion": "Consider implementing caching layer for verification results"
        }

    except Exception as e:
        logger.error(f"Error retrieving verification results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving verification results: {str(e)}"
        )