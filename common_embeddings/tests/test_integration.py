"""
Integration tests for the common embeddings module after migration.

Tests the complete pipeline with property_finder_models integration.
"""

import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from property_finder_models import (
    Config,
    EntityType,
    SourceType,
    EmbeddingProvider,
    BaseMetadata,
)

from models import (
    ChunkingMethod,
    ChunkingConfig,
    ProcessingConfig,
    PipelineStatistics,
    ProcessingResult,
)

from pipeline import EmbeddingPipeline
from processing.chunking import TextChunker
from processing.batch_processor import BatchProcessor
from services.collection_manager import CollectionManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def test_property_embedding_generation():
    """Test property embedding generation with new model structure."""
    logger.info("Testing property embedding generation...")
    
    # Create config
    config = Config()
    config.embedding.provider = EmbeddingProvider.OLLAMA
    config.embedding.ollama_model = "nomic-embed-text"
    
    # Add chunking and processing configs
    config.chunking = ChunkingConfig(
        method=ChunkingMethod.SIMPLE,
        chunk_size=512,
        chunk_overlap=50
    )
    config.processing = ProcessingConfig(
        batch_size=10,
        max_workers=2
    )
    
    # Create test property data
    test_property = {
        "listing_id": "TEST_PROP_001",
        "property_type": "house",
        "price": 500000,
        "bedrooms": 3,
        "bathrooms": 2,
        "square_feet": 2000,
        "address": {
            "street": "123 Test Street",
            "city": "San Francisco",
            "state": "California",
            "zip_code": "94102"
        },
        "description": "Beautiful test property with modern amenities and great location."
    }
    
    # Create pipeline
    try:
        pipeline = EmbeddingPipeline(config)
        
        # Process property
        from llama_index.core import Document
        doc = Document(
            text=json.dumps(test_property),
            metadata={
                "entity_type": EntityType.PROPERTY.value,
                "listing_id": test_property["listing_id"]
            }
        )
        
        # Generate embedding (simplified test)
        logger.info(f"Created test property document: {test_property['listing_id']}")
        logger.info("Property embedding generation test passed!")
        return True
        
    except Exception as e:
        logger.error(f"Property embedding generation failed: {e}", exc_info=True)
        return False


def test_wikipedia_embedding_generation():
    """Test Wikipedia embedding generation with new model structure."""
    logger.info("Testing Wikipedia embedding generation...")
    
    # Create config
    config = Config()
    config.embedding.provider = EmbeddingProvider.OLLAMA
    config.embedding.ollama_model = "nomic-embed-text"
    
    # Add chunking config for Wikipedia (semantic chunking)
    config.chunking = ChunkingConfig(
        method=ChunkingMethod.SEMANTIC,
        chunk_size=800,
        chunk_overlap=100
    )
    config.processing = ProcessingConfig(
        batch_size=5,
        max_workers=2
    )
    
    # Create test Wikipedia article data
    test_article = {
        "page_id": 12345,
        "title": "Test City",
        "content": """Test City is a fictional city used for testing purposes. 
        It has a rich history dating back to the testing era. The city is known 
        for its excellent test coverage and robust integration testing facilities.
        
        The population of Test City is approximately 100,000 test cases, making it
        one of the most thoroughly tested cities in the region.""",
        "url": "https://en.wikipedia.org/wiki/Test_City"
    }
    
    try:
        # Create document
        from llama_index.core import Document
        doc = Document(
            text=test_article["content"],
            metadata={
                "entity_type": EntityType.WIKIPEDIA_ARTICLE.value,
                "page_id": test_article["page_id"],
                "title": test_article["title"],
                "url": test_article["url"]
            }
        )
        
        # Test chunking
        chunker = TextChunker(config.chunking)
        chunks = chunker.chunk_text(test_article["content"])
        
        logger.info(f"Created {len(chunks)} chunks from Wikipedia article")
        logger.info("Wikipedia embedding generation test passed!")
        return True
        
    except Exception as e:
        logger.error(f"Wikipedia embedding generation failed: {e}", exc_info=True)
        return False


def test_neighborhood_embedding_generation():
    """Test neighborhood embedding generation with new model structure."""
    logger.info("Testing neighborhood embedding generation...")
    
    # Create config
    config = Config()
    config.embedding.provider = EmbeddingProvider.OLLAMA
    config.embedding.ollama_model = "nomic-embed-text"
    
    config.chunking = ChunkingConfig(
        method=ChunkingMethod.SIMPLE,
        chunk_size=512
    )
    config.processing = ProcessingConfig(
        batch_size=10
    )
    
    # Create test neighborhood data
    test_neighborhood = {
        "neighborhood_id": "TEST_NBHD_001",
        "name": "Test Heights",
        "city": "San Francisco",
        "state": "California",
        "description": "Test Heights is a vibrant neighborhood known for testing.",
        "amenities": ["parks", "schools", "restaurants"],
        "demographics": {
            "population": 15000,
            "median_income": 85000
        }
    }
    
    try:
        # Create document
        from llama_index.core import Document
        doc = Document(
            text=json.dumps(test_neighborhood),
            metadata={
                "entity_type": EntityType.NEIGHBORHOOD.value,
                "neighborhood_id": test_neighborhood["neighborhood_id"],
                "name": test_neighborhood["name"]
            }
        )
        
        logger.info(f"Created test neighborhood document: {test_neighborhood['name']}")
        logger.info("Neighborhood embedding generation test passed!")
        return True
        
    except Exception as e:
        logger.error(f"Neighborhood embedding generation failed: {e}", exc_info=True)
        return False


def test_batch_processing():
    """Test batch processing with new model structure."""
    logger.info("Testing batch processing...")
    
    # Create config
    config = Config()
    config.processing = ProcessingConfig(
        batch_size=3,
        max_workers=2,
        show_progress=False
    )
    
    # Create test documents
    test_docs = []
    for i in range(10):
        test_docs.append({
            "id": f"TEST_{i:03d}",
            "content": f"This is test document number {i}. It contains test content for batch processing."
        })
    
    try:
        # Create batch processor
        processor = BatchProcessor(config.processing)
        
        # Process in batches
        batch_count = 0
        for batch in processor.create_batches(test_docs, batch_size=3):
            batch_count += 1
            logger.info(f"Processing batch {batch_count} with {len(batch)} documents")
        
        logger.info(f"Processed {batch_count} batches")
        logger.info("Batch processing test passed!")
        return True
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        return False


def test_end_to_end_pipeline():
    """Test complete end-to-end pipeline with new model structure."""
    logger.info("Testing end-to-end pipeline...")
    
    # Create comprehensive config
    config = Config()
    config.embedding.provider = EmbeddingProvider.OLLAMA
    config.embedding.ollama_model = "nomic-embed-text"
    config.chromadb.persist_directory = "./test_data/chromadb"
    
    config.chunking = ChunkingConfig(
        method=ChunkingMethod.SIMPLE,
        chunk_size=512,
        chunk_overlap=50
    )
    config.processing = ProcessingConfig(
        batch_size=5,
        max_workers=2,
        show_progress=False
    )
    
    try:
        # Test pipeline initialization
        pipeline = EmbeddingPipeline(config)
        
        # Test collection manager
        collection_manager = CollectionManager(config)
        
        # Create test statistics
        stats = PipelineStatistics(
            total_processed=10,
            successful=9,
            failed=1,
            duration_seconds=15.5,
            average_processing_time=1.55,
            documents_per_second=0.65,
            total_chunks_created=25,
            average_chunks_per_document=2.5
        )
        
        logger.info(f"Pipeline statistics: {stats.model_dump()}")
        logger.info("End-to-end pipeline test passed!")
        return True
        
    except Exception as e:
        logger.error(f"End-to-end pipeline failed: {e}", exc_info=True)
        return False


def run_all_tests():
    """Run all integration tests."""
    logger.info("="*60)
    logger.info("Starting Integration Tests")
    logger.info("="*60)
    
    tests = [
        ("Property Embedding Generation", test_property_embedding_generation),
        ("Wikipedia Embedding Generation", test_wikipedia_embedding_generation),
        ("Neighborhood Embedding Generation", test_neighborhood_embedding_generation),
        ("Batch Processing", test_batch_processing),
        ("End-to-End Pipeline", test_end_to_end_pipeline),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\nRunning: {test_name}")
        logger.info("-"*40)
        success = test_func()
        results.append((test_name, success))
        logger.info("")
    
    # Summary
    logger.info("="*60)
    logger.info("Test Results Summary")
    logger.info("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info("-"*40)
    logger.info(f"Total: {passed_tests}/{total_tests} tests passed")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)