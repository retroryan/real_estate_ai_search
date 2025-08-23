"""
FastAPI application instance and configuration.

This module creates and configures the FastAPI application with all routers,
middleware, and dependency injection setup.
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

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
        title="Common Ingest API",
        description="REST API for loading and accessing enriched property and Wikipedia data",
        version=settings.metadata.version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    
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