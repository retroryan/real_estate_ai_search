"""Main embedding pipeline orchestrating document conversion, chunking, and embedding generation."""

import time
from typing import List, Dict, Any, Optional, Callable

from llama_index.core import Document
from llama_index.core.schema import TextNode
from llama_index.core.embeddings import BaseEmbedding

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.embeddings.factory import EmbeddingFactory
from squack_pipeline.embeddings.document_converter import DocumentConverter
from squack_pipeline.embeddings.text_chunker import TextChunker
from squack_pipeline.embeddings.batch_processor import BatchProcessor
from squack_pipeline.utils.logging import PipelineLogger


class EmbeddingPipeline:
    """Main embedding pipeline following common_embeddings patterns."""
    
    def __init__(self, config: PipelineSettings):
        """Initialize embedding pipeline.
        
        Args:
            config: Complete pipeline configuration
        """
        self.config = config
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        
        # Initialize components
        self.embed_model: Optional[BaseEmbedding] = None
        self.document_converter: Optional[DocumentConverter] = None
        self.text_chunker: Optional[TextChunker] = None
        self.batch_processor: Optional[BatchProcessor] = None
        
        # Metrics
        self.metrics = {
            "documents_converted": 0,
            "nodes_created": 0,
            "embeddings_generated": 0,
            "processing_time": 0.0,
            "embedding_success_rate": 0.0
        }
    
    def initialize(self) -> bool:
        """Initialize all pipeline components.
        
        Returns:
            True if initialization successful, False otherwise
        """
        self.logger.info("Initializing embedding pipeline")
        
        try:
            # Create embedding model
            self.embed_model = EmbeddingFactory.create_from_config(self.config.embedding)
            provider_name = self.config.embedding.provider.value
            self.logger.info(f"Created embedding model: {provider_name}")
            
            # Create document converter
            self.document_converter = DocumentConverter()
            
            # Create text chunker
            self.text_chunker = TextChunker(self.config.processing, self.embed_model)
            
            # Create batch processor
            self.batch_processor = BatchProcessor(
                self.config.processing,
                self.embed_model,
                progress_callback=self._progress_callback
            )
            
            self.logger.success("Embedding pipeline initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize embedding pipeline: {e}")
            return False
    
    def process_gold_properties(self, properties_data: List[Dict[str, Any]]) -> List[TextNode]:
        """Process Gold tier properties through complete embedding pipeline.
        
        Args:
            properties_data: List of property records from Gold tier
            
        Returns:
            List of TextNode objects with embeddings
        """
        if not properties_data:
            self.logger.warning("No properties data provided")
            return []
        
        start_time = time.time()
        self.logger.info(f"Processing {len(properties_data)} properties through embedding pipeline")
        
        try:
            # Step 1: Convert to Documents
            self.logger.info("Converting properties to LlamaIndex Documents")
            documents = self.document_converter.convert_gold_properties_to_documents(properties_data)
            
            if not self.document_converter.validate_documents(documents):
                raise ValueError("Document validation failed")
            
            self.metrics["documents_converted"] = len(documents)
            
            # Step 2: Chunk documents into nodes
            if self.config.processing.enable_chunking:
                self.logger.info("Chunking documents into text nodes")
                nodes = self.text_chunker.chunk_documents(documents)
                
                if not self.text_chunker.validate_nodes(nodes):
                    raise ValueError("Node validation failed")
            else:
                self.logger.info("Chunking disabled, converting documents to single nodes")
                nodes = self.text_chunker._documents_to_single_nodes(documents)
            
            self.metrics["nodes_created"] = len(nodes)
            
            # Step 3: Generate embeddings
            if self.config.processing.generate_embeddings:
                self.logger.info("Generating embeddings for text nodes")
                embedded_nodes = self.batch_processor.process_nodes_to_embeddings(nodes)
                
                # Validate embeddings
                embedding_metrics = self.batch_processor.validate_embeddings(embedded_nodes)
                self.metrics["embeddings_generated"] = embedding_metrics["nodes_with_embeddings"]
                self.metrics["embedding_success_rate"] = embedding_metrics["success_rate"]
            else:
                self.logger.info("Embedding generation disabled")
                embedded_nodes = nodes
                self.metrics["embeddings_generated"] = 0
                self.metrics["embedding_success_rate"] = 0.0
            
            # Record processing time
            self.metrics["processing_time"] = time.time() - start_time
            
            self.logger.success(f"Embedding pipeline completed successfully")
            self.logger.info(f"  Documents converted: {self.metrics['documents_converted']}")
            self.logger.info(f"  Nodes created: {self.metrics['nodes_created']}")
            self.logger.info(f"  Embeddings generated: {self.metrics['embeddings_generated']}")
            self.logger.info(f"  Success rate: {self.metrics['embedding_success_rate']:.2%}")
            self.logger.info(f"  Processing time: {self.metrics['processing_time']:.2f}s")
            
            return embedded_nodes
            
        except Exception as e:
            self.logger.error(f"Embedding pipeline failed: {e}")
            raise
    
    def _progress_callback(self, current: int, total: int) -> None:
        """Progress callback for batch processing."""
        if total > 0:
            percentage = (current / total) * 100
            self.logger.info(f"Embedding progress: {current}/{total} ({percentage:.1f}%)")
    
    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get comprehensive pipeline metrics."""
        return {
            **self.metrics,
            "configuration": {
                "embedding_provider": self.config.embedding.provider.value,
                "chunking_method": self.config.processing.chunk_method.value,
                "chunk_size": self.config.processing.chunk_size,
                "batch_size": self.config.processing.batch_size,
                "max_workers": self.config.processing.max_workers,
                "generate_embeddings": self.config.processing.generate_embeddings,
                "enable_chunking": self.config.processing.enable_chunking
            }
        }
    
    def validate_configuration(self) -> bool:
        """Validate embedding pipeline configuration."""
        try:
            # Check embedding provider configuration
            if self.config.embedding.provider.value not in ["voyage", "openai", "ollama", "gemini", "mock"]:
                self.logger.error(f"Unsupported embedding provider: {self.config.embedding.provider}")
                return False
            
            # Check chunking configuration
            if self.config.processing.chunk_size < 128 or self.config.processing.chunk_size > 2048:
                self.logger.error(f"Invalid chunk size: {self.config.processing.chunk_size}")
                return False
            
            # Check batch configuration
            if self.config.processing.batch_size < 1 or self.config.processing.batch_size > 1000:
                self.logger.error(f"Invalid batch size: {self.config.processing.batch_size}")
                return False
            
            # Validate API keys for production
            if self.config.environment == "production":
                if self.config.embedding.provider.value == "voyage" and not self.config.embedding.voyage_api_key:
                    self.logger.error("VOYAGE_API_KEY required for production")
                    return False
                elif self.config.embedding.provider.value == "openai" and not self.config.embedding.openai_api_key:
                    self.logger.error("OPENAI_API_KEY required for production")
                    return False
            
            self.logger.success("Embedding pipeline configuration validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False