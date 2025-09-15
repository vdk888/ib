"""
Custom exception classes for the application
"""
from typing import Optional, Dict, Any

class BaseServiceError(Exception):
    """Base exception for all service errors"""
    def __init__(self, message: str, error_code: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class ExternalAPIError(BaseServiceError):
    """Base for external API errors"""
    pass

class UncleStockAPIError(ExternalAPIError):
    """Uncle Stock API specific errors"""
    pass

class UncleStockTimeoutError(UncleStockAPIError):
    """Raised when Uncle Stock API times out"""
    def __init__(self, message: str = "Uncle Stock API request timed out", **kwargs):
        super().__init__(message, "UNCLE_STOCK_TIMEOUT", **kwargs)

class UncleStockRateLimitError(UncleStockAPIError):
    """Raised when Uncle Stock API rate limit exceeded"""
    def __init__(self, message: str = "Uncle Stock API rate limit exceeded", **kwargs):
        super().__init__(message, "UNCLE_STOCK_RATE_LIMIT", **kwargs)

class UncleStockInvalidQueryError(UncleStockAPIError):
    """Raised when query name is invalid or not found"""
    def __init__(self, message: str = "Invalid or missing query name", **kwargs):
        super().__init__(message, "UNCLE_STOCK_INVALID_QUERY", **kwargs)

class FileOperationError(BaseServiceError):
    """File system operation errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, "FILE_OPERATION_ERROR", **kwargs)

class IBKRError(ExternalAPIError):
    """IBKR API specific errors"""
    pass

class IBKRConnectionError(IBKRError):
    """IBKR connection specific errors"""
    pass

class OrderExecutionError(BaseServiceError):
    """Order execution specific errors"""
    pass

class ValidationError(BaseServiceError):
    """Data validation errors"""
    pass

class ConfigurationError(BaseServiceError):
    """Configuration and setup errors"""
    pass