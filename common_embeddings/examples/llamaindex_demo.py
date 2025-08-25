#!/usr/bin/env python
"""
Demo script showing LlamaIndex best practices implementation.

This demonstrates the enhanced pipeline that follows LlamaIndex
best practices for node-centric processing, selective retrieval,
and efficient storage patterns.
"""

import sys
from pathlib import Path
from typing import List

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from llama_index.core import Document

from models.config import load_config_from_yaml
from models import EntityType, SourceType
from processing import LlamaIndexOptimizedPipeline
from loaders.optimized_loader import OptimizedDocumentLoader
from services import CollectionManager
from utils import setup_logging, get_logger

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)


def demo_llamaindex_optimization():
    """
    Demonstrate LlamaIndex best practices implementation.
    """
    logger.info("=" * 60)
    logger.info("LlamaIndex Best Practices Demo")
    logger.info("=" * 60)
    
    # Load configuration
    config = load_config_from_yaml("../config.yaml")
    logger.info(f"Loaded configuration with provider: {config.embedding.provider}")
    
    # Initialize optimized pipeline
    logger.info("\n--- Initializing LlamaIndex-Optimized Pipeline ---")
    pipeline = LlamaIndexOptimizedPipeline(config, store_embeddings=True)
    
    # Demo 1: Optimized document loading
    logger.info("\n--- Demo 1: Optimized Document Loading ---")
    demo_optimized_loading(config)
    
    # Demo 2: Node-centric processing
    logger.info("\n--- Demo 2: Node-Centric Processing ---")
    demo_node_centric_processing(pipeline, config)
    
    # Demo 3: Selective data retrieval
    logger.info("\n--- Demo 3: Selective Data Retrieval ---")
    demo_selective_retrieval(pipeline, config)
    
    # Demo 4: Lazy processing for memory efficiency
    logger.info("\n--- Demo 4: Lazy Processing for Memory Efficiency ---")
    demo_lazy_processing(pipeline, config)
    
    logger.info("\n" + "=" * 60)
    logger.info("LlamaIndex Best Practices Demo Complete!")
    logger.info("=" * 60)


def demo_optimized_loading(config):
    """Demo optimized document loading patterns."""
    data_path = Path("../data")
    
    # Initialize optimized loader
    loader = OptimizedDocumentLoader(
        base_path=data_path,
        entity_type=EntityType.WIKIPEDIA_ARTICLE,
        source_type=SourceType.WIKIPEDIA_HTML
    )
    
    # Demo lazy loading (memory efficient)
    logger.info("Loading documents lazily...")
    document_count = 0
    for document in loader.load_documents_lazy(
        file_patterns=["wikipedia/pages/*.html"],
        max_documents=3
    ):
        logger.info(f"  Loaded document: {document.doc_id} ({len(document.text)} chars)")
        document_count += 1
    
    logger.info(f"Loaded {document_count} documents using lazy loading")
    
    # Demo batch loading
    logger.info("\nLoading documents in batches...")
    batch_count = 0
    for batch in loader.load_documents_batch(
        file_patterns=["wikipedia/pages/*.html"],
        batch_size=2,
        max_documents=4
    ):
        batch_count += 1
        logger.info(f"  Batch {batch_count}: {len(batch)} documents")
    
    logger.info(f"Processed {batch_count} batches")


def demo_node_centric_processing(pipeline, config):
    """Demo node-centric processing following LlamaIndex best practices."""
    
    # Create sample documents with proper IDs and metadata
    documents = [
        Document(
            text="San Francisco is a major city in California known for its tech industry and cultural diversity.",
            metadata={
                "title": "San Francisco Overview",
                "entity_type": "city",
                "region": "Bay Area"
            },
            doc_id="sf_overview_001"
        ),
        Document(
            text="The Golden Gate Bridge is an iconic suspension bridge spanning the Golden Gate strait. It connects San Francisco to Marin County and is painted in International Orange.",
            metadata={
                "title": "Golden Gate Bridge",
                "entity_type": "landmark", 
                "region": "Bay Area"
            },
            doc_id="gg_bridge_002"
        )
    ]
    
    logger.info(f"Processing {len(documents)} documents with node-centric approach...")
    
    # Setup collection
    collection_manager = CollectionManager(config)
    collection_name = collection_manager.get_collection_name(
        EntityType.WIKIPEDIA_ARTICLE,
        pipeline.model_identifier
    )
    
    # Process documents - the pipeline will convert to nodes internally
    results = []
    for result in pipeline.process_documents_optimized(
        documents=documents,
        entity_type=EntityType.WIKIPEDIA_ARTICLE,
        source_type=SourceType.EVALUATION_JSON,
        source_file="demo_documents",
        collection_name=collection_name,
        force_recreate=False
    ):
        results.append(result)
        logger.info(f"  Processed node: {result.node_id} ({len(result.text)} chars)")
        if result.relationships:
            logger.info(f"    Relationships: {list(result.relationships.keys())}")
    
    logger.info(f"Created {len(results)} embeddings from {len(documents)} documents")
    
    # Show statistics
    stats = pipeline.get_statistics()
    logger.info(f"Pipeline stats: {stats.documents_processed} docs → {stats.chunks_created} nodes → {stats.embeddings_generated} embeddings")


def demo_selective_retrieval(pipeline, config):
    """Demo selective data retrieval patterns."""
    
    # Create documents with different metadata for filtering
    documents = [
        Document(
            text="This is a technical document about machine learning.",
            metadata={
                "category": "technical",
                "difficulty": "advanced",
                "topic": "ai"
            },
            doc_id="tech_ml_001"
        ),
        Document(
            text="This is a beginner's guide to cooking basics.",
            metadata={
                "category": "lifestyle", 
                "difficulty": "beginner",
                "topic": "cooking"
            },
            doc_id="cook_basic_002"
        ),
        Document(
            text="Advanced algorithms and data structures for computer science.",
            metadata={
                "category": "technical",
                "difficulty": "advanced", 
                "topic": "algorithms"
            },
            doc_id="cs_algo_003"
        )
    ]
    
    # Demo selective retrieval - only technical documents
    logger.info("Processing with selective retrieval (technical documents only)...")
    
    technical_filter = {"category": "technical"}
    
    results = []
    for result in pipeline.process_documents_optimized(
        documents=documents,
        entity_type=EntityType.WIKIPEDIA_ARTICLE,
        source_type=SourceType.EVALUATION_JSON,
        source_file="selective_demo",
        metadata_filter=technical_filter
    ):
        results.append(result)
        logger.info(f"  Selected document: {result.node_id}")
    
    logger.info(f"Selected {len(results)} documents out of {len(documents)} using filter: {technical_filter}")


def demo_lazy_processing(pipeline, config):
    """Demo lazy processing for memory efficiency."""
    
    def document_generator():
        """Generate documents lazily."""
        for i in range(5):
            yield Document(
                text=f"This is document number {i+1} with some sample content for processing.",
                metadata={
                    "doc_number": i+1,
                    "batch": "lazy_demo"
                },
                doc_id=f"lazy_doc_{i+1:03d}"
            )
    
    logger.info("Processing documents lazily in batches...")
    
    batch_count = 0
    total_results = 0
    
    for batch_results in pipeline.process_documents_lazy(
        document_iterator=document_generator(),
        entity_type=EntityType.WIKIPEDIA_ARTICLE,
        source_type=SourceType.EVALUATION_JSON,
        source_file="lazy_demo",
        batch_size=2
    ):
        batch_count += 1
        batch_size = len(batch_results)
        total_results += batch_size
        logger.info(f"  Batch {batch_count}: Processed {batch_size} documents")
    
    logger.info(f"Lazy processing complete: {batch_count} batches, {total_results} total results")


if __name__ == "__main__":
    try:
        demo_llamaindex_optimization()
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        sys.exit(1)