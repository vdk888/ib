"""
FastAPI application entry point
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import logging

from .core.config import settings
from .core.middleware import RequestLoggingMiddleware
from .core.exceptions import BaseServiceError
from .models.errors import ErrorResponse

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Uncle Stock Portfolio API",
    description="API for managing portfolio optimization, screening, and execution",
    version="1.0.0",
    debug=settings.debug
)

# Add middleware
app.add_middleware(RequestLoggingMiddleware)

# Include routers
from .api.v1.endpoints.screeners import router as screeners_router
from .api.v1.endpoints.historical import router as historical_router
from .api.v1.endpoints.universe import router as universe_router

app.include_router(screeners_router, prefix="/api/v1")
app.include_router(historical_router, prefix="/api/v1")
app.include_router(universe_router, prefix="/api/v1")

# Exception handlers
@app.exception_handler(BaseServiceError)
async def service_error_handler(request, exc: BaseServiceError):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            request_id=getattr(request.state, 'request_id', None)
        ).dict()
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=f"HTTP_{exc.status_code}",
            message=exc.detail,
            request_id=getattr(request.state, 'request_id', None)
        ).dict()
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Uncle Stock Portfolio API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_url": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)