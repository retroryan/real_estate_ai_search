#!/usr/bin/env python3
"""
Run the Property Search API server.
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

import uvicorn
import structlog
from real_estate_search.config.settings import Settings

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


def main():
    """Main entry point."""
    settings = Settings.load()
    
    logger.info(
        "Starting Property Search API",
        host="0.0.0.0",
        port=8000,
        elasticsearch=f"{settings.elasticsearch.host}:{settings.elasticsearch.port}"
    )
    
    uvicorn.run(
        "real_estate_search.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()