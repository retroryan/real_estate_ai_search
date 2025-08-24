#!/usr/bin/env python
"""
Entry point for the Common Ingest FastAPI server (run from parent directory).

This script starts the Common Ingest API server that provides REST endpoints
for properties, neighborhoods, Wikipedia data, and statistics.

Usage:
    python common_ingest_api.py
    python -m common_ingest_api
    
    Or with uvicorn directly:
    uvicorn common_ingest_api:app --reload --host 0.0.0.0 --port 8001
"""

import sys
import uvicorn
from pathlib import Path

# Add project root to Python path to ensure imports work
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the API app and utilities
from common_ingest.api.app import app
from common_ingest.utils.logger import setup_logger
from common_ingest.utils.config import get_settings

logger = setup_logger(__name__)


def main():
    """
    Start the FastAPI server.
    
    This function configures and starts the uvicorn server with appropriate
    settings for development and demo purposes.
    """
    settings = get_settings()
    
    logger.info("Starting Common Ingest API server")
    logger.info(f"Server: http://{settings.api.host}:{settings.api.port}")
    logger.info(f"API Documentation: http://{settings.api.host}:{settings.api.port}{settings.api.docs_url}")
    logger.info(f"Health Check: http://{settings.api.host}:{settings.api.port}/api/v1/health")
    
    # Configure uvicorn using settings
    uvicorn.run(
        "common_ingest_api:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        log_level=settings.logging.level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()