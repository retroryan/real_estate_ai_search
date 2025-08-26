"""Embedding factory for creating LlamaIndex embedding providers."""

from typing import Any

from llama_index.core.embeddings import BaseEmbedding

from squack_pipeline.config.settings import EmbeddingConfig, EmbeddingProvider
from squack_pipeline.utils.logging import PipelineLogger


class EmbeddingFactory:
    """Factory for creating embedding providers following common_embeddings patterns."""
    
    @staticmethod
    def create_from_config(config: EmbeddingConfig) -> BaseEmbedding:
        """Create embedding provider from configuration."""
        logger = PipelineLogger.get_logger("EmbeddingFactory")
        
        if config.provider == EmbeddingProvider.VOYAGE:
            return EmbeddingFactory._create_voyage_embedding(config, logger)
        elif config.provider == EmbeddingProvider.OPENAI:
            return EmbeddingFactory._create_openai_embedding(config, logger)
        elif config.provider == EmbeddingProvider.OLLAMA:
            return EmbeddingFactory._create_ollama_embedding(config, logger)
        elif config.provider == EmbeddingProvider.GEMINI:
            return EmbeddingFactory._create_gemini_embedding(config, logger)
        elif config.provider == EmbeddingProvider.MOCK:
            return EmbeddingFactory._create_mock_embedding(config, logger)
        else:
            raise ValueError(f"Unsupported embedding provider: {config.provider}")
    
    @staticmethod
    def _create_voyage_embedding(config: EmbeddingConfig, logger: Any) -> BaseEmbedding:
        """Create Voyage AI embedding provider."""
        try:
            from llama_index.embeddings.voyageai import VoyageEmbedding
            
            logger.info(f"Creating Voyage AI embedding with model: {config.voyage_model}")
            
            return VoyageEmbedding(
                model_name=config.voyage_model,
                voyage_api_key=config.voyage_api_key
            )
        except ImportError as e:
            raise ImportError(
                "VoyageAI embedding provider not available. "
                "Install with: pip install llama-index-embeddings-voyageai"
            ) from e
    
    @staticmethod
    def _create_openai_embedding(config: EmbeddingConfig, logger: Any) -> BaseEmbedding:
        """Create OpenAI embedding provider."""
        try:
            from llama_index.embeddings.openai import OpenAIEmbedding
            
            logger.info(f"Creating OpenAI embedding with model: {config.openai_model}")
            
            return OpenAIEmbedding(
                model=config.openai_model,
                api_key=config.openai_api_key
            )
        except ImportError as e:
            raise ImportError(
                "OpenAI embedding provider not available. "
                "Install with: pip install llama-index-embeddings-openai"
            ) from e
    
    @staticmethod
    def _create_ollama_embedding(config: EmbeddingConfig, logger: Any) -> BaseEmbedding:
        """Create Ollama embedding provider."""
        try:
            from llama_index.embeddings.ollama import OllamaEmbedding
            
            logger.info(f"Creating Ollama embedding with model: {config.ollama_model}")
            
            return OllamaEmbedding(
                model_name=config.ollama_model,
                base_url=config.ollama_base_url
            )
        except ImportError as e:
            raise ImportError(
                "Ollama embedding provider not available. "
                "Install with: pip install llama-index-embeddings-ollama"
            ) from e
    
    @staticmethod
    def _create_gemini_embedding(config: EmbeddingConfig, logger: Any) -> BaseEmbedding:
        """Create Gemini embedding provider."""
        try:
            from llama_index.embeddings.gemini import GeminiEmbedding
            
            logger.info(f"Creating Gemini embedding with model: {config.gemini_model}")
            
            return GeminiEmbedding(
                model_name=config.gemini_model,
                api_key=config.gemini_api_key
            )
        except ImportError as e:
            raise ImportError(
                "Gemini embedding provider not available. "
                "Install with: pip install llama-index-embeddings-gemini"  
            ) from e
    
    @staticmethod
    def _create_mock_embedding(config: EmbeddingConfig, logger: Any) -> BaseEmbedding:
        """Create mock embedding provider for testing."""
        from llama_index.core.embeddings import MockEmbedding
        
        logger.info(f"Creating mock embedding with dimension: {config.mock_dimension}")
        
        return MockEmbedding(embed_dim=config.mock_dimension)
    
    @staticmethod 
    def get_embedding_dimension(provider: EmbeddingProvider, model: str) -> int:
        """Get embedding dimension for a provider/model combination."""
        # Voyage AI dimensions
        if provider == EmbeddingProvider.VOYAGE:
            voyage_dimensions = {
                "voyage-3": 1024,
                "voyage-large-2": 1536, 
                "voyage-code-2": 1536,
                "voyage-2": 1024
            }
            return voyage_dimensions.get(model, 1024)
        
        # OpenAI dimensions
        elif provider == EmbeddingProvider.OPENAI:
            openai_dimensions = {
                "text-embedding-3-small": 1536,
                "text-embedding-3-large": 3072,
                "text-embedding-ada-002": 1536
            }
            return openai_dimensions.get(model, 1536)
        
        # Ollama dimensions (model-specific)
        elif provider == EmbeddingProvider.OLLAMA:
            ollama_dimensions = {
                "nomic-embed-text": 768,
                "mxbai-embed-large": 1024,
                "all-minilm": 384
            }
            return ollama_dimensions.get(model, 768)
        
        # Gemini dimensions
        elif provider == EmbeddingProvider.GEMINI:
            return 768
        
        # Default fallback
        return 1024