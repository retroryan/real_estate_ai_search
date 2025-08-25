"""
Fixed data integration tests for the common embeddings module.

Uses predetermined test articles and queries to ensure consistent,
reproducible testing of the embedding pipeline functionality.
"""

import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import tempfile
import shutil

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from llama_index.core import Document

from common_embeddings.models import (
    EntityType,
    SourceType,
    EmbeddingProvider,
    ChunkingMethod,
    ChunkingConfig,
    ProcessingConfig,
    PipelineStatistics,
    ProcessingResult,
)
from common_embeddings.models.config import load_config_from_yaml, ExtendedConfig
from common_embeddings.pipeline import EmbeddingPipeline
from common_embeddings.processing import LlamaIndexOptimizedPipeline
from common_embeddings.services import CollectionManager
from common_embeddings.storage import ChromaDBStore
from common_embeddings.utils import setup_logging, get_logger

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)


class FixedDataIntegrationTester:
    """
    Integration tester using fixed test data for reproducible results.
    """
    
    def __init__(self):
        """Initialize tester with fixed data."""
        self.test_data_dir = Path(__file__).parent
        self.temp_data_dir = None
        self.config = None
        self.test_articles = None
        self.test_queries = None
        self.pipeline = None
        
        # Load fixed test data
        self._load_test_data()
        self._setup_test_config()
    
    def _load_test_data(self):
        """Load fixed test articles and queries."""
        # Load test articles
        articles_file = self.test_data_dir / "fixed_test_articles.json"
        with open(articles_file, 'r') as f:
            articles_data = json.load(f)
            self.test_articles = articles_data["articles"]
        
        # Load test queries  
        queries_file = self.test_data_dir / "fixed_test_queries.json"
        with open(queries_file, 'r') as f:
            queries_data = json.load(f)
            self.test_queries = queries_data["test_queries"]
        
        logger.info(f"Loaded {len(self.test_articles)} test articles and {len(self.test_queries)} test queries")
    
    def _setup_test_config(self):
        """Setup test configuration."""
        # Create temporary directory for test data
        self.temp_data_dir = Path(tempfile.mkdtemp(prefix="embeddings_test_"))
        
        # Create test config
        self.config = ExtendedConfig()
        self.config.embedding.provider = EmbeddingProvider.OLLAMA
        self.config.embedding.ollama_model = "nomic-embed-text"
        self.config.chromadb.persist_directory = str(self.temp_data_dir / "chromadb")
        
        # Configure chunking for Wikipedia content
        self.config.chunking = ChunkingConfig(
            method=ChunkingMethod.SEMANTIC,
            chunk_size=512,
            chunk_overlap=50
        )
        
        # Configure processing
        self.config.processing = ProcessingConfig(
            batch_size=10,
            max_workers=2,
            show_progress=False
        )
        
        logger.info(f"Created test config with temp directory: {self.temp_data_dir}")
    
    def cleanup(self):
        """Cleanup temporary test data."""
        if self.temp_data_dir and self.temp_data_dir.exists():
            shutil.rmtree(self.temp_data_dir)
            logger.info(f"Cleaned up temp directory: {self.temp_data_dir}")
    
    def test_document_creation(self) -> bool:
        """Test creating LlamaIndex documents from fixed test data."""
        logger.info("Testing document creation from fixed test data...")
        
        try:
            documents = []
            
            for article in self.test_articles:
                # Combine summary and long_summary for richer content
                text_content = f"{article['title']}\n\n{article['summary']}\n\n{article['long_summary']}"
                if article.get('key_topics'):
                    text_content += f"\n\nKey Topics: {article['key_topics']}"
                
                doc = Document(
                    text=text_content,
                    metadata={
                        "page_id": str(article["page_id"]),
                        "title": article["title"],
                        "city": article.get("city", ""),
                        "county": article.get("county", ""),
                        "state": article["state"],
                        "categories": ", ".join(article.get("categories", [])),
                        "source": "fixed_test_data",
                        "confidence": article.get("confidence", 1.0)
                    },
                    doc_id=f"test_{article['page_id']}"
                )
                documents.append(doc)
            
            logger.info(f"Successfully created {len(documents)} test documents")
            
            # Verify document properties
            for i, doc in enumerate(documents[:2]):
                logger.info(f"Document {i+1}: {doc.metadata['title']} ({len(doc.text)} chars)")
            
            return True
            
        except Exception as e:
            logger.error(f"Document creation failed: {e}", exc_info=True)
            return False
    
    def test_pipeline_initialization(self) -> bool:
        """Test pipeline initialization with test config."""
        logger.info("Testing pipeline initialization...")
        
        try:
            # Test standard pipeline
            self.pipeline = EmbeddingPipeline(self.config, store_embeddings=True)
            logger.info("Standard pipeline initialized successfully")
            
            # Test LlamaIndex optimized pipeline
            optimized_pipeline = LlamaIndexOptimizedPipeline(self.config, store_embeddings=True)
            logger.info("LlamaIndex optimized pipeline initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Pipeline initialization failed: {e}", exc_info=True)
            return False
    
    def test_embedding_generation(self) -> bool:
        """Test embedding generation with fixed test data."""
        logger.info("Testing embedding generation with fixed articles...")
        
        if not self.pipeline:
            logger.error("Pipeline not initialized")
            return False
        
        try:
            # Create documents from test articles
            documents = []
            for article in self.test_articles:  # Test with all articles
                text_content = f"{article['title']}\n\n{article['summary']}\n\n{article['long_summary']}"
                
                doc = Document(
                    text=text_content,
                    metadata={
                        "page_id": str(article["page_id"]),
                        "title": article["title"],
                        "state": article["state"]
                    },
                    doc_id=f"test_{article['page_id']}"
                )
                documents.append(doc)
            
            # Setup collection
            collection_manager = CollectionManager(self.config)
            collection_name = collection_manager.get_collection_name(
                EntityType.WIKIPEDIA_ARTICLE,
                self.pipeline.model_identifier
            )
            
            # Process documents through pipeline
            results = []
            for result in self.pipeline.process_documents(
                documents=documents,
                entity_type=EntityType.WIKIPEDIA_ARTICLE,
                source_type=SourceType.EVALUATION_JSON,
                source_file="fixed_test_articles.json",
                collection_name=collection_name,
                force_recreate=True
            ):
                results.append(result)
            
            logger.info(f"Generated {len(results)} embeddings from {len(documents)} documents")
            
            # Verify embeddings
            if results:
                first_result = results[0]
                logger.info(f"First embedding: dimension={len(first_result.embedding)}")
                logger.info(f"First metadata type: {type(first_result.metadata)}")
            
            return len(results) > 0
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}", exc_info=True)
            return False
    
    def test_retrieval_with_queries(self) -> bool:
        """Test retrieval using fixed test queries."""
        logger.info("Testing retrieval with fixed test queries...")
        
        try:
            # First, ensure we have embeddings stored
            if not self.test_embedding_generation():
                logger.error("Failed to generate embeddings for retrieval test")
                return False
            
            # Setup ChromaDB store for querying
            store = ChromaDBStore(self.config.chromadb)
            
            collection_manager = CollectionManager(self.config)
            collection_name = collection_manager.get_collection_name(
                EntityType.WIKIPEDIA_ARTICLE,
                self.pipeline.model_identifier
            )
            
            # Select the collection in the store
            store.create_collection(
                name=collection_name,
                metadata={"test": "fixed_data_retrieval"},
                force_recreate=False  # Use existing collection
            )
            
            # Test a few queries
            test_queries = self.test_queries[:3]  # Test first 3 queries
            successful_queries = 0
            
            for query_data in test_queries:
                query = query_data["query"]
                expected_page_ids = query_data["expected_page_ids"]
                
                logger.info(f"Testing query: '{query}'")
                logger.info(f"Expected page IDs: {expected_page_ids}")
                
                # Generate query embedding using the same model
                try:
                    query_embedding = self.pipeline.embed_model.get_text_embedding(query)
                    
                    # Search in ChromaDB
                    results = store.query(
                        query_embeddings=[query_embedding],
                        n_results=5,
                        where=None
                    )
                    
                    if results and 'metadatas' in results and results['metadatas']:
                        retrieved_page_ids = []
                        for metadata in results['metadatas'][0]:
                            if 'page_id' in metadata:
                                retrieved_page_ids.append(int(metadata['page_id']))
                        
                        logger.info(f"Retrieved page IDs: {retrieved_page_ids}")
                        
                        # Check if any expected page IDs were found
                        found_expected = any(pid in retrieved_page_ids for pid in expected_page_ids)
                        if found_expected:
                            successful_queries += 1
                            logger.info("✅ Query found expected results")
                        else:
                            logger.warning("⚠️  Query did not find expected results")
                    else:
                        logger.warning("No results returned for query")
                
                except Exception as query_error:
                    logger.error(f"Query failed: {query_error}")
            
            logger.info(f"Successful queries: {successful_queries}/{len(test_queries)}")
            return successful_queries > 0
            
        except Exception as e:
            logger.error(f"Retrieval testing failed: {e}", exc_info=True)
            return False
    
    def test_statistics_tracking(self) -> bool:
        """Test pipeline statistics tracking."""
        logger.info("Testing pipeline statistics tracking...")
        
        if not self.pipeline:
            logger.error("Pipeline not initialized")
            return False
        
        try:
            # Get pipeline statistics
            stats = self.pipeline.get_statistics()
            
            logger.info("Pipeline Statistics:")
            stats_dict = stats.model_dump()
            for key, value in stats_dict.items():
                logger.info(f"  {key}: {value}")
            
            # Verify statistics structure
            required_fields = [
                "documents_processed",
                "chunks_created", 
                "embeddings_generated",
                "errors",
                "model_identifier"
            ]
            
            for field in required_fields:
                if not hasattr(stats, field):
                    logger.error(f"Missing required statistics field: {field}")
                    return False
            
            logger.info("Statistics tracking test passed")
            return True
            
        except Exception as e:
            logger.error(f"Statistics tracking failed: {e}", exc_info=True)
            return False
    
    def test_collection_management(self) -> bool:
        """Test collection management operations."""
        logger.info("Testing collection management...")
        
        try:
            collection_manager = CollectionManager(self.config)
            
            # Test collection name generation
            collection_name = collection_manager.get_collection_name(
                EntityType.WIKIPEDIA_ARTICLE,
                "test_model"
            )
            logger.info(f"Generated collection name: {collection_name}")
            
            # Test collection info retrieval
            collection_info = collection_manager.get_entity_collection_info(
                EntityType.WIKIPEDIA_ARTICLE,
                "test_model"
            )
            logger.info(f"Collection info: {collection_info.model_dump()}")
            
            return True
            
        except Exception as e:
            logger.error(f"Collection management failed: {e}", exc_info=True)
            return False


def run_fixed_data_integration_tests() -> bool:
    """Run all fixed data integration tests."""
    logger.info("="*60)
    logger.info("Fixed Data Integration Tests")
    logger.info("="*60)
    
    tester = FixedDataIntegrationTester()
    
    try:
        tests = [
            ("Document Creation", tester.test_document_creation),
            ("Pipeline Initialization", tester.test_pipeline_initialization),
            ("Embedding Generation", tester.test_embedding_generation),
            ("Statistics Tracking", tester.test_statistics_tracking),
            ("Collection Management", tester.test_collection_management),
            ("Retrieval with Queries", tester.test_retrieval_with_queries),
        ]
        
        results = []
        for test_name, test_func in tests:
            logger.info(f"\nRunning: {test_name}")
            logger.info("-"*40)
            try:
                success = test_func()
                results.append((test_name, success))
                status = "✅ PASSED" if success else "❌ FAILED"
                logger.info(f"{test_name}: {status}")
            except Exception as e:
                logger.error(f"{test_name} failed with exception: {e}", exc_info=True)
                results.append((test_name, False))
        
        # Summary
        logger.info("\n" + "="*60)
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
        
    finally:
        # Cleanup
        tester.cleanup()


if __name__ == "__main__":
    success = run_fixed_data_integration_tests()
    sys.exit(0 if success else 1)