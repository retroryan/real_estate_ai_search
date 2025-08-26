"""
Factory for creating embedding providers.

Clean, self-contained implementation with no dependencies on common_embeddings.
"""

from typing import Tuple, Any
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.google import GeminiEmbedding
from llama_index.embeddings.voyageai import VoyageEmbedding

# Try to import Cohere, but make it optional
try:
    from llama_index.embeddings.cohere import CohereEmbedding
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False

from data_pipeline.models.embedding_config import EmbeddingProvider, EmbeddingPipelineConfig
from data_pipeline.models.exceptions import ConfigurationError, ProviderError
import logging


logger = logging.getLogger(__name__)


class EmbeddingFactory:
    """
    Factory for creating and managing embedding providers.
    
    Simple, clean implementation that creates LlamaIndex embedding instances.
    """
    
    @staticmethod
    def create_provider(config: EmbeddingPipelineConfig) -> Tuple[Any, str]:
        """
        Create embedding provider and identifier from config.
        
        Args:
            config: EmbeddingPipelineConfig object
            
        Returns:
            Tuple of (embed_model, model_identifier)
            
        Raises:
            ConfigurationError: If configuration is invalid
            ProviderError: If provider creation fails
        """
        provider = config.embedding.provider
        logger.info(f"Creating embedding provider: {provider}")
        
        try:
            if provider == EmbeddingProvider.VOYAGE:
                embed_model = VoyageEmbedding(
                    api_key=config.embedding.voyage_api_key,
                    model_name=config.embedding.voyage_model
                )
                model_identifier = config.embedding.get_model_identifier()
                
            elif provider == EmbeddingProvider.OPENAI:
                embed_model = OpenAIEmbedding(
                    api_key=config.embedding.openai_api_key,
                    model=config.embedding.openai_model
                )
                model_identifier = config.embedding.get_model_identifier()
                
            elif provider == EmbeddingProvider.OLLAMA:
                embed_model = OllamaEmbedding(
                    model_name=config.embedding.ollama_model,
                    base_url=config.embedding.ollama_base_url
                )
                model_identifier = config.embedding.get_model_identifier()
                
            elif provider == EmbeddingProvider.GEMINI:
                embed_model = GeminiEmbedding(
                    api_key=config.embedding.gemini_api_key,
                    model_name=config.embedding.gemini_model
                )
                model_identifier = config.embedding.get_model_identifier()
                
            elif provider == EmbeddingProvider.COHERE:
                if not COHERE_AVAILABLE:
                    raise ConfigurationError("Cohere provider not available. Install llama-index-embeddings-cohere.")
                embed_model = CohereEmbedding(
                    api_key=config.embedding.cohere_api_key,
                    model_name=config.embedding.cohere_model
                )
                model_identifier = config.embedding.get_model_identifier()
                
            else:
                raise ConfigurationError(f"Unknown embedding provider: {provider}")
            
            logger.info(f"Successfully created {model_identifier}")
            return embed_model, model_identifier
            
        except Exception as e:
            logger.error(f"Failed to create embedding provider: {e}")
            raise ProviderError(provider.value, str(e), e)