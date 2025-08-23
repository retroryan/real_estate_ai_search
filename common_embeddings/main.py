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
    
    return stats


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
    
    return stats


def process_json_articles(config: Config, json_path: Path, force_recreate: bool = False):
    """
    Process Wikipedia articles from evaluation JSON file.
    
    Args:
        config: Configuration object
        json_path: Path to JSON file with articles
        force_recreate: Whether to recreate collections
        
    Returns:
        Pipeline statistics
    """
    logger = get_logger(__name__)
    logger.info(f"Processing articles from JSON: {json_path}")
    
    # Load articles from JSON
    with open(json_path) as f:
        data = json.load(f)
    
    articles = data.get("articles", [])
    logger.info(f"Loaded {len(articles)} articles from JSON")
    
    # Create Document objects from JSON data
    from llama_index.core import Document
    documents = []
    
    for article in articles:
        # Combine short and long summaries for more content
        text_content = f"{article['title']}\n\n"
        text_content += f"{article['summary']}\n\n"
        if article.get('long_summary'):
            text_content += f"{article['long_summary']}\n\n"
        if article.get('key_topics'):
            text_content += f"Topics: {article['key_topics']}"
        
        doc = Document(
            text=text_content,
            metadata={
                "page_id": str(article["page_id"]),
                "title": article["title"],
                "city": article.get("city", ""),
                "county": article.get("county", ""),
                "state": article.get("state", ""),
                "categories": ", ".join(article.get("categories", [])),
                "source": "evaluation_set",
                "source_file": article.get("html_file", "")
            }
        )
        documents.append(doc)
    
    if not documents:
        logger.warning("No documents created from JSON")
        return None
    
    # Create pipeline
    pipeline = EmbeddingPipeline(config)
    
    # Process documents with progress indicator
    logger.info(f"Processing {len(documents)} evaluation articles...")
    progress = create_progress_indicator(
        total=len(documents),
        operation="Processing evaluation articles",
        show_console=True
    )
    
    # Store in collection first
    logger.info("Setting up ChromaDB collection for evaluation...")
    collection_manager = CollectionManager(config)
    
    # Create collection for evaluation articles
    eval_collection = collection_manager.create_collection_for_entity(
        entity_type=EntityType.WIKIPEDIA_ARTICLE,
        model_identifier=pipeline.model_identifier,
        force_recreate=force_recreate,
        additional_metadata={
            "source": "evaluation_set",
            "json_path": str(json_path),
            "article_count": len(articles)
        }
    )
    
    # Get the ChromaDB store to add embeddings
    from common_embeddings.storage import ChromaDBStore
    chroma_store = ChromaDBStore(config.chromadb)
    chroma_store.create_collection(
        name=eval_collection,
        metadata={
            "source": "evaluation_set",
            "json_path": str(json_path),
            "article_count": len(articles)
        },
        force_recreate=False  # Already recreated above
    )
    
    doc_count = 0
    embeddings_to_add = []
    
    for result in pipeline.process_documents(
        documents,
        EntityType.WIKIPEDIA_ARTICLE,
        SourceType.EVALUATION_JSON,
        str(json_path)
    ):
        # Collect embeddings to batch add
        # Ensure metadata is a dict
        if hasattr(result.metadata, 'to_dict'):
            metadata_dict = result.metadata.to_dict()
        elif hasattr(result.metadata, 'dict'):
            metadata_dict = result.metadata.dict()
        elif hasattr(result.metadata, 'model_dump'):
            metadata_dict = result.metadata.model_dump()
        else:
            metadata_dict = dict(result.metadata) if not isinstance(result.metadata, dict) else result.metadata
        
        doc_id = metadata_dict.get("page_id", f"doc_{doc_count}")
        
        embeddings_to_add.append({
            "embedding": result.embedding,
            "metadata": metadata_dict,
            "document_id": f"{doc_id}_{doc_count}"
        })
        
        doc_count += 1
        progress.update(current=doc_count)
        
        # Batch add every 10 embeddings
        if len(embeddings_to_add) >= 10:
            ids = [e["document_id"] for e in embeddings_to_add]
            embeddings = [e["embedding"] for e in embeddings_to_add]
            metadatas = [e["metadata"] for e in embeddings_to_add]
            texts = [str(e["metadata"].get("title", "") if isinstance(e["metadata"], dict) else getattr(e["metadata"], "title", "")) for e in embeddings_to_add]
            
            chroma_store.add_embeddings(
                embeddings=embeddings,
                texts=texts,
                metadatas=metadatas,
                ids=ids
            )
            embeddings_to_add = []
    
    # Add remaining embeddings
    if embeddings_to_add:
        ids = [e["document_id"] for e in embeddings_to_add]
        embeddings = [e["embedding"] for e in embeddings_to_add]
        metadatas = [e["metadata"] for e in embeddings_to_add]
        texts = [str(e["metadata"].get("title", "")) for e in embeddings_to_add]
        
        chroma_store.add_embeddings(
            embeddings=embeddings,
            texts=texts,
            metadatas=metadatas,
            ids=ids
        )
    
    progress.complete()
    logger.info(f"Completed processing and storing {doc_count} evaluation embeddings")
    logger.info(f"Created evaluation collection: {eval_collection}")
    
    # Get statistics
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
        choices=["real_estate", "wikipedia", "all", "evaluation"],
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
        "--evaluation-json",
        type=str,
        default="common_embeddings/evaluate_data/evaluate_articles.json",
        help="Path to evaluation JSON file (for --data-type=evaluation)"
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
    
    if args.data_type == "evaluation":
        logger.info("\n--- Processing Evaluation Data ---")
        json_path = Path(args.evaluation_json)
        if not json_path.exists():
            logger.error(f"Evaluation JSON file not found: {json_path}")
            sys.exit(1)
        eval_stats = process_json_articles(config, json_path, args.force_recreate)
        if eval_stats:
            all_stats['evaluation'] = eval_stats
    
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
    
    if args.data_type in ["wikipedia", "all", "evaluation"]:
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


if __name__ == "__main__":
    try:
        summary = main()
        # Optionally write summary to file for external tools
        if summary:
            import json
            summary_path = Path("data/common_embeddings/last_run_summary.json")
            summary_path.parent.mkdir(exist_ok=True, parents=True)
            with open(summary_path, "w") as f:
                # Convert any non-serializable objects
                json_summary = json.loads(json.dumps(summary, default=str))
                json.dump(json_summary, f, indent=2)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)