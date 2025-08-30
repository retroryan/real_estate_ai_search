"""Base transformer with embedding generation capabilities.

This module provides a base class for transformers that need to generate
embeddings for their data. It integrates with the existing embedding service
and provides clean, entity-agnostic embedding functionality.
"""

from typing import Optional, List
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from squack_pipeline.utils.logging import PipelineLogger
from squack_pipeline.config.settings import PipelineSettings
from real_estate_search.embeddings.service import QueryEmbeddingService
from real_estate_search.embeddings.models import EmbeddingConfig as ServiceEmbeddingConfig


class BaseEmbeddingTransformer:
    """Base transformer with embedding generation capabilities.
    
    This class provides:
    - Embedding service initialization
    - Safe embedding generation with error handling
    - Clean resource management
    
    Entity-specific transformers extend this to add embeddings
    to their documents during transformation.
    """
    
    def __init__(self):
        """Initialize the base embedding transformer."""
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.embedding_service: Optional[QueryEmbeddingService] = None
        self.service_config: Optional[ServiceEmbeddingConfig] = None
        
        # Load pipeline settings to get embedding configuration
        self.pipeline_settings = PipelineSettings()
        self._initialize_embedding_service()
    
    def _initialize_embedding_service(self) -> None:
        """Initialize the embedding service if API key is available."""
        try:
            # Get the embedding configuration from pipeline settings
            embedding_config = self.pipeline_settings.embedding
            
            # Check which provider is configured and get the appropriate API key
            api_key = None
            model_name = None
            
            if embedding_config.provider == "voyage":
                api_key = embedding_config.voyage_api_key
                model_name = embedding_config.voyage_model
            elif embedding_config.provider == "openai":
                api_key = embedding_config.openai_api_key
                model_name = embedding_config.openai_model
            elif embedding_config.provider == "gemini":
                api_key = embedding_config.gemini_api_key
                model_name = embedding_config.gemini_model
            elif embedding_config.provider == "ollama":
                # Ollama doesn't need API key
                api_key = "dummy"  # Service expects a key but ollama doesn't use it
                model_name = embedding_config.ollama_model
            
            if not api_key:
                self.logger.info(f"No API key found for {embedding_config.provider} - embeddings will not be generated")
                return
            
            # Create service config for the embedding service
            self.service_config = ServiceEmbeddingConfig(
                api_key=api_key,
                model_name=model_name,
                dimension=1024  # Default for voyage-3
            )
            
            # Initialize the service
            self.embedding_service = QueryEmbeddingService(config=self.service_config)
            self.embedding_service.initialize()
            
            self.logger.info(
                f"Embedding service initialized with {embedding_config.provider}:{model_name}"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize embedding service: {e}")
            self.embedding_service = None
            self.service_config = None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception)),
        before_sleep=lambda retry_state: None  # Avoid logging retry attempts by default
    )
    def _generate_embedding_with_retry(self, text: str) -> List[float]:
        """Generate embedding with retry logic for transient failures."""
        if not self.embedding_service:
            raise RuntimeError("Embedding service not initialized")
        
        # Generate embedding using the service
        return self.embedding_service.embed_query(text)
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for the given text.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            Embedding vector as list of floats, or None if generation fails
        """
        if not self.embedding_service:
            return None
        
        if not text or not text.strip():
            return None
        
        try:
            # Use retry-enabled method
            embedding = self._generate_embedding_with_retry(text)
            return embedding
            
        except Exception as e:
            self.logger.error(f"Failed to generate embedding after retries: {e}")
            return None
    
    def add_embedding_fields(self, doc: dict, text: str) -> dict:
        """Add embedding fields to a document.
        
        Args:
            doc: Document to add embedding fields to
            text: Text to generate embedding from
            
        Returns:
            Document with embedding fields added (if embedding was generated)
        """
        if not self.embedding_service or not self.service_config:
            return doc
        
        embedding = self.generate_embedding(text)
        
        if embedding:
            doc['embedding'] = embedding
            doc['embedding_model'] = self.service_config.model_name
            doc['embedding_dimension'] = len(embedding)
        
        return doc
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.embedding_service:
            try:
                self.embedding_service.close()
            except Exception as e:
                self.logger.warning(f"Error during embedding service cleanup: {e}")
            finally:
                self.embedding_service = None
                self.service_config = None
    
    def __del__(self):
        """Ensure cleanup on deletion."""
        self.cleanup()