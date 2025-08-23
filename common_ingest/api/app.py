"""
FastAPI application instance and configuration.

This module creates and configures the FastAPI application with all routers,
middleware, and dependency injection setup.
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..utils.config import get_settings
from ..utils.logger import setup_logger
from .middleware import LoggingMiddleware, ErrorHandlingMiddleware
from .routers import properties

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.
    
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    settings = get_settings()
    logger.info(f"Starting Common Ingest API v{settings.metadata.version}")
    logger.info(f"Configuration loaded from: common_ingest/config.yaml")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Common Ingest API")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.api.title,
        description=settings.api.description,
        version=settings.metadata.version,
        docs_url=settings.api.docs_url,
        redoc_url=settings.api.redoc_url,
        openapi_url=settings.api.openapi_url,
        debug=settings.api.debug,
        lifespan=lifespan
    )
    
    # Add CORS middleware using configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors.allow_origins,
        allow_credentials=settings.api.cors.allow_credentials,
        allow_methods=settings.api.cors.allow_methods,
        allow_headers=settings.api.cors.allow_headers,
    )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Add custom exception handler for HTTPException
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTPException with structured error response."""
        correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
        
        error_response = {
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "status_code": exc.status_code,
                "correlation_id": correlation_id
            }
        }
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
            headers={"X-Correlation-ID": correlation_id}
        )
    
    # Add custom exception handler for validation errors
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors with structured error response."""
        correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
        
        # Extract validation error details
        error_details = []
        for error in exc.errors():
            field_path = " -> ".join(str(x) for x in error["loc"])
            error_details.append(f"{field_path}: {error['msg']}")
        
        error_message = f"Validation failed: {'; '.join(error_details)}"
        
        error_response = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": error_message,
                "status_code": 422,
                "correlation_id": correlation_id,
                "validation_details": exc.errors()
            }
        }
        
        return JSONResponse(
            status_code=422,
            content=error_response,
            headers={"X-Correlation-ID": correlation_id}
        )
    
    # Include routers
    app.include_router(
        properties.router,
        prefix="/api/v1",
        tags=["Properties"]
    )
    
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "Common Ingest API",
            "version": settings.metadata.version,
            "description": settings.metadata.description,
            "docs_url": "/docs",
            "health_url": "/api/v1/health"
        }
    
    @app.get("/api/v1/health")
    async def health():
        """Health check endpoint."""
        settings = get_settings()
        return {
            "status": "healthy",
            "version": settings.metadata.version,
            "timestamp": time.time(),
            "data_sources": {
                "property_data": str(settings.data_paths.get_property_data_path()),
                "wikipedia_db": str(settings.data_paths.get_wikipedia_db_path())
            }
        }
    
    return app


# Create the application instance
app = create_app()