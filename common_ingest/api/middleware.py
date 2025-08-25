"""
FastAPI middleware components for logging and error handling.

Provides request/response logging with correlation IDs and structured error handling.
"""

import time
import uuid
import traceback
from typing import Callable

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request and response logging with correlation IDs.
    
    Adds correlation ID to each request for tracking and logs request/response details.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and response with logging.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or endpoint
            
        Returns:
            Response: The HTTP response
        """
        # Generate correlation ID for request tracking
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Log request
        start_time = time.time()
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={"correlation_id": correlation_id}
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - "
                f"Status: {response.status_code} - Time: {process_time:.3f}s",
                extra={"correlation_id": correlation_id}
            )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} - "
                f"Error: {str(e)} - Time: {process_time:.3f}s",
                extra={"correlation_id": correlation_id}
            )
            raise


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured error handling and response formatting.
    
    Converts exceptions into structured JSON error responses with correlation IDs.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with error handling.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or endpoint
            
        Returns:
            Response: The HTTP response or error response
        """
        try:
            return await call_next(request)
            
        except HTTPException as e:
            # Handle FastAPI HTTP exceptions
            correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
            
            error_response = {
                "error": {
                    "code": f"HTTP_{e.status_code}",
                    "message": e.detail,
                    "status_code": e.status_code,
                    "correlation_id": correlation_id
                }
            }
            
            return JSONResponse(
                status_code=e.status_code,
                content=error_response,
                headers={"X-Correlation-ID": correlation_id}
            )
            
        except Exception as e:
            # Handle unexpected exceptions
            correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
            
            # Log the full traceback for debugging
            logger.error(
                f"Unexpected error in {request.method} {request.url.path}: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "traceback": traceback.format_exc()
                }
            )
            
            error_response = {
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred",
                    "status_code": 500,
                    "correlation_id": correlation_id
                }
            }
            
            return JSONResponse(
                status_code=500,
                content=error_response,
                headers={"X-Correlation-ID": correlation_id}
            )