#!/usr/bin/env python
"""
Test script to validate the common embeddings module with sample documents.

This test uses synthetic sample data to verify the pipeline works correctly.
For processing real data, use main.py instead.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from llama_index.core import Document
from common_embeddings import (
    Config,
    EmbeddingPipeline,
    ChromaDBStore,
    EntityType,
    SourceType,
)
from common_embeddings.utils import setup_logging, get_logger


def test_pipeline():
    """
    Test the embedding pipeline with sample synthetic data.
    
    This function creates a few sample documents to verify the pipeline
    works correctly. For processing real data from real_estate_data/ or
    wikipedia data, use main.py instead.
    """
    # Setup logging
    setup_logging(level="INFO")
    logger = get_logger(__name__)
    
    logger.info("Starting common embeddings pipeline test with SAMPLE data")
    
    # Load configuration
    config = Config.from_yaml("common_embeddings/config.yaml")
    logger.info(f"Loaded configuration: provider={config.embedding.provider}")
    
    # Create pipeline
    pipeline = EmbeddingPipeline(config)
    
    # Create sample documents
    documents = [
        Document(
            text="Beautiful 3-bedroom house in Park City with mountain views. Features include granite countertops, hardwood floors, and a spacious backyard. Perfect for families.",
            metadata={
                "listing_id": "PC001",
                "property_type": "house",
                "bedrooms": 3,
                "city": "Park City",
                "state": "Utah"
            }
        ),
        Document(
            text="Modern downtown condo with city skyline views. Walking distance to restaurants and shopping. Features include stainless steel appliances and in-unit laundry.",
            metadata={
                "listing_id": "SF001",
                "property_type": "condo",
                "bedrooms": 2,
                "city": "San Francisco",
                "state": "California"
            }
        ),
        Document(
            text="The Marina District is a neighborhood located in San Francisco, California. The area is known for its Mediterranean-style architecture and its location along San Francisco Bay.",
            metadata={
                "neighborhood_id": "marina_district",
                "neighborhood_name": "Marina District",
                "city": "San Francisco",
                "state": "California"
            }
        )
    ]
    
    # Process property documents
    logger.info("Processing property documents...")
    property_results = []
    for result in pipeline.process_documents(
        documents[:2],
        EntityType.PROPERTY,
        SourceType.PROPERTY_JSON,
        "test_properties.json"
    ):
        property_results.append(result)
        logger.info(f"Generated embedding for property: {result.metadata.listing_id}")
    
    # Process neighborhood document
    logger.info("Processing neighborhood document...")
    neighborhood_results = []
    for result in pipeline.process_documents(
        documents[2:3],
        EntityType.NEIGHBORHOOD,
        SourceType.NEIGHBORHOOD_JSON,
        "test_neighborhoods.json"
    ):
        neighborhood_results.append(result)
        logger.info(f"Generated embedding for neighborhood: {result.metadata.neighborhood_name}")
    
    # Store in ChromaDB
    logger.info("Storing embeddings in ChromaDB...")
    store = ChromaDBStore(config.chromadb)
    
    # Create collection for properties
    store.create_collection(
        name="property_test_v1",
        metadata={
            "entity_type": "property",
            "model": pipeline.model_identifier,
            "test": True
        },
        force_recreate=True
    )
    
    # Add property embeddings
    if property_results:
        embeddings = [r.embedding for r in property_results]
        texts = [documents[i].text for i in range(len(property_results))]
        metadatas = [r.metadata.model_dump() for r in property_results]
        ids = [r.metadata.embedding_id for r in property_results]
        
        store.add_embeddings(embeddings, texts, metadatas, ids)
        logger.info(f"Stored {len(property_results)} property embeddings")
    
    # Test retrieval
    logger.info("Testing bulk retrieval...")
    retrieved_data = store.get_all(include_embeddings=True)
    logger.info(f"Retrieved {len(retrieved_data.get('ids', []))} items from storage")
    
    # Print statistics (now returns PipelineStatistics Pydantic model)
    stats = pipeline.get_statistics()
    logger.info("Pipeline Statistics:")
    stats_dict = stats.model_dump()
    for key, value in stats_dict.items():
        logger.info(f"  {key}: {value}")
    
    logger.info("Test completed successfully!")
    
    return True


if __name__ == "__main__":
    try:
        success = test_pipeline()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)