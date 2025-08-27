"""
Main entry point for the Real Estate Search application.
Works with pre-indexed data from data_pipeline.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from real_estate_search.config import AppConfig
from real_estate_search.container import DependencyContainer
from real_estate_search.search.models import SearchRequest, SearchResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_logging(log_level: str) -> None:
    """Configure logging based on the provided level."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    logging.getLogger().setLevel(numeric_level)


def run_search(container: DependencyContainer, query: str) -> SearchResponse:
    """
    Run a search query and display results.
    
    Args:
        container: Dependency container with all services
        query: Search query text
        
    Returns:
        SearchResponse with results
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


def validate_data_exists(container: DependencyContainer) -> bool:
    """
    Validate that required data exists in indices.
    
    Args:
        container: Dependency container with all services
        
    Returns:
        True if data exists, False otherwise
    """
    try:
        # Check if property index exists and has data
        if not container.property_repository.index_exists():
            logger.error(f"Property index '{container.config.elasticsearch.property_index}' does not exist")
            logger.info("Please run the data_pipeline first to index data")
            return False
        
        # Get document count
        count = container.property_repository.count()
        if count == 0:
            logger.error("Property index exists but contains no documents")
            logger.info("Please run the data_pipeline to index property data")
            return False
        
        logger.info(f"Found {count} properties in index")
        return True
        
    except Exception as e:
        logger.error(f"Error checking data: {e}")
        return False


def run_demo(container: DependencyContainer) -> None:
    """
    Run demo searches on pre-indexed data.
    
    Args:
        container: Dependency container with all services
    """
    logger.info("Running Real Estate Search Demo")
    logger.info("=" * 50)
    
    # Step 1: Validate data exists
    logger.info("\nStep 1: Validating pre-indexed data")
    if not validate_data_exists(container):
        logger.error("Demo cannot run without data. Please run data_pipeline first.")
        sys.exit(1)
    
    # Step 2: Demo searches
    logger.info("\nStep 2: Running demo searches")
    
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


def main() -> None:
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="Real Estate Search Application - Works with pre-indexed data from data_pipeline"
    )
    
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
        choices=["search", "demo"],
        default="demo",
        help="Operation mode: search or demo"
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
        
        # Create dependency container
        logger.info("Initializing dependency container")
        container = DependencyContainer(config)
        
        # Execute based on mode
        if args.mode == "search":
            if not args.query:
                logger.error("Query is required for search mode")
                sys.exit(1)
            
            # Validate data exists before searching
            if not validate_data_exists(container):
                logger.error("Cannot search without data. Please run data_pipeline first.")
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