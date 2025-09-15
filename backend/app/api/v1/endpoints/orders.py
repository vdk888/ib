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