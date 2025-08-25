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
import os
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv
# Try to load from parent directory .env first, then current directory
if Path("../.env").exists():
    load_dotenv("../.env")
else:
    load_dotenv()

from .models import Config, EntityType, SourceType
from .models.config import load_config_from_yaml
from .pipeline import EmbeddingPipeline
from .utils import setup_logging, get_logger
from .utils.progress import create_progress_indicator
from .loaders import RealEstateLoader, WikipediaLoader
from .services import CollectionManager


# Data loading functions have been moved to loaders/ module


def process_real_estate_data(config: Config, force_recreate: bool = False):
    """Process real estate data from real_estate_data/ directory."""
    logger = get_logger(__name__)
    logger.info("Processing real estate data")
    
    # Load data using new loader
    data_dir = Path("../real_estate_data")
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        return
    
    loader = RealEstateLoader(data_dir)
    if not loader.validate_source():
        logger.error("Invalid real estate data source")
        return
    
    property_docs, neighborhood_docs = loader.load_all()
    
    # Create pipeline and collection manager
    pipeline = EmbeddingPipeline(config)
    collection_manager = CollectionManager(config)
    
    # Process properties with progress indicator
    if property_docs:
        # Get collection name for properties
        prop_collection = collection_manager.get_collection_name(
            EntityType.PROPERTY,
            pipeline.model_identifier
        )
        
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
            "real_estate_data/properties.json",
            collection_name=prop_collection,
            force_recreate=force_recreate
        ):
            property_count += 1
            progress.update(current=property_count)
        
        progress.complete()
        logger.info(f"Completed processing {property_count} property embeddings")
    
    # Process neighborhoods with progress indicator
    if neighborhood_docs:
        # Get collection name for neighborhoods
        neighborhood_collection = collection_manager.get_collection_name(
            EntityType.NEIGHBORHOOD,
            pipeline.model_identifier
        )
        
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
            "real_estate_data/neighborhoods.json",
            collection_name=neighborhood_collection,
            force_recreate=force_recreate
        ):
            neighborhood_count += 1
            progress.update(current=neighborhood_count)
        
        progress.complete()
        logger.info(f"Completed processing {neighborhood_count} neighborhood embeddings")
    
    # Collections were created during processing, no need to create again
    
    # Get statistics (now returns PipelineStatistics Pydantic model)
    stats = pipeline.get_statistics()
    logger.info("Pipeline Statistics:")
    stats_dict = stats.model_dump()
    for key, value in stats_dict.items():
        logger.info(f"  {key}: {value}")
    
    return stats


def process_wikipedia_data(config: Config, force_recreate: bool = False, max_articles: int = None):
    """Process Wikipedia data from data/wikipedia/ directory."""
    logger = get_logger(__name__)
    logger.info("Processing Wikipedia data")
    
    # Load data using new loader
    data_dir = Path("../data")
    loader = WikipediaLoader(data_dir, max_articles)
    
    if not loader.validate_source():
        logger.warning("No Wikipedia data source found")
        return
    
    wikipedia_docs = loader.load_all()
    
    if not wikipedia_docs:
        logger.warning("No Wikipedia documents found to process")
        return
    
    # Create pipeline and collection manager
    pipeline = EmbeddingPipeline(config)
    collection_manager = CollectionManager(config)
    
    # Get collection name for Wikipedia
    wiki_collection = collection_manager.get_collection_name(
        EntityType.WIKIPEDIA_ARTICLE,
        pipeline.model_identifier
    )
    
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
        "../data/wikipedia/pages",
        collection_name=wiki_collection,
        force_recreate=force_recreate
    ):
        wiki_count += 1
        progress.update(current=wiki_count)
    
    progress.complete()
    logger.info(f"Completed processing {wiki_count} Wikipedia embeddings")
    
    # Get statistics (now returns PipelineStatistics Pydantic model)
    stats = pipeline.get_statistics()
    logger.info("Pipeline Statistics:")
    stats_dict = stats.model_dump()
    for key, value in stats_dict.items():
        logger.info(f"  {key}: {value}")
    
    return stats


def main():
    """Main entry point for processing real data.
    
    Returns:
        Dict containing consolidated statistics from all processing operations
    """
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
    config_path = args.config
    config = load_config_from_yaml(config_path)
    logger.info(f"Loaded configuration from {config_path}: provider={config.embedding.provider}")
    
    # Process based on data type and collect statistics
    all_stats = {}
    
    if args.data_type in ["real_estate", "all"]:
        logger.info("\n--- Processing Real Estate Data ---")
        real_estate_stats = process_real_estate_data(config, args.force_recreate)
        if real_estate_stats:
            all_stats['real_estate'] = real_estate_stats
    
    if args.data_type in ["wikipedia", "all"]:
        logger.info("\n--- Processing Wikipedia Data ---")
        wikipedia_stats = process_wikipedia_data(config, args.force_recreate, args.max_articles)
        if wikipedia_stats:
            all_stats['wikipedia'] = wikipedia_stats
    
    
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
        logger.info(f"Property collection: {prop_info.collection_name} ({prop_info.count} embeddings)")
        logger.info(f"Neighborhood collection: {neighborhood_info.collection_name} ({neighborhood_info.count} embeddings)")
    
    if args.data_type in ["wikipedia", "all"]:
        wiki_info = collection_manager.get_entity_collection_info(EntityType.WIKIPEDIA_ARTICLE, model_id)
        logger.info(f"Wikipedia collection: {wiki_info.collection_name} ({wiki_info.count} embeddings)")
    
    # Create consolidated statistics summary
    final_summary = {
        'data_type': args.data_type,
        'total_documents': 0,
        'total_chunks': 0,
        'total_embeddings': 0,
        'total_errors': 0,
        'collections': {}
    }
    
    # Aggregate statistics from all processing operations
    for source, stats in all_stats.items():
        final_summary['total_documents'] += stats.documents_processed
        final_summary['total_chunks'] += stats.chunks_created
        final_summary['total_embeddings'] += stats.embeddings_generated
        final_summary['total_errors'] += stats.errors
    
    # Add collection info to summary
    if args.data_type in ["real_estate", "all"]:
        prop_info = collection_manager.get_entity_collection_info(EntityType.PROPERTY, model_id)
        neighborhood_info = collection_manager.get_entity_collection_info(EntityType.NEIGHBORHOOD, model_id)
        final_summary['collections']['properties'] = {
            'name': prop_info.collection_name,
            'count': prop_info.count,
            'exists': prop_info.exists
        }
        final_summary['collections']['neighborhoods'] = {
            'name': neighborhood_info.collection_name,
            'count': neighborhood_info.count,
            'exists': neighborhood_info.exists
        }
    
    if args.data_type in ["wikipedia", "all"]:
        wiki_info = collection_manager.get_entity_collection_info(EntityType.WIKIPEDIA_ARTICLE, model_id)
        final_summary['collections']['wikipedia'] = {
            'name': wiki_info.collection_name,
            'count': wiki_info.count,
            'exists': wiki_info.exists
        }
    
    # Log final summary
    logger.info("\n" + "=" * 60)
    logger.info("FINAL PROCESSING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Data Type: {final_summary['data_type']}")
    logger.info(f"Total Documents Processed: {final_summary['total_documents']}")
    logger.info(f"Total Chunks Created: {final_summary['total_chunks']}")
    logger.info(f"Total Embeddings Generated: {final_summary['total_embeddings']}")
    logger.info(f"Total Errors: {final_summary['total_errors']}")
    
    if final_summary['total_documents'] > 0:
        avg_chunks = final_summary['total_chunks'] / final_summary['total_documents']
        logger.info(f"Average Chunks per Document: {avg_chunks:.1f}")
    
    logger.info("\nCollections Created/Updated:")
    for collection_type, info in final_summary['collections'].items():
        status = "✓" if info['exists'] else "✗"
        logger.info(f"  {status} {collection_type}: {info['name']} ({info['count']} embeddings)")
    
    logger.info("\n" + "=" * 60)
    logger.info("Processing complete!")
    logger.info("=" * 60)
    
    return final_summary


# This module should be executed as: python -m common_embeddings
# Direct execution with 'python main.py' is not supported
