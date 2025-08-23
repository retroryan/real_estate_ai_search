#!/usr/bin/env python
"""
Main script for processing real data with the common embeddings module.

This script loads and processes actual data from:
- real_estate_data/ directory for properties and neighborhoods
- data/wikipedia/ directory for Wikipedia articles

Usage:
    python -m common_embeddings.main --data-type real_estate
    python -m common_embeddings.main --data-type wikipedia  
    python -m common_embeddings.main --data-type all
"""

import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common_embeddings import (
    Config,
    EmbeddingPipeline,
    EntityType,
    SourceType,
)
from common_embeddings.utils import setup_logging, get_logger
from common_embeddings.utils.progress import create_progress_indicator
from common_embeddings.loaders import RealEstateLoader, WikipediaLoader
from common_embeddings.services import CollectionManager


# Data loading functions have been moved to loaders/ module


def process_real_estate_data(config: Config, force_recreate: bool = False):
    """Process real estate data from real_estate_data/ directory."""
    logger = get_logger(__name__)
    logger.info("Processing real estate data")
    
    # Load data using new loader
    data_dir = Path("real_estate_data")
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        return
    
    loader = RealEstateLoader(data_dir)
    if not loader.validate_source():
        logger.error("Invalid real estate data source")
        return
    
    property_docs, neighborhood_docs = loader.load_all()
    
    # Create pipeline
    pipeline = EmbeddingPipeline(config)
    
    # Process properties with progress indicator
    if property_docs:
        logger.info(f"Processing {len(property_docs)} properties...")
        progress = create_progress_indicator(
            total=len(property_docs),
            operation="Processing properties",
            show_console=True
        )
        
        property_count = 0
        for result in pipeline.process_documents(
            property_docs,
            EntityType.PROPERTY,
            SourceType.PROPERTY_JSON,
            "real_estate_data/properties.json"
        ):
            property_count += 1
            progress.update(current=property_count)
        
        progress.complete()
        logger.info(f"Completed processing {property_count} property embeddings")
    
    # Process neighborhoods with progress indicator
    if neighborhood_docs:
        logger.info(f"Processing {len(neighborhood_docs)} neighborhoods...")
        progress = create_progress_indicator(
            total=len(neighborhood_docs),
            operation="Processing neighborhoods",
            show_console=True
        )
        
        neighborhood_count = 0
        for result in pipeline.process_documents(
            neighborhood_docs,
            EntityType.NEIGHBORHOOD,
            SourceType.NEIGHBORHOOD_JSON,
            "real_estate_data/neighborhoods.json"
        ):
            neighborhood_count += 1
            progress.update(current=neighborhood_count)
        
        progress.complete()
        logger.info(f"Completed processing {neighborhood_count} neighborhood embeddings")
    
    # Store in separate collections by entity type
    logger.info("Setting up ChromaDB collections...")
    collection_manager = CollectionManager(config)
    
    # Create separate collections for properties and neighborhoods
    if property_docs:
        prop_collection = collection_manager.create_collection_for_entity(
            entity_type=EntityType.PROPERTY,
            model_identifier=pipeline.model_identifier,
            force_recreate=force_recreate,
            additional_metadata={"source": "real_estate_data", "data_type": "properties"}
        )
        logger.info(f"Created property collection: {prop_collection}")
    
    if neighborhood_docs:
        neighborhood_collection = collection_manager.create_collection_for_entity(
            entity_type=EntityType.NEIGHBORHOOD,
            model_identifier=pipeline.model_identifier,
            force_recreate=force_recreate,
            additional_metadata={"source": "real_estate_data", "data_type": "neighborhoods"}
        )
        logger.info(f"Created neighborhood collection: {neighborhood_collection}")
    
    # Get statistics (now returns PipelineStatistics Pydantic model)
    stats = pipeline.get_statistics()
    logger.info("Pipeline Statistics:")
    stats_dict = stats.model_dump()
    for key, value in stats_dict.items():
        logger.info(f"  {key}: {value}")


def process_wikipedia_data(config: Config, force_recreate: bool = False, max_articles: int = None):
    """Process Wikipedia data from data/wikipedia/ directory."""
    logger = get_logger(__name__)
    logger.info("Processing Wikipedia data")
    
    # Load data using new loader
    data_dir = Path("data")
    loader = WikipediaLoader(data_dir, max_articles)
    
    if not loader.validate_source():
        logger.warning("No Wikipedia data source found")
        return
    
    wikipedia_docs = loader.load_all()
    
    if not wikipedia_docs:
        logger.warning("No Wikipedia documents found to process")
        return
    
    # Create pipeline
    pipeline = EmbeddingPipeline(config)
    
    # Process Wikipedia articles with progress indicator
    logger.info(f"Processing {len(wikipedia_docs)} Wikipedia articles...")
    progress = create_progress_indicator(
        total=len(wikipedia_docs),
        operation="Processing Wikipedia articles",
        show_console=True
    )
    
    wiki_count = 0
    for result in pipeline.process_documents(
        wikipedia_docs,
        EntityType.WIKIPEDIA_ARTICLE,
        SourceType.WIKIPEDIA_HTML,
        "data/wikipedia/pages"
    ):
        wiki_count += 1
        progress.update(current=wiki_count)
    
    progress.complete()
    logger.info(f"Completed processing {wiki_count} Wikipedia embeddings")
    
    # Store in separate collection for Wikipedia articles
    logger.info("Setting up ChromaDB collection for Wikipedia...")
    collection_manager = CollectionManager(config)
    
    # Create collection for Wikipedia articles
    wiki_collection = collection_manager.create_collection_for_entity(
        entity_type=EntityType.WIKIPEDIA_ARTICLE,
        model_identifier=pipeline.model_identifier,
        force_recreate=force_recreate,
        additional_metadata={"source": "data/wikipedia", "data_type": "articles", "max_articles": max_articles}
    )
    logger.info(f"Created Wikipedia collection: {wiki_collection}")
    
    # Get statistics (now returns PipelineStatistics Pydantic model)
    stats = pipeline.get_statistics()
    logger.info("Pipeline Statistics:")
    stats_dict = stats.model_dump()
    for key, value in stats_dict.items():
        logger.info(f"  {key}: {value}")


def main():
    """Main entry point for processing real data."""
    parser = argparse.ArgumentParser(
        description="Process real data with common embeddings module"
    )
    parser.add_argument(
        "--data-type",
        choices=["real_estate", "wikipedia", "all"],
        default="all",
        help="Type of data to process"
    )
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Delete existing embeddings and recreate"
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=None,
        help="Maximum number of Wikipedia articles to process (for testing)"
    )
    parser.add_argument(
        "--config",
        default="common_embeddings/config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level=args.log_level)
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("Common Embeddings - Real Data Processing")
    logger.info("=" * 60)
    
    # Load configuration
    config = Config.from_yaml(args.config)
    logger.info(f"Loaded configuration: provider={config.embedding.provider}")
    
    # Process based on data type
    if args.data_type in ["real_estate", "all"]:
        logger.info("\n--- Processing Real Estate Data ---")
        process_real_estate_data(config, args.force_recreate)
    
    if args.data_type in ["wikipedia", "all"]:
        logger.info("\n--- Processing Wikipedia Data ---")
        process_wikipedia_data(config, args.force_recreate, args.max_articles)
    
    # Show collection summary
    logger.info("\n--- Collection Summary ---")
    collection_manager = CollectionManager(config)
    
    # Create a temporary pipeline to get model identifier
    temp_config = config
    temp_pipeline = EmbeddingPipeline(temp_config)
    model_id = temp_pipeline.model_identifier
    
    if args.data_type in ["real_estate", "all"]:
        prop_info = collection_manager.get_entity_collection_info(EntityType.PROPERTY, model_id)
        neighborhood_info = collection_manager.get_entity_collection_info(EntityType.NEIGHBORHOOD, model_id)
        logger.info(f"Property collection: {prop_info['collection_name']} ({prop_info['count']} embeddings)")
        logger.info(f"Neighborhood collection: {neighborhood_info['collection_name']} ({neighborhood_info['count']} embeddings)")
    
    if args.data_type in ["wikipedia", "all"]:
        wiki_info = collection_manager.get_entity_collection_info(EntityType.WIKIPEDIA_ARTICLE, model_id)
        logger.info(f"Wikipedia collection: {wiki_info['collection_name']} ({wiki_info['count']} embeddings)")
    
    logger.info("\n" + "=" * 60)
    logger.info("Processing complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)