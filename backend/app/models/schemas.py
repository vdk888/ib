"""
Pydantic models for request/response validation
Following fintech data validation standards
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ScreenerStatus(str, Enum):
    """Screener operation status"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class ScreenerDataResponse(BaseModel):
    """
    Response model for screener data fetching
    Matches legacy return structure for 100% compatibility
    """
    success: bool = Field(
        description="Whether the operation was successful"
    )
    data: Any = Field(
        description="Screener data (list of symbols for success, error message for failure)"
    )
    raw_response: Optional[str] = Field(
        description="Raw API response data",
        default=None
    )
    csv_file: Optional[str] = Field(
        description="Path to saved CSV file",
        default=None
    )
    screener_name: Optional[str] = Field(
        description="Human-readable screener name",
        default=None
    )
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when data was fetched"
    )
    symbol_count: Optional[int] = Field(
        description="Number of symbols returned (for successful responses)",
        default=None
    )

    @validator('symbol_count', always=True)
    def set_symbol_count(cls, v, values):
        """Auto-calculate symbol count for successful responses"""
        if values.get('success') and isinstance(values.get('data'), list):
            return len(values.get('data'))
        return v


class ScreenerHistoryResponse(BaseModel):
    """
    Response model for screener historical data
    Matches legacy return structure for 100% compatibility
    """
    success: bool = Field(
        description="Whether the operation was successful"
    )
    data: Any = Field(
        description="Historical data (dict for success, error message for failure)"
    )
    raw_response: Optional[str] = Field(
        description="Raw API response data",
        default=None
    )
    csv_file: Optional[str] = Field(
        description="Path to saved CSV file",
        default=None
    )
    screener_name: Optional[str] = Field(
        description="Human-readable screener name",
        default=None
    )
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when data was fetched"
    )


class AllScreenersResponse(BaseModel):
    """
    Response model for fetching all screener data
    """
    screeners: Dict[str, ScreenerDataResponse] = Field(
        description="Results for each screener, keyed by screener ID"
    )
    total_screeners: int = Field(
        description="Total number of screeners processed"
    )
    successful_screeners: int = Field(
        description="Number of screeners that returned data successfully"
    )
    total_symbols: int = Field(
        description="Total number of symbols across all screeners",
        default=0
    )
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when batch operation was completed"
    )

    @validator('total_symbols', always=True)
    def calculate_total_symbols(cls, v, values):
        """Auto-calculate total symbols across all screeners"""
        screeners = values.get('screeners', {})
        total = 0
        for screener_data in screeners.values():
            if screener_data.success and isinstance(screener_data.data, list):
                total += len(screener_data.data)
        return total

    @validator('successful_screeners', always=True)
    def calculate_successful_screeners(cls, v, values):
        """Auto-calculate number of successful screeners"""
        screeners = values.get('screeners', {})
        return sum(1 for s in screeners.values() if s.success)

    @validator('total_screeners', always=True)
    def calculate_total_screeners(cls, v, values):
        """Auto-calculate total number of screeners"""
        screeners = values.get('screeners', {})
        return len(screeners)


class AllScreenerHistoriesResponse(BaseModel):
    """
    Response model for fetching all screener histories
    """
    screeners: Dict[str, ScreenerHistoryResponse] = Field(
        description="History results for each screener, keyed by screener ID"
    )
    total_screeners: int = Field(
        description="Total number of screeners processed"
    )
    successful_screeners: int = Field(
        description="Number of screeners that returned history successfully"
    )
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when batch operation was completed"
    )

    @validator('successful_screeners', always=True)
    def calculate_successful_screeners(cls, v, values):
        """Auto-calculate number of successful screeners"""
        screeners = values.get('screeners', {})
        return sum(1 for s in screeners.values() if s.success)

    @validator('total_screeners', always=True)
    def calculate_total_screeners(cls, v, values):
        """Auto-calculate total number of screeners"""
        screeners = values.get('screeners', {})
        return len(screeners)


class AvailableScreenersResponse(BaseModel):
    """
    Response model for available screeners
    """
    screeners: Dict[str, str] = Field(
        description="Available screeners, mapping ID to display name"
    )
    total_count: int = Field(
        description="Total number of available screeners"
    )

    @validator('total_count', always=True)
    def calculate_total_count(cls, v, values):
        """Auto-calculate total count"""
        screeners = values.get('screeners', {})
        return len(screeners)


class ScreenerRequest(BaseModel):
    """
    Request model for individual screener operations
    """
    max_results: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum number of results to return"
    )


# Legacy compatibility models - exact structure match
class LegacyScreenerResponse(BaseModel):
    """
    Legacy response format for 100% backward compatibility
    This matches the exact dict structure from the original implementation
    """
    success: bool
    data: Any  # List[str] for success, str for error
    raw_response: Optional[str] = None
    csv_file: Optional[str] = None

    class Config:
        # Allow arbitrary field names for maximum compatibility
        extra = "allow"


# Universe-related models
class StockData(BaseModel):
    """
    Individual stock data model
    Matches the structure from parser.py
    """
    ticker: str = Field(description="Stock ticker symbol")
    isin: Optional[str] = Field(description="ISIN identifier", default=None)
    name: Optional[str] = Field(description="Company name", default=None)
    currency: Optional[str] = Field(description="Stock price currency", default=None)
    sector: Optional[str] = Field(description="Sector classification", default=None)
    country: Optional[str] = Field(description="Country of incorporation", default=None)
    price: Optional[float] = Field(description="Current stock price", default=None)
    screens: Optional[List[str]] = Field(description="Screens where this stock appears", default=None)

    class Config:
        # Allow additional fields for flexible parsing
        extra = "allow"


class ScreenInfo(BaseModel):
    """
    Screen information model
    """
    name: str = Field(description="Screen display name")
    count: int = Field(description="Number of stocks in this screen")
    stocks: List[StockData] = Field(description="List of stocks in this screen")


class UniverseMetadata(BaseModel):
    """
    Universe metadata model
    """
    screens: List[str] = Field(description="List of screen names")
    total_stocks: int = Field(description="Total stocks across all screens")
    unique_stocks: int = Field(description="Number of unique stocks")
    additional_fields_enabled: bool = Field(description="Whether additional fields are extracted")
    additional_fields: List[Dict[str, str]] = Field(description="Configuration of additional fields")


class UniverseResponse(BaseModel):
    """
    Complete universe response model
    Matches the structure from create_universe()
    """
    metadata: UniverseMetadata = Field(description="Universe metadata and statistics")
    screens: Dict[str, ScreenInfo] = Field(description="Data organized by screen")
    all_stocks: Dict[str, StockData] = Field(description="All unique stocks indexed by ticker")


class ParseUniverseRequest(BaseModel):
    """
    Request model for parsing universe
    """
    output_path: Optional[str] = Field(
        default="data/universe.json",
        description="Path where to save the universe.json file"
    )


class ParseUniverseResponse(BaseModel):
    """
    Response model for universe parsing operation
    """
    success: bool = Field(description="Whether parsing was successful")
    message: str = Field(description="Status message")
    universe_path: str = Field(description="Path to the created universe.json file")
    metadata: UniverseMetadata = Field(description="Universe metadata and statistics")
    processing_time: Optional[float] = Field(description="Time taken for processing", default=None)


class StockFieldRequest(BaseModel):
    """
    Request model for getting stock field data
    """
    header_name: str = Field(description="Header name to search for (e.g., 'Price')")
    subtitle_pattern: str = Field(description="Subtitle pattern to match (e.g., '180d change')")
    screen_name: Optional[str] = Field(description="Optional screen name to limit search", default=None)


class StockFieldResponse(BaseModel):
    """
    Response model for stock field data
    """
    ticker: str = Field(description="Stock ticker")
    field: str = Field(description="Field description")
    value: str = Field(description="Field value")
    screen: str = Field(description="Screen where the data was found")


class AvailableFieldsResponse(BaseModel):
    """
    Response model for available fields discovery
    """
    fields: List[Dict[str, Any]] = Field(description="Available field combinations")
    total_count: int = Field(description="Total number of available fields")
    csv_file: Optional[str] = Field(description="CSV file analyzed", default=None)

    @validator('total_count', always=True)
    def calculate_total_count(cls, v, values):
        """Auto-calculate total count"""
        fields = values.get('fields', [])
        return len(fields)


# Historical Data models for Step 3 API
class QuarterlyPerformance(BaseModel):
    """
    Quarterly performance data model
    Matches the structure from history_parser.py
    """
    quarter: str = Field(description="Quarter identifier (e.g., '2023 Q1')")
    return_: str = Field(alias="return", description="Quarterly return percentage")
    period_sd: str = Field(description="Period standard deviation")
    beta: str = Field(description="Beta coefficient")
    benchmark_return: Optional[str] = Field(description="Benchmark return percentage", default=None)


class BacktestMetadata(BaseModel):
    """
    Backtest metadata model
    Contains configuration and period information
    """
    begin: Optional[str] = Field(description="Backtest start date", default=None)
    end: Optional[str] = Field(description="Backtest end date", default=None)
    rebalance_timing: Optional[str] = Field(description="Rebalancing frequency", default=None)
    number_of_stocks: Optional[str] = Field(description="Number of stocks in portfolio", default=None)

    class Config:
        # Allow additional metadata fields
        extra = "allow"


class KeyStatistics(BaseModel):
    """
    Key performance statistics model
    """
    return_yearly: Optional[str] = Field(description="Yearly return percentage", default=None)
    period_sd_yearly: Optional[str] = Field(description="Yearly standard deviation", default=None)
    sharpe_ratio_yearly: Optional[str] = Field(description="Yearly Sharpe ratio", default=None)

    class Config:
        # Allow additional statistics fields
        extra = "allow"


class QuarterlySummary(BaseModel):
    """
    Quarterly summary statistics model
    """
    total_quarters: int = Field(description="Total number of quarters parsed")
    avg_quarterly_return: Optional[str] = Field(description="Average quarterly return", default=None)
    quarterly_std: Optional[str] = Field(description="Average quarterly standard deviation", default=None)


class ScreenPerformance(BaseModel):
    """
    Complete performance data for a single screener
    """
    screen_name: str = Field(description="Screener display name")
    backtest_metadata: BacktestMetadata = Field(description="Backtest configuration metadata")
    key_statistics: KeyStatistics = Field(description="Key performance statistics")
    quarterly_summary: QuarterlySummary = Field(description="Quarterly summary statistics")
    quarterly_data: List[QuarterlyPerformance] = Field(description="Complete quarterly performance data")


class HistoricalDataResponse(BaseModel):
    """
    Response model for individual screener backtest data
    """
    success: bool = Field(description="Whether the operation was successful")
    screener_id: str = Field(description="Screener identifier")
    data: Dict[str, Any] = Field(description="Parsed backtest data structure")
    metadata: Dict[str, Any] = Field(description="Operation metadata (quarters parsed, etc.)")


class BacktestDataResponse(BaseModel):
    """
    Response model for all screeners backtest data
    """
    success: bool = Field(description="Whether the operation was successful")
    data: Dict[str, Dict[str, Any]] = Field(description="Backtest data for all screeners")
    metadata: Dict[str, Any] = Field(description="Operation metadata (counts, etc.)")


class ScreenerSummary(BaseModel):
    """
    Performance summary for a single screener
    """
    screen_name: str = Field(description="Screener display name")
    status: str = Field(description="Parsing status (success/error)")
    error: Optional[str] = Field(description="Error message if parsing failed", default=None)
    backtest_period: Optional[Dict[str, str]] = Field(description="Backtest date range", default=None)
    rebalance_timing: Optional[str] = Field(description="Rebalancing frequency", default=None)
    number_of_stocks: Optional[str] = Field(description="Number of stocks", default=None)
    key_statistics: Optional[Dict[str, str]] = Field(description="Key performance metrics", default=None)
    quarterly_summary: Optional[Dict[str, Any]] = Field(description="Quarterly summary", default=None)


class PerformanceSummaryData(BaseModel):
    """
    Complete performance summary data
    """
    title: str = Field(description="Summary title")
    screeners: Dict[str, ScreenerSummary] = Field(description="Performance data by screener")


class PerformanceSummaryResponse(BaseModel):
    """
    Response model for performance summary
    """
    success: bool = Field(description="Whether the operation was successful")
    summary: PerformanceSummaryData = Field(description="Formatted performance summary")
    metadata: Dict[str, Any] = Field(description="Summary generation metadata")


class UpdateUniverseResponse(BaseModel):
    """
    Response model for universe update operation
    """
    success: bool = Field(description="Whether the update was successful")
    message: str = Field(description="Operation status message")
    metadata: Dict[str, Any] = Field(description="Update operation metadata")


# Portfolio Optimization Schemas

class PortfolioStats(BaseModel):
    """Portfolio performance statistics"""
    expected_annual_return: float = Field(description="Expected annual return (decimal, e.g., 0.12 = 12%)")
    annual_volatility: float = Field(description="Annual volatility (decimal)")
    sharpe_ratio: float = Field(description="Sharpe ratio")


class ScreenerStats(BaseModel):
    """Individual screener performance statistics"""
    annual_return: float = Field(description="Annual return (decimal)")
    annual_volatility: float = Field(description="Annual volatility (decimal)")
    sharpe_ratio: float = Field(description="Sharpe ratio")


class OptimizationDetails(BaseModel):
    """Portfolio optimization technical details"""
    success: bool = Field(description="Whether optimization was successful")
    message: str = Field(description="Optimization status message")
    method: str = Field(description="Optimization method used")
    objective: str = Field(description="Optimization objective")
    constraints: str = Field(description="Optimization constraints")


class PortfolioOptimizationData(BaseModel):
    """Complete portfolio optimization results"""
    optimal_allocations: Dict[str, float] = Field(description="Optimal portfolio weights by screener")
    portfolio_performance: PortfolioStats = Field(description="Optimized portfolio performance")
    individual_screener_stats: Dict[str, ScreenerStats] = Field(description="Individual screener statistics")
    correlation_matrix: Dict[str, Dict[str, float]] = Field(description="Screener correlation matrix")
    optimization_details: OptimizationDetails = Field(description="Optimization technical details")


class PortfolioOptimizationResponse(BaseModel):
    """
    Response model for portfolio optimization
    Maintains compatibility with CLI output
    """
    success: bool = Field(description="Whether the optimization was successful")
    optimization_results: PortfolioOptimizationData = Field(description="Complete optimization results")
    universe_updated: bool = Field(description="Whether universe.json was updated")
    message: str = Field(description="Operation status message")


class QuarterlyReturnsMetadata(BaseModel):
    """Metadata for quarterly returns data"""
    num_quarters: int = Field(description="Number of quarters in dataset")
    num_screeners: int = Field(description="Number of screeners with data")
    screeners: List[str] = Field(description="List of screener names")
    data_range: str = Field(description="Date range of quarterly data")


class QuarterlyReturnsResponse(BaseModel):
    """
    Response model for quarterly returns data
    Used as input for portfolio optimization
    """
    returns_data: Dict[str, List[float]] = Field(description="Quarterly returns by screener (decimal format)")
    quarters: List[str] = Field(description="Quarter labels (e.g., '2023Q1')")
    metadata: QuarterlyReturnsMetadata = Field(description="Dataset metadata")


# Target Allocation Service Schemas (Step 6)

class StockAllocationData(BaseModel):
    """
    Individual stock allocation data
    Matches the structure from calculate_final_allocations()
    """
    ticker: str = Field(description="Stock ticker symbol")
    screener: str = Field(description="Screener name where stock appears")
    rank: int = Field(description="Rank within screener (1 = best performing)")
    performance_180d: float = Field(description="180-day performance percentage (e.g., 12.45 for 12.45%)")
    pocket_allocation: float = Field(description="Allocation within screener (decimal, 0.0 to MAX_ALLOCATION)")
    screener_target: float = Field(description="Screener target allocation from optimizer (decimal)")
    final_allocation: float = Field(description="Final allocation = screener_target * pocket_allocation")


class AllocationSummaryStats(BaseModel):
    """
    Summary statistics for allocation results
    """
    total_stocks: int = Field(description="Total number of stocks processed")
    total_allocation_pct: float = Field(description="Total allocation percentage")
    stocks_with_allocation: int = Field(description="Number of stocks with non-zero allocation")


class Top10Allocation(BaseModel):
    """
    Top 10 allocation entry for quick reference
    """
    rank_overall: int = Field(description="Overall rank (1-10)")
    ticker: str = Field(description="Stock ticker symbol")
    final_allocation: float = Field(description="Final allocation percentage (decimal)")
    screener: str = Field(description="Screener name")
    screener_rank: int = Field(description="Rank within screener")
    performance_180d: float = Field(description="180-day performance percentage")


class AllocationSummaryData(BaseModel):
    """
    Complete allocation summary data (JSON equivalent of display_allocation_summary)
    """
    sorted_allocations: List[StockAllocationData] = Field(description="All allocations sorted by final_allocation desc")
    total_allocation: float = Field(description="Total allocation (decimal)")
    top_10_allocations: List[Top10Allocation] = Field(description="Top 10 allocations for quick reference")
    summary_stats: AllocationSummaryStats = Field(description="Summary statistics")


class TargetAllocationResponse(BaseModel):
    """
    Response model for target allocation calculation
    """
    success: bool = Field(description="Whether the calculation was successful")
    message: str = Field(description="Operation status message")
    allocation_data: Dict[str, StockAllocationData] = Field(description="Allocation data by ticker")
    universe_updated: bool = Field(description="Whether universe.json was updated with allocation data")


class AllocationSummaryResponse(BaseModel):
    """
    Response model for allocation summary data
    """
    success: bool = Field(description="Whether the operation was successful")
    summary: AllocationSummaryData = Field(description="Complete allocation summary")


class ScreenerAllocation(BaseModel):
    """
    Screener allocation from portfolio optimizer
    """
    screener_id: str = Field(description="Screener identifier")
    screener_name: str = Field(description="Screener display name")
    allocation: float = Field(description="Target allocation (decimal, e.g., 0.35 = 35%)")


class ScreenerAllocationsResponse(BaseModel):
    """
    Response model for screener allocations
    """
    success: bool = Field(description="Whether extraction was successful")
    screener_allocations: Dict[str, float] = Field(description="Screener allocations by ID")
    screeners_data: List[ScreenerAllocation] = Field(description="Detailed screener allocation data")


class StockRanking(BaseModel):
    """
    Individual stock ranking within screener
    """
    ticker: str = Field(description="Stock ticker symbol")
    rank: int = Field(description="Rank within screener (1 = best)")
    performance_180d: float = Field(description="180-day performance percentage")
    pocket_allocation: float = Field(description="Allocation within screener (decimal)")


class ScreenerRankingsResponse(BaseModel):
    """
    Response model for stock rankings within a screener
    """
    success: bool = Field(description="Whether ranking was successful")
    screener_id: str = Field(description="Screener identifier")
    screener_name: str = Field(description="Screener display name")
    rankings: List[StockRanking] = Field(description="Stock rankings sorted by performance")
    total_stocks: int = Field(description="Total stocks in screener")
    stocks_with_allocation: int = Field(description="Stocks receiving non-zero allocation")


class CalculateTargetsRequest(BaseModel):
    """
    Request model for calculating target allocations
    """
    force_recalculate: bool = Field(default=False, description="Force recalculation even if data exists")
    save_to_universe: bool = Field(default=True, description="Save results to universe.json")


class UniverseAllocationUpdate(BaseModel):
    """
    Model for universe update with allocation data
    """
    stocks_updated: int = Field(description="Number of stocks updated with allocation data")
    fields_added: List[str] = Field(description="Fields added to stock records")


class UniverseAllocationUpdateResponse(BaseModel):
    """
    Response model for universe allocation update
    """
    success: bool = Field(description="Whether the update was successful")
    message: str = Field(description="Update status message")
    update_details: UniverseAllocationUpdate = Field(description="Details of the update operation")


# ============================================================================
# Rebalancing and Orders Models
# ============================================================================

class OrderAction(str, Enum):
    """Order action enumeration"""
    BUY = "BUY"
    SELL = "SELL"


class StockInfo(BaseModel):
    """Stock information for order context"""
    ticker: str = Field(description="Original stock ticker")
    name: str = Field(description="Company name")
    currency: str = Field(description="Stock currency")
    screens: List[str] = Field(description="List of screens this stock appears in")


class IBKRDetails(BaseModel):
    """IBKR contract details for order execution"""
    symbol: str = Field(description="IBKR symbol for trading")
    exchange: str = Field(description="Trading exchange")
    primaryExchange: str = Field(description="Primary exchange")
    conId: Optional[int] = Field(description="IBKR contract ID", default=None)


class Order(BaseModel):
    """Individual rebalancing order"""
    symbol: str = Field(description="IBKR trading symbol")
    action: OrderAction = Field(description="BUY or SELL action")
    quantity: int = Field(description="Number of shares to trade", gt=0)
    current_quantity: int = Field(description="Current position quantity (can be negative for short positions)")
    target_quantity: int = Field(description="Target position quantity", ge=0)
    stock_info: StockInfo = Field(description="Stock information")
    ibkr_details: IBKRDetails = Field(description="IBKR contract details")

    @validator('quantity')
    def validate_quantity_logic(cls, v, values):
        """Validate order quantity matches the action logic"""
        if 'current_quantity' in values and 'target_quantity' in values:
            diff = values['target_quantity'] - values['current_quantity']
            expected_qty = abs(diff)
            if v != expected_qty:
                raise ValueError(f"Order quantity {v} doesn't match expected {expected_qty}")
        return v


class OrderMetadata(BaseModel):
    """Metadata for order generation"""
    generated_at: str = Field(description="Timestamp when orders were generated")
    total_orders: int = Field(description="Total number of orders", ge=0)
    buy_orders: int = Field(description="Number of BUY orders", ge=0)
    sell_orders: int = Field(description="Number of SELL orders", ge=0)
    total_buy_quantity: int = Field(description="Total shares to buy", ge=0)
    total_sell_quantity: int = Field(description="Total shares to sell", ge=0)

    @validator('total_orders')
    def validate_order_totals(cls, v, values):
        """Validate that order counts add up correctly"""
        if 'buy_orders' in values and 'sell_orders' in values:
            if v != values['buy_orders'] + values['sell_orders']:
                raise ValueError("Total orders must equal buy_orders + sell_orders")
        return v


class RebalancingResponse(BaseModel):
    """
    Response model for rebalancing order generation
    Complete response including orders, metadata, and analysis data
    """
    success: bool = Field(description="Whether the rebalancing was successful")
    orders: List[Order] = Field(description="List of generated orders")
    metadata: OrderMetadata = Field(description="Order generation metadata")
    target_quantities: Dict[str, int] = Field(description="Target quantities by symbol")
    current_positions: Dict[str, int] = Field(description="Current positions by symbol")
    message: str = Field(description="Rebalancing status message")


class OrdersResponse(BaseModel):
    """
    Response model for retrieving saved orders
    Simplified response for getting orders from file
    """
    success: bool = Field(description="Whether the retrieval was successful")
    orders: List[Order] = Field(description="List of orders from file")
    metadata: OrderMetadata = Field(description="Order metadata from file")


class PositionsResponse(BaseModel):
    """
    Response model for current IBKR positions
    """
    success: bool = Field(description="Whether position fetch was successful")
    positions: Dict[str, int] = Field(description="Current positions by symbol")
    contract_details: Dict[str, Dict[str, Any]] = Field(description="IBKR contract details by symbol")
    message: str = Field(description="Position fetch status message")


class TargetQuantitiesResponse(BaseModel):
    """
    Response model for target quantities calculation
    """
    success: bool = Field(description="Whether calculation was successful")
    target_quantities: Dict[str, int] = Field(description="Target quantities by symbol")
    total_symbols: int = Field(description="Total number of symbols with targets", ge=0)
    total_shares: int = Field(description="Total target shares across all symbols", ge=0)


# ============================================================================
# Order Execution Models
# ============================================================================

class OrderType(str, Enum):
    """Supported IBKR order types"""
    MKT = "MKT"              # Market order
    GTC_MKT = "GTC_MKT"      # Good Till Cancelled Market order (default)
    MOO = "MOO"              # Market on Open order
    DAY = "DAY"              # Day order


class OrderExecutionRequest(BaseModel):
    """
    Request model for order execution
    """
    orders_file: str = Field(
        default="orders.json",
        description="Orders JSON filename in data directory"
    )
    max_orders: Optional[int] = Field(
        default=None,
        description="Limit execution to first N orders (None for all)",
        ge=1
    )
    delay_between_orders: float = Field(
        default=1.0,
        description="Delay in seconds between order submissions",
        ge=0.1,
        le=10.0
    )
    order_type: OrderType = Field(
        default=OrderType.GTC_MKT,
        description="IBKR order type for all orders"
    )

    @validator('orders_file')
    def validate_orders_file(cls, v):
        if not v.endswith('.json'):
            v = f"{v}.json"
        return v


class IBKRConnectionRequest(BaseModel):
    """
    Request model for IBKR connection
    """
    host: str = Field(
        default="127.0.0.1",
        description="IBKR Gateway/TWS host"
    )
    port: int = Field(
        default=4002,
        description="IBKR Gateway/TWS port (4002 for paper trading, 4001 for live)",
        ge=1000,
        le=65535
    )
    client_id: int = Field(
        default=20,
        description="Client ID for API connection",
        ge=1,
        le=999
    )
    timeout: int = Field(
        default=15,
        description="Connection timeout in seconds",
        ge=5,
        le=60
    )


class OrderStatusSummary(BaseModel):
    """
    Summary of order statuses
    """
    status: str = Field(description="Order status (Filled, PreSubmitted, Submitted, etc.)")
    count: int = Field(description="Number of orders with this status", ge=0)


class OrderDetails(BaseModel):
    """
    Detailed order information
    """
    order_id: int = Field(description="IBKR order ID")
    status: str = Field(description="Current order status")
    filled: int = Field(description="Number of shares filled", ge=0)
    remaining: int = Field(description="Number of shares remaining", ge=0)
    avg_fill_price: float = Field(description="Average fill price", ge=0.0)
    perm_id: Optional[int] = Field(description="IBKR permanent ID")
    symbol: Optional[str] = Field(description="Stock symbol")
    action: Optional[str] = Field(description="Order action (BUY/SELL)")
    quantity: Optional[int] = Field(description="Order quantity")
    order_type: Optional[str] = Field(description="Order type used")
    submission_time: Optional[str] = Field(description="Order submission timestamp")


class OrderExecutionSummary(BaseModel):
    """
    Summary of order execution results
    """
    total_processed: int = Field(description="Total orders processed", ge=0)
    successful_submissions: int = Field(description="Successfully submitted orders", ge=0)
    failed_submissions: int = Field(description="Failed order submissions", ge=0)
    success_rate: float = Field(description="Success rate (0.0-1.0)", ge=0.0, le=1.0)


class OrderStatusResponse(BaseModel):
    """
    Response model for order status checking
    """
    success: bool = Field(description="Whether status check was successful")
    status_summary: Dict[str, int] = Field(description="Count of orders by status")
    total_filled_shares: int = Field(description="Total shares filled across all orders", ge=0)
    pending_orders_count: int = Field(description="Number of orders still pending", ge=0)
    order_details: Dict[str, OrderDetails] = Field(description="Detailed order information by order ID")
    wait_time_used: int = Field(description="Wait time used in seconds", ge=0)
    checked_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when status was checked"
    )


class OrderExecutionResponse(BaseModel):
    """
    Response model for order execution
    """
    success: bool = Field(description="Whether order execution was successful")
    executed_count: int = Field(description="Number of orders successfully submitted", ge=0)
    failed_count: int = Field(description="Number of orders that failed to submit", ge=0)
    total_orders: int = Field(description="Total orders processed", ge=0)
    order_statuses: Dict[str, Dict[str, Any]] = Field(description="Order statuses by order ID")
    order_results: List[OrderDetails] = Field(description="List of order execution results")
    execution_summary: OrderExecutionSummary = Field(description="Summary of execution results")
    executed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when execution completed"
    )


class OrderExecutionWorkflowResponse(BaseModel):
    """
    Response model for complete order execution workflow
    """
    success: bool = Field(description="Whether the entire workflow was successful")
    execution_summary: Optional[OrderExecutionSummary] = Field(default=None, description="Execution summary if successful")
    order_statuses: Optional[Dict[str, Dict[str, Any]]] = Field(default=None, description="Final order statuses")
    status_summary: Optional[Dict[str, int]] = Field(default=None, description="Status summary counts")
    total_filled_shares: Optional[int] = Field(default=None, description="Total shares filled")
    pending_orders_count: Optional[int] = Field(default=None, description="Pending orders count")
    orders_loaded: Optional[int] = Field(default=None, description="Number of orders loaded from file")
    error_message: Optional[str] = Field(default=None, description="Error message if workflow failed")
    workflow_completed_at: Optional[str] = Field(default=None, description="Workflow completion timestamp")
    failure_time: Optional[str] = Field(default=None, description="Failure timestamp if applicable")


class LoadOrdersResponse(BaseModel):
    """
    Response model for loading orders from file
    """
    success: bool = Field(description="Whether orders were loaded successfully")
    metadata: Optional[Dict[str, Any]] = Field(description="Order metadata (totals, counts)")
    orders: Optional[List[Dict[str, Any]]] = Field(description="List of orders")
    total_orders: Optional[int] = Field(description="Total number of orders loaded", ge=0)
    orders_file: str = Field(description="Orders file used")
    loaded_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when orders were loaded"
    )


class IBKRConnectionResponse(BaseModel):
    """
    Response model for IBKR connection
    """
    success: bool = Field(description="Whether connection was successful")
    account_id: Optional[str] = Field(description="IBKR account ID if connected")
    next_order_id: Optional[int] = Field(description="Next valid order ID if connected")
    connection_details: Dict[str, Any] = Field(description="Connection parameters used")
    error_message: Optional[str] = Field(description="Error message if connection failed")
    connected_at: Optional[str] = Field(description="Connection timestamp if successful")


class ContractSpecification(BaseModel):
    """
    IBKR contract specification
    """
    symbol: str = Field(description="Stock symbol")
    sec_type: str = Field(description="Security type (STK for stocks)")
    exchange: str = Field(description="Exchange routing")
    primary_exchange: str = Field(description="Primary exchange")
    currency: str = Field(description="Contract currency")
    con_id: Optional[int] = Field(description="Contract ID for precise identification")


class OrderSpecification(BaseModel):
    """
    IBKR order specification
    """
    action: str = Field(description="Order action (BUY/SELL)")
    total_quantity: int = Field(description="Total quantity to trade", ge=1)
    order_type: str = Field(description="Order type (MKT, etc.)")
    tif: Optional[str] = Field(description="Time in Force")
    e_trade_only: bool = Field(description="Electronic trading only flag")
    firm_quote_only: bool = Field(description="Firm quote only flag")


# Order Status Checking Models

class OrderMatchStatus(str, Enum):
    """Order matching status"""
    OK = "OK"
    MISSING = "MISSING"
    QTY_DIFF = "QTY_DIFF"
    NOT_FOUND = "NOT_FOUND"


class OrderAnalysisRow(BaseModel):
    """Single row in order analysis table"""
    symbol: str = Field(description="Stock symbol")
    json_action: str = Field(description="Action from orders.json (BUY/SELL)")
    json_quantity: int = Field(description="Quantity from orders.json", ge=0)
    ibkr_status: Optional[str] = Field(description="IBKR order status or 'NOT_FOUND'")
    ibkr_quantity: Optional[int] = Field(description="IBKR order quantity or None", ge=0)
    match_status: OrderMatchStatus = Field(description="Match status between JSON and IBKR")


class OrderFailureAnalysis(BaseModel):
    """Detailed analysis of a missing order"""
    symbol: str = Field(description="Stock symbol")
    action: str = Field(description="Order action (BUY/SELL)")
    quantity: int = Field(description="Order quantity", ge=0)
    currency: str = Field(description="Stock currency")
    ticker: str = Field(description="Stock ticker")
    exchange: str = Field(description="Exchange")
    reason: str = Field(description="Failure reason category")
    details: str = Field(description="Detailed failure explanation")
    note: str = Field(description="Additional notes or suggestions")


class OrderStatusDetail(BaseModel):
    """Detailed order information"""
    order_id: int = Field(description="IBKR order ID")
    symbol: str = Field(description="Stock symbol")
    action: str = Field(description="Order action (BUY/SELL)")
    quantity: int = Field(description="Order quantity", ge=0)
    filled: int = Field(description="Filled quantity", ge=0)
    status: str = Field(description="Order status")
    avg_fill_price: Any = Field(description="Average fill price or N/A")
    order_type: str = Field(description="Order type")


class PositionDetail(BaseModel):
    """Current position information"""
    position: int = Field(description="Position size (+ long, - short)")
    avg_cost: float = Field(description="Average cost per share")
    currency: str = Field(description="Position currency")
    exchange: str = Field(description="Exchange")
    market_value: float = Field(description="Current market value")


class ComparisonSummary(BaseModel):
    """Summary of order comparison results"""
    found_in_ibkr: int = Field(description="Number of orders found in IBKR", ge=0)
    missing_from_ibkr: int = Field(description="Number of orders missing from IBKR", ge=0)
    quantity_mismatches: int = Field(description="Number of quantity mismatches", ge=0)
    success_rate: float = Field(description="Success rate percentage", ge=0, le=100)
    total_orders: int = Field(description="Total orders in JSON file", ge=0)
    timestamp: str = Field(description="Analysis timestamp")


class OrderStatusCheckResponse(BaseModel):
    """Complete order status check results"""
    comparison_summary: ComparisonSummary = Field(description="Comparison summary statistics")
    order_matches: List[OrderAnalysisRow] = Field(description="Detailed order comparison table")
    missing_orders: List[OrderFailureAnalysis] = Field(description="Missing orders with failure analysis")
    recommendations: List[str] = Field(description="Actionable recommendations")
    extra_orders: List[Dict[str, Any]] = Field(description="Extra orders in IBKR not in JSON")
    positions: Dict[str, PositionDetail] = Field(description="Current account positions")
    order_status_breakdown: Dict[str, List[OrderStatusDetail]] = Field(description="Orders grouped by status")


class OrderStatusRequest(BaseModel):
    """Request for order status checking"""
    orders_file: Optional[str] = Field(
        default="orders.json",
        description="Orders file to compare against (default: data/orders.json)"
    )


class PositionsSummaryResponse(BaseModel):
    """Response for positions summary"""
    positions: Dict[str, PositionDetail] = Field(description="Current account positions")
    total_positions: int = Field(description="Total number of positions", ge=0)
    market_values: Dict[str, float] = Field(description="Market value by symbol")
    total_market_value: float = Field(description="Total portfolio market value")


class OrderStatusSummaryResponse(BaseModel):
    """Response for order status summary"""
    orders_by_status: Dict[str, List[OrderStatusDetail]] = Field(description="Orders grouped by status")
    status_counts: Dict[str, int] = Field(description="Count of orders by status")
    total_orders: int = Field(description="Total number of orders", ge=0)
    order_details: List[OrderStatusDetail] = Field(description="All order details")


class MissingOrderAnalysisResponse(BaseModel):
    """Response for missing order analysis"""
    failure_analysis: List[OrderFailureAnalysis] = Field(description="Detailed failure analysis")
    recommendations: List[str] = Field(description="Actionable recommendations")
    failure_patterns: Dict[str, Dict[str, str]] = Field(description="Known failure patterns by symbol")


# Currency Exchange Service Schemas (Step 5)

class ExchangeRatesData(BaseModel):
    """
    Exchange rates data structure
    """
    rates: Dict[str, float] = Field(description="Currency codes mapped to EUR exchange rates")
    base_currency: str = Field(default="EUR", description="Base currency for rates")
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when rates were fetched"
    )
    currency_count: int = Field(description="Number of currencies fetched", ge=0)

    @validator('currency_count', always=True)
    def set_currency_count(cls, v, values):
        """Auto-calculate currency count from rates"""
        rates = values.get('rates', {})
        return len(rates)


class ExchangeRatesResponse(BaseModel):
    """
    Response model for exchange rate fetching
    Matches legacy behavior with API-friendly structure
    """
    success: bool = Field(description="Whether exchange rates were successfully fetched")
    exchange_rates: Optional[ExchangeRatesData] = Field(
        description="Exchange rate data if successful",
        default=None
    )
    error_message: Optional[str] = Field(
        description="Error message if fetching failed",
        default=None
    )
    api_endpoint: str = Field(
        default="https://api.exchangerate-api.com/v4/latest/EUR",
        description="External API endpoint used"
    )
    timeout_seconds: int = Field(
        default=10,
        description="API request timeout in seconds"
    )


class UniverseCurrenciesResponse(BaseModel):
    """
    Response model for currencies found in universe.json
    """
    success: bool = Field(description="Whether currencies were successfully extracted")
    currencies: List[str] = Field(
        description="List of unique currency codes found",
        default_factory=list
    )
    currency_count: int = Field(description="Number of unique currencies", ge=0)
    source_file: str = Field(
        default="data/universe.json",
        description="Source file path"
    )
    extracted_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when currencies were extracted"
    )

    @validator('currency_count', always=True)
    def set_currency_count(cls, v, values):
        """Auto-calculate currency count"""
        currencies = values.get('currencies', [])
        return len(currencies)


class UniverseUpdateStats(BaseModel):
    """
    Statistics for universe.json update operation
    """
    updated_stocks_screens: int = Field(description="Stocks updated in screens sections", ge=0)
    updated_stocks_all: int = Field(description="Stocks updated in all_stocks section", ge=0)
    total_updated: int = Field(description="Total stocks updated", ge=0)
    missing_rates: List[str] = Field(
        description="Currencies without exchange rates",
        default_factory=list
    )

    @validator('total_updated', always=True)
    def calculate_total(cls, v, values):
        """Auto-calculate total updated stocks"""
        screens = values.get('updated_stocks_screens', 0)
        all_stocks = values.get('updated_stocks_all', 0)
        return screens + all_stocks


class UniverseUpdateResponse(BaseModel):
    """
    Response model for universe.json update with exchange rates
    """
    success: bool = Field(description="Whether universe was successfully updated")
    update_stats: Optional[UniverseUpdateStats] = Field(
        description="Update statistics if successful",
        default=None
    )
    error_message: Optional[str] = Field(
        description="Error message if update failed",
        default=None
    )
    file_path: str = Field(
        default="data/universe.json",
        description="Universe file path"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when update was performed"
    )


class CurrencyUpdateWorkflowResponse(BaseModel):
    """
    Response model for complete currency update workflow
    Matches CLI behavior with structured API response
    """
    success: bool = Field(description="Whether entire workflow completed successfully")
    step1_currencies: Optional[UniverseCurrenciesResponse] = Field(
        description="Step 1: Currency extraction results",
        default=None
    )
    step2_exchange_rates: Optional[ExchangeRatesResponse] = Field(
        description="Step 2: Exchange rate fetching results",
        default=None
    )
    step3_universe_update: Optional[UniverseUpdateResponse] = Field(
        description="Step 3: Universe update results",
        default=None
    )
    workflow_message: str = Field(description="Overall workflow status message")
    error_step: Optional[str] = Field(
        description="Step where workflow failed (if applicable)",
        default=None
    )
    completed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when workflow completed"
    )


# ============================================================================
# Pipeline Orchestration Models (Step 12)
# ============================================================================

class PipelineExecutionStatus(str, Enum):
    """Pipeline execution status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NOT_FOUND = "not_found"


class PipelineStepStatus(str, Enum):
    """Individual step execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStepInfo(BaseModel):
    """Pipeline step information and metadata"""
    step_number: int = Field(description="Step number (1-11)", ge=1, le=11)
    step_name: str = Field(description="Human-readable step name")
    description: str = Field(description="Step description")
    aliases: List[str] = Field(description="CLI aliases for this step")
    dependencies: List[int] = Field(description="Step numbers this step depends on")
    creates_files: List[str] = Field(description="Files this step creates")
    modifies_files: List[str] = Field(description="Files this step modifies")


class AvailableStepsResponse(BaseModel):
    """Response model for available pipeline steps"""
    steps: Dict[int, PipelineStepInfo] = Field(description="Step information by step number")
    total_steps: int = Field(description="Total number of available steps")
    step_aliases: Dict[str, int] = Field(description="CLI aliases mapped to step numbers")

    @validator('total_steps', always=True)
    def set_total_steps(cls, v, values):
        """Auto-calculate total steps"""
        steps = values.get('steps', {})
        return len(steps)


class PipelineStepResult(BaseModel):
    """Individual step execution result"""
    step_number: int = Field(description="Step number executed", ge=1, le=11)
    step_name: str = Field(description="Human-readable step name")
    status: PipelineStepStatus = Field(description="Step execution status")
    success: bool = Field(description="Whether step completed successfully")
    execution_time: float = Field(description="Step execution time in seconds", ge=0)
    start_time: datetime = Field(description="Step start timestamp")
    end_time: Optional[datetime] = Field(description="Step completion timestamp", default=None)
    created_files: List[str] = Field(description="Files created by this step", default_factory=list)
    modified_files: List[str] = Field(description="Files modified by this step", default_factory=list)
    console_output: List[str] = Field(description="Console output lines from step", default_factory=list)
    error_message: Optional[str] = Field(description="Error message if step failed", default=None)
    error_traceback: Optional[str] = Field(description="Error traceback if step failed", default=None)


class PipelineLogEntry(BaseModel):
    """Structured pipeline log entry"""
    timestamp: datetime = Field(description="Log entry timestamp")
    execution_id: str = Field(description="Pipeline execution identifier")
    step_number: Optional[int] = Field(description="Step number (None for pipeline-level logs)", ge=1, le=11)
    level: str = Field(description="Log level (INFO, WARNING, ERROR)")
    message: str = Field(description="Log message")
    details: Optional[Dict[str, Any]] = Field(description="Additional log details", default=None)


class PipelineExecutionMetadata(BaseModel):
    """Pipeline execution metadata and configuration"""
    execution_id: str = Field(description="Unique execution identifier")
    execution_type: str = Field(description="Execution type (full_pipeline, individual_step, step_range)")
    started_by: Optional[str] = Field(description="User/system that started execution", default=None)
    start_time: datetime = Field(description="Execution start timestamp")
    end_time: Optional[datetime] = Field(description="Execution completion timestamp", default=None)
    estimated_duration: Optional[float] = Field(description="Estimated execution time in seconds", default=None)

    # Parameters for different execution types
    target_steps: Optional[List[int]] = Field(description="Target steps to execute", default=None)
    start_step: Optional[int] = Field(description="Start step for range execution", default=None)
    end_step: Optional[int] = Field(description="End step for range execution", default=None)
    single_step: Optional[int] = Field(description="Single step for individual execution", default=None)

    # Resume functionality
    is_resumed: bool = Field(description="Whether this is a resumed execution", default=False)
    original_execution_id: Optional[str] = Field(description="Original execution ID if resumed", default=None)
    resumed_from_step: Optional[int] = Field(description="Step number resumed from", default=None)


class PipelineExecutionStatus(BaseModel):
    """Real-time pipeline execution status"""
    execution_id: str = Field(description="Unique execution identifier")
    status: PipelineExecutionStatus = Field(description="Current execution status")
    current_step: Optional[int] = Field(description="Currently executing step number", ge=1, le=11)
    current_step_name: Optional[str] = Field(description="Currently executing step name")
    completed_steps: List[int] = Field(description="Successfully completed step numbers")
    failed_step: Optional[int] = Field(description="Step number that failed (None if no failure)")
    progress_percentage: float = Field(description="Execution progress (0-100)", ge=0, le=100)
    execution_time: float = Field(description="Current execution time in seconds", ge=0)
    estimated_remaining_time: Optional[float] = Field(description="Estimated remaining time in seconds")
    metadata: PipelineExecutionMetadata = Field(description="Execution metadata")


class PipelineExecutionResult(BaseModel):
    """Complete pipeline execution results"""
    execution_id: str = Field(description="Unique execution identifier")
    success: bool = Field(description="Overall pipeline success")
    status: PipelineExecutionStatus = Field(description="Final execution status")
    execution_time: float = Field(description="Total execution time in seconds", ge=0)
    completed_steps: List[int] = Field(description="Successfully completed step numbers")
    failed_step: Optional[int] = Field(description="Step number that failed (None if all successful)")
    step_results: Dict[int, PipelineStepResult] = Field(description="Detailed results for each step")
    created_files: Dict[int, List[str]] = Field(description="Files created by each step")
    metadata: PipelineExecutionMetadata = Field(description="Execution metadata")
    error_message: Optional[str] = Field(description="Error message if pipeline failed")


class PipelineFileInfo(BaseModel):
    """Information about files created/modified by pipeline"""
    file_path: str = Field(description="Absolute path to the file")
    file_size: int = Field(description="File size in bytes", ge=0)
    created_at: datetime = Field(description="File creation timestamp")
    modified_at: datetime = Field(description="File modification timestamp")
    created_by_step: int = Field(description="Step that created this file", ge=1, le=11)
    file_type: str = Field(description="File type (json, csv, etc.)")


class PipelineExecutionFiles(BaseModel):
    """File results from pipeline execution"""
    execution_id: str = Field(description="Execution identifier")
    created_files: Dict[int, List[str]] = Field(description="File paths created by each step")
    file_info: Dict[str, PipelineFileInfo] = Field(description="Detailed file information")
    total_files_created: int = Field(description="Total number of files created", ge=0)
    total_file_size: int = Field(description="Total size of all files in bytes", ge=0)

    @validator('total_files_created', always=True)
    def calculate_total_files(cls, v, values):
        """Auto-calculate total files created"""
        created_files = values.get('created_files', {})
        return sum(len(files) for files in created_files.values())

    @validator('total_file_size', always=True)
    def calculate_total_size(cls, v, values):
        """Auto-calculate total file size"""
        file_info = values.get('file_info', {})
        return sum(info.file_size for info in file_info.values())


class PipelineExecutionLogs(BaseModel):
    """Structured execution logs"""
    execution_id: str = Field(description="Execution identifier")
    logs: List[PipelineLogEntry] = Field(description="List of log entries in chronological order")
    step_logs: Optional[Dict[int, List[PipelineLogEntry]]] = Field(description="Logs grouped by step")
    total_log_entries: int = Field(description="Total number of log entries", ge=0)

    @validator('total_log_entries', always=True)
    def calculate_total_logs(cls, v, values):
        """Auto-calculate total log entries"""
        logs = values.get('logs', [])
        return len(logs)


class PipelineHistoryEntry(BaseModel):
    """Pipeline execution history entry"""
    execution_id: str = Field(description="Unique execution identifier")
    execution_type: str = Field(description="Type of execution")
    status: PipelineExecutionStatus = Field(description="Final execution status")
    success: bool = Field(description="Whether execution was successful")
    start_time: datetime = Field(description="Execution start timestamp")
    end_time: Optional[datetime] = Field(description="Execution end timestamp")
    execution_time: Optional[float] = Field(description="Total execution time in seconds")
    completed_steps: List[int] = Field(description="Successfully completed steps")
    failed_step: Optional[int] = Field(description="Failed step number")
    total_files_created: int = Field(description="Number of files created", ge=0)
    is_resumed: bool = Field(description="Whether this was a resumed execution")


class PipelineHistoryResponse(BaseModel):
    """Pipeline execution history response"""
    executions: List[PipelineHistoryEntry] = Field(description="List of execution history entries")
    total_executions: int = Field(description="Total executions in history", ge=0)
    filtered_count: int = Field(description="Number of executions matching filter", ge=0)
    status_filter: Optional[str] = Field(description="Status filter applied")

    @validator('total_executions', always=True)
    def calculate_total(cls, v, values):
        """Auto-calculate total executions"""
        executions = values.get('executions', [])
        return len(executions)


class PipelineDependencyCheck(BaseModel):
    """Individual dependency validation result"""
    name: str = Field(description="Dependency name")
    type: str = Field(description="Dependency type (file, service, configuration)")
    required: bool = Field(description="Whether this dependency is required")
    valid: bool = Field(description="Whether dependency is satisfied")
    details: str = Field(description="Dependency validation details")
    recommendation: Optional[str] = Field(description="Recommendation if invalid")


class PipelineDependencyValidation(BaseModel):
    """Complete pipeline dependency validation"""
    valid: bool = Field(description="Whether all dependencies are satisfied")
    checks: Dict[str, PipelineDependencyCheck] = Field(description="Individual dependency checks")
    missing_dependencies: List[str] = Field(description="List of missing dependency names")
    recommendations: List[str] = Field(description="List of recommendations to fix issues")
    checked_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when validation was performed"
    )


# Request models for pipeline operations

class PipelineExecutionRequest(BaseModel):
    """Request model for full pipeline execution"""
    execution_id: Optional[str] = Field(description="Optional execution ID (generated if not provided)")
    started_by: Optional[str] = Field(description="User identifier starting the execution")


class StepExecutionRequest(BaseModel):
    """Request model for individual step execution"""
    step_number: int = Field(description="Step number to execute (1-11)", ge=1, le=11)
    execution_id: Optional[str] = Field(description="Optional execution ID")
    started_by: Optional[str] = Field(description="User identifier starting the execution")


class StepRangeExecutionRequest(BaseModel):
    """Request model for step range execution"""
    start_step: int = Field(description="First step to execute (1-11)", ge=1, le=11)
    end_step: int = Field(description="Last step to execute (1-11)", ge=1, le=11)
    execution_id: Optional[str] = Field(description="Optional execution ID")
    started_by: Optional[str] = Field(description="User identifier starting the execution")

    @validator('end_step')
    def validate_step_range(cls, v, values):
        """Validate that end_step >= start_step"""
        if 'start_step' in values and v < values['start_step']:
            raise ValueError("end_step must be >= start_step")
        return v


class ResumeExecutionRequest(BaseModel):
    """Request model for resuming failed execution"""
    execution_id: str = Field(description="Original execution ID to resume")
    from_step: Optional[int] = Field(description="Step to resume from (auto-detect if None)", ge=1, le=11)
    started_by: Optional[str] = Field(description="User identifier resuming the execution")


class PipelineHistoryRequest(BaseModel):
    """Request model for pipeline execution history"""
    limit: int = Field(default=50, description="Maximum executions to return", ge=1, le=1000)
    status_filter: Optional[PipelineExecutionStatus] = Field(description="Filter by execution status")
    execution_type_filter: Optional[str] = Field(description="Filter by execution type")


class PipelineLogsRequest(BaseModel):
    """Request model for execution logs"""
    execution_id: str = Field(description="Execution identifier")
    step_number: Optional[int] = Field(description="Filter by step number", ge=1, le=11)
    level_filter: Optional[str] = Field(description="Filter by log level")
    limit: Optional[int] = Field(description="Limit number of log entries", ge=1, le=10000)


# Response models for pipeline API endpoints

class FullPipelineResponse(BaseModel):
    """Response for full pipeline execution"""
    execution_id: str = Field(description="Execution identifier")
    success: bool = Field(description="Whether pipeline started successfully")
    message: str = Field(description="Status message")
    estimated_duration: Optional[float] = Field(description="Estimated execution time")
    started_at: datetime = Field(default_factory=datetime.utcnow)


class IndividualStepResponse(BaseModel):
    """Response for individual step execution"""
    execution_id: str = Field(description="Execution identifier")
    step_number: int = Field(description="Step number executed")
    step_name: str = Field(description="Step name")
    success: bool = Field(description="Whether step completed successfully")
    execution_time: Optional[float] = Field(description="Step execution time")
    created_files: List[str] = Field(description="Files created by step")
    console_output: List[str] = Field(description="Console output from step")
    error_message: Optional[str] = Field(description="Error message if failed")


class StepRangeResponse(BaseModel):
    """Response for step range execution"""
    execution_id: str = Field(description="Execution identifier")
    start_step: int = Field(description="First step executed")
    end_step: int = Field(description="Last step attempted")
    success: bool = Field(description="Whether range execution completed successfully")
    completed_steps: List[int] = Field(description="Successfully completed steps")
    failed_step: Optional[int] = Field(description="Step that failed")
    execution_time: float = Field(description="Total execution time")
    step_results: Dict[int, PipelineStepResult] = Field(description="Results for each step")


class ResumeExecutionResponse(BaseModel):
    """Response for resume execution"""
    execution_id: str = Field(description="New execution identifier")
    original_execution_id: str = Field(description="Original failed execution ID")
    resumed_from_step: int = Field(description="Step number resumed from")
    success: bool = Field(description="Whether resume was successful")
    message: str = Field(description="Resume status message")

# IBKR Search API Models
# Exact replication of comprehensive_enhanced_search.py behavior

class StockSearchRequest(BaseModel):
    """Request model for individual stock search"""
    ticker: str = Field(description="Stock ticker symbol", min_length=1)
    isin: Optional[str] = Field(description="International Securities Identification Number")
    name: str = Field(description="Company name", min_length=1)
    currency: str = Field(description="Stock currency (EUR, USD, JPY, etc.)", min_length=3, max_length=3)
    sector: Optional[str] = Field(description="Business sector")
    country: Optional[str] = Field(description="Country of incorporation")

    @validator('currency')
    def validate_currency(cls, v):
        """Ensure currency is uppercase"""
        if v:
            return v.upper()
        return v


class IBKRContractDetails(BaseModel):
    """IBKR contract details response"""
    symbol: str = Field(description="IBKR symbol")
    longName: str = Field(description="Full company name from IBKR")
    currency: str = Field(description="Contract currency")
    exchange: str = Field(description="Exchange where contract is traded")
    primaryExchange: str = Field(description="Primary exchange", default="")
    conId: int = Field(description="IBKR contract ID", default=0)
    search_method: str = Field(description="Method used to find stock (isin, ticker, name)")
    match_score: float = Field(description="Name similarity score", ge=0.0, le=1.0)


class StockSearchResponse(BaseModel):
    """Response model for individual stock search"""
    success: bool = Field(description="Whether the search operation was successful")
    found: bool = Field(description="Whether the stock was found in IBKR")
    message: str = Field(description="Search result message")
    stock: StockSearchRequest = Field(description="Original stock search request")
    ibkr_details: Optional[IBKRContractDetails] = Field(
        description="IBKR contract details if found",
        default=None
    )


class IBKRSearchStats(BaseModel):
    """Statistics for IBKR search operations"""
    total: int = Field(description="Total stocks processed")
    found_isin: int = Field(description="Stocks found via ISIN search")
    found_ticker: int = Field(description="Stocks found via ticker search")
    found_name: int = Field(description="Stocks found via name search")
    not_found: int = Field(description="Stocks not found in IBKR")
    execution_time_seconds: float = Field(description="Total execution time")
    filtered_stocks: int = Field(description="Stocks filtered by quantity > 0", default=0)
    not_found_stocks: List[Dict[str, Any]] = Field(
        description="List of stocks not found with details",
        default=[]
    )

    @validator('execution_time_seconds')
    def validate_execution_time(cls, v):
        """Ensure execution time is positive"""
        if v < 0:
            raise ValueError('Execution time must be positive')
        return v


class UniverseSearchResponse(BaseModel):
    """Response model for universe search operation"""
    success: bool = Field(description="Whether the universe search was successful")
    message: str = Field(description="Search operation message")
    statistics: IBKRSearchStats = Field(description="Detailed search statistics")
    output_file: str = Field(description="Path to output file with results")

    @validator('output_file')
    def validate_output_file(cls, v):
        """Ensure output file path is provided"""
        if not v:
            raise ValueError('Output file path is required')
        return v
