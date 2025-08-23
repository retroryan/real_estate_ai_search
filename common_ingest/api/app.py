"""
FastAPI application instance and configuration.

This module creates and configures the FastAPI application with all routers,
middleware, and dependency injection setup.
"""

import time
import uuid
import sqlite3
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any
from pathlib import Path

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..utils.config import get_settings
from ..utils.logger import setup_logger
from .middleware import LoggingMiddleware, ErrorHandlingMiddleware
from .routers import properties, wikipedia, stats

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
    
    app.include_router(
        wikipedia.router,
        prefix="/api/v1/wikipedia",
        tags=["Wikipedia"]
    )
    
    app.include_router(
        stats.router,
        prefix="/api/v1/stats",
        tags=["Statistics"]
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
    
    def _check_file_health(file_path: Path, name: str) -> Dict[str, Any]:
        """Check if a file exists and is readable."""
        try:
            if not file_path.exists():
                return {
                    "status": "unhealthy",
                    "message": f"{name} file does not exist",
                    "path": str(file_path)
                }
            
            if not file_path.is_file():
                return {
                    "status": "unhealthy", 
                    "message": f"{name} path is not a file",
                    "path": str(file_path)
                }
            
            # Try to read the file
            with open(file_path, 'rb') as f:
                f.read(1)  # Try to read first byte
            
            return {
                "status": "healthy",
                "message": f"{name} file is accessible",
                "path": str(file_path),
                "size_mb": round(file_path.stat().st_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Error accessing {name} file: {str(e)}",
                "path": str(file_path)
            }
    
    def _check_database_health(db_path: Path, name: str) -> Dict[str, Any]:
        """Check if a SQLite database exists and is accessible."""
        try:
            if not db_path.exists():
                return {
                    "status": "unavailable",
                    "message": f"{name} database does not exist",
                    "path": str(db_path)
                }
            
            # Try to connect and run a simple query
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1;")
            cursor.fetchone()
            conn.close()
            
            return {
                "status": "healthy",
                "message": f"{name} database is accessible",
                "path": str(db_path),
                "size_mb": round(db_path.stat().st_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Error connecting to {name} database: {str(e)}",
                "path": str(db_path)
            }
    
    def _check_directory_health(dir_path: Path, name: str) -> Dict[str, Any]:
        """Check if a directory exists and contains expected files."""
        try:
            if not dir_path.exists():
                return {
                    "status": "unhealthy",
                    "message": f"{name} directory does not exist",
                    "path": str(dir_path)
                }
            
            if not dir_path.is_dir():
                return {
                    "status": "unhealthy",
                    "message": f"{name} path is not a directory", 
                    "path": str(dir_path)
                }
            
            # Count JSON files in the directory
            json_files = list(dir_path.glob("*.json"))
            
            return {
                "status": "healthy",
                "message": f"{name} directory is accessible",
                "path": str(dir_path),
                "json_files_count": len(json_files)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Error accessing {name} directory: {str(e)}",
                "path": str(dir_path)
            }

    @app.get("/api/v1/health")
    async def health():
        """
        Enhanced health check endpoint with database connectivity and file availability.
        
        Checks the actual availability and accessibility of all data sources including
        property JSON files, Wikipedia database, and directory structures.
        
        Returns:
        - overall status (healthy/degraded/unhealthy)
        - component-level health status
        - basic system information
        """
        settings = get_settings()
        
        # Check all data sources
        property_dir_health = _check_directory_health(
            settings.data_paths.get_property_data_path(),
            "Property data directory"
        )
        
        wikipedia_db_health = _check_database_health(
            settings.data_paths.get_wikipedia_db_path(),
            "Wikipedia database"
        )
        
        # Determine overall status
        components = {
            "property_data_directory": property_dir_health,
            "wikipedia_database": wikipedia_db_health
        }
        
        # Calculate overall health
        healthy_components = sum(1 for comp in components.values() if comp["status"] == "healthy")
        unavailable_components = sum(1 for comp in components.values() if comp["status"] == "unavailable")
        total_components = len(components)
        
        if healthy_components == total_components:
            overall_status = "healthy"
        elif unavailable_components > 0 and healthy_components > 0:
            overall_status = "degraded"  # Some services unavailable but core functionality works
        else:
            overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "version": settings.metadata.version,
            "timestamp": time.time(),
            "components": components,
            "summary": {
                "healthy_components": healthy_components,
                "total_components": total_components,
                "api_server": "running"
            }
        }
    
    return app


# Create the application instance
app = create_app()