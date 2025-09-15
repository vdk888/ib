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
    pass

class UncleStockRateLimitError(UncleStockAPIError):
    """Raised when Uncle Stock API rate limit exceeded"""
    pass

class IBKRError(ExternalAPIError):
    """IBKR API specific errors"""
    pass

class IBKRConnectionError(IBKRError):
    """IBKR connection specific errors"""
    pass

class ValidationError(BaseServiceError):
    """Data validation errors"""
    pass

class ConfigurationError(BaseServiceError):
    """Configuration and setup errors"""
    pass