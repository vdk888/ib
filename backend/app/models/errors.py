"""
Error response models
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retry_after: Optional[int] = None
    timestamp: str = datetime.utcnow().isoformat()
    request_id: Optional[str] = None

class ValidationErrorDetail(BaseModel):
    field: str
    message: str
    invalid_value: Any

class ValidationErrorResponse(ErrorResponse):
    validation_errors: List[ValidationErrorDetail]