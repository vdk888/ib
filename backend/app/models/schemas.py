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