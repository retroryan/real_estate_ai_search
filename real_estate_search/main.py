"""
Main entry point for the Real Estate Search demo application.
Uses dependency injection container for all operations.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List

from config.config import AppConfig
from container import DependencyContainer
from search.models import SearchRequest
from indexer.models import Property

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_logging(log_level: str):
    """Configure logging based on the provided level."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    logging.getLogger().setLevel(numeric_level)


def run_ingestion(container: DependencyContainer, force_recreate: bool = False):
    """
    Run the data ingestion pipeline.
    
    Args:
        container: Dependency container with all services
        force_recreate: If True, recreate indices before ingestion
    """
    logger.info("Starting data ingestion pipeline")
    
    # Run ingestion through orchestrator
    stats = container.ingestion_orchestrator.ingest_all(force_recreate=force_recreate)
    
    logger.info(f"Ingestion complete: {stats['indexed']} properties indexed, {stats['failed']} failed")
    
    return stats


def run_search(container: DependencyContainer, query: str):
    """
    Run a search query and display results.
    
    Args:
        container: Dependency container with all services
        query: Search query text
    """
    logger.info(f"Searching for: {query}")
    
    # Create search request
    request = SearchRequest(
        query_text=query,
        size=10,
        include_aggregations=False
    )
    
    # Execute search
    response = container.search_service.search(request)
    
    # Display results
    logger.info(f"Found {response.total} properties")
    
    for i, hit in enumerate(response.hits[:5], 1):
        prop = hit.property
        logger.info(
            f"{i}. {prop.address.street}, {prop.address.city}, {prop.address.state} - "
            f"${prop.price:,.0f} - {prop.bedrooms}bd/{prop.bathrooms}ba"
        )
        
        # Show enrichment if available
        if hit.raw_hit and 'location_context' in hit.raw_hit['_source']:
            context = hit.raw_hit['_source']['location_context']
            logger.info(f"   Location: {context.get('location_summary', '')[:100]}...")
    
    return response


def run_demo(container: DependencyContainer):
    """
    Run a full demo showing ingestion and search capabilities.
    
    Args:
        container: Dependency container with all services
    """
    logger.info("Running Real Estate Search Demo")
    logger.info("=" * 50)
    
    # Step 1: Create index
    logger.info("\nStep 1: Creating property index")
    container.indexing_service.create_index(force_recreate=True)
    
    # Step 2: Ingest data
    logger.info("\nStep 2: Ingesting properties with Wikipedia enrichment")
    stats = run_ingestion(container, force_recreate=False)
    
    # Step 3: Demo searches
    logger.info("\nStep 3: Running demo searches")
    
    demo_queries = [
        "ski resort properties",
        "family home near parks",
        "downtown condo with amenities",
        "historic neighborhood"
    ]
    
    for query in demo_queries:
        logger.info(f"\nSearching: '{query}'")
        response = run_search(container, query)
        logger.info(f"Found {response.total} matching properties")
    
    logger.info("\nDemo complete!")


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Real Estate Search Demo Application")
    
    # Configuration
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to configuration file"
    )
    
    # Operation mode
    parser.add_argument(
        "--mode",
        choices=["ingest", "search", "demo"],
        default="demo",
        help="Operation mode: ingest data, search, or run full demo"
    )
    
    # Ingestion options
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate indices before ingestion"
    )
    
    # Search options
    parser.add_argument(
        "--query",
        type=str,
        help="Search query (required for search mode)"
    )
    
    # Logging
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        config = AppConfig.from_yaml(args.config)
        
        # Override force_recreate if specified
        if args.recreate:
            config.force_recreate = True
        
        # Create dependency container
        logger.info("Initializing dependency container")
        container = DependencyContainer(config)
        
        # Execute based on mode
        if args.mode == "ingest":
            run_ingestion(container, force_recreate=args.recreate)
        
        elif args.mode == "search":
            if not args.query:
                logger.error("Query is required for search mode")
                sys.exit(1)
            run_search(container, args.query)
        
        elif args.mode == "demo":
            run_demo(container)
        
        else:
            logger.error(f"Unknown mode: {args.mode}")
            sys.exit(1)
            
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Application error: {e}")
        logger.debug("Full error details:", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()