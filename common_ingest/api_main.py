"""
Entry point for the Common Ingest FastAPI server.

Run this module to start the API server. This is separate from __main__.py
which is used for data loading testing.

Usage:
    python common_ingest/api_main.py
    
    Or with uvicorn:
    uvicorn common_ingest.api_main:app --reload --host 0.0.0.0 --port 8000
"""

import sys
import uvicorn
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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
    logger.info(f"API Documentation: http://localhost:8000/docs")
    logger.info(f"Health Check: http://localhost:8000/api/v1/health")
    
    # Configure uvicorn for development/demo
    uvicorn.run(
        "common_ingest.api_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.logging.level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()