"""
Embedding service management for semantic search.

Handles embedding generation and service lifecycle for query embeddings.
"""

from typing import List, Optional, Tuple
from contextlib import contextmanager
import logging
import time

from ...embeddings import QueryEmbeddingService
from ...embeddings.exceptions import (
    EmbeddingServiceError, 
    EmbeddingGenerationError,
    ConfigurationError
)
from ...config import AppConfig


logger = logging.getLogger(__name__)


class SemanticEmbeddingService:
    """Service for managing query embeddings in semantic search."""
    
    def __init__(self, config: Optional[AppConfig] = None):
        """
        Initialize the embedding service.
        
        Args:
            config: Optional application configuration
        """
        self.config = config or AppConfig.load()
        self.service: Optional[QueryEmbeddingService] = None
        
    def initialize(self) -> None:
        """
        Initialize the underlying embedding service.
        
        Raises:
            ConfigurationError: If service cannot be configured
            EmbeddingServiceError: If service cannot be initialized
        """
        try:
            self.service = QueryEmbeddingService(config=self.config.embedding)
            self.service.initialize()
            logger.info("Embedding service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {e}")
            raise EmbeddingServiceError(f"Service initialization failed: {str(e)}")
    
    def close(self) -> None:
        """Close the embedding service and clean up resources."""
        if self.service:
            self.service.close()
            self.service = None
            logger.info("Embedding service closed")
    
    def generate_query_embedding(self, query: str) -> Tuple[List[float], float]:
        """
        Generate an embedding for a query text.
        
        Args:
            query: The query text to embed
            
        Returns:
            Tuple of (embedding vector, generation time in milliseconds)
            
        Raises:
            EmbeddingGenerationError: If embedding generation fails
            EmbeddingServiceError: If service is not initialized
        """
        if not self.service:
            raise EmbeddingServiceError("Embedding service not initialized")
            
        start_time = time.time()
        try:
            logger.info(f"Generating embedding for query: '{query}'")
            embedding = self.service.embed_query(query)
            generation_time_ms = (time.time() - start_time) * 1000
            logger.info(f"Generated query embedding in {generation_time_ms:.1f}ms")
            return embedding, generation_time_ms
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingGenerationError(f"Embedding generation failed: {str(e)}")


@contextmanager
def get_embedding_service(config: Optional[AppConfig] = None):
    """
    Context manager for embedding service lifecycle management.
    
    Args:
        config: Optional application configuration
        
    Yields:
        SemanticEmbeddingService: Initialized embedding service
        
    Raises:
        ConfigurationError: If service cannot be configured
        EmbeddingServiceError: If service cannot be initialized
    """
    service = SemanticEmbeddingService(config)
    try:
        service.initialize()
        yield service
    finally:
        service.close()