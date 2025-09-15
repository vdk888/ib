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