"""
Factory for creating embedding providers.

Adapted from wiki_embed/embedding/factory.py with enhanced provider support.
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

from ..models.config import Config
from ..models.enums import EmbeddingProvider
from ..models.interfaces import IEmbeddingProvider
from ..models.exceptions import ProviderError, ConfigurationError
from ..utils.logging import get_logger


logger = get_logger(__name__)


class EmbeddingFactory:
    """
    Factory for creating and managing embedding providers.
    
    Follows the factory pattern from wiki_embed with additional providers.
    """
    
    @staticmethod
    def create_provider(config: Config) -> Tuple[Any, str]:
        """
        Create embedding provider and identifier from config.
        
        Args:
            config: Configuration object
            
        Returns:
            Tuple of (embed_model, model_identifier)
            
        Raises:
            ConfigurationError: If configuration is invalid
            ProviderError: If provider creation fails
        """
        provider = config.embedding.provider
        logger.info(f"Creating embedding provider: {provider}")
        
        try:
            if provider == EmbeddingProvider.OLLAMA:
                embed_model = OllamaEmbedding(
                    model_name=config.embedding.ollama_model,
                    base_url=config.embedding.ollama_base_url
                )
                model_identifier = f"ollama_{config.embedding.ollama_model}"
                
            elif provider == EmbeddingProvider.OPENAI:
                embed_model = OpenAIEmbedding(
                    api_key=config.embedding.openai_api_key,
                    model=config.embedding.openai_model
                )
                model_identifier = f"openai_{config.embedding.openai_model.replace('-', '_')}"
                
            elif provider == EmbeddingProvider.GEMINI:
                embed_model = GeminiEmbedding(
                    api_key=config.embedding.gemini_api_key,
                    model_name=config.embedding.gemini_model
                )
                # Extract model name from path
                model_name = config.embedding.gemini_model.split('/')[-1]
                model_identifier = f"gemini_{model_name}"
                
            elif provider == EmbeddingProvider.VOYAGE:
                embed_model = VoyageEmbedding(
                    api_key=config.embedding.voyage_api_key,
                    model_name=config.embedding.voyage_model
                )
                model_identifier = f"voyage_{config.embedding.voyage_model}"
                
            elif provider == EmbeddingProvider.COHERE:
                if not COHERE_AVAILABLE:
                    raise ConfigurationError("Cohere embedding provider is not available. Install llama-index-embeddings-cohere.")
                embed_model = CohereEmbedding(
                    api_key=config.embedding.cohere_api_key,
                    model_name=config.embedding.cohere_model
                )
                model_identifier = f"cohere_{config.embedding.cohere_model.replace('-', '_')}"
                
            else:
                raise ConfigurationError(f"Unknown embedding provider: {provider}")
            
            logger.info(f"Successfully created {model_identifier}")
            return embed_model, model_identifier
            
        except Exception as e:
            logger.error(f"Failed to create embedding provider: {e}")
            raise ProviderError(provider.value, str(e), e)
    
    @staticmethod
    def get_model_identifier(config: Config) -> str:
        """
        Get model identifier without creating the provider.
        
        Args:
            config: Configuration object
            
        Returns:
            Model identifier string
        """
        provider = config.embedding.provider
        
        if provider == EmbeddingProvider.OLLAMA:
            return f"ollama_{config.embedding.ollama_model}"
        elif provider == EmbeddingProvider.OPENAI:
            return f"openai_{config.embedding.openai_model.replace('-', '_')}"
        elif provider == EmbeddingProvider.GEMINI:
            model_name = config.embedding.gemini_model.split('/')[-1]
            return f"gemini_{model_name}"
        elif provider == EmbeddingProvider.VOYAGE:
            return f"voyage_{config.embedding.voyage_model}"
        elif provider == EmbeddingProvider.COHERE:
            return f"cohere_{config.embedding.cohere_model.replace('-', '_')}"
        else:
            raise ConfigurationError(f"Unknown embedding provider: {provider}")
    
    @staticmethod
    def get_embedding_dimension(provider: EmbeddingProvider, model: str) -> int:
        """
        Get expected embedding dimension for a provider/model combination.
        
        Args:
            provider: Embedding provider
            model: Model name
            
        Returns:
            Expected embedding dimension
        """
        # Known dimensions for common models
        dimensions = {
            # Ollama models
            "nomic-embed-text": 768,
            "mxbai-embed-large": 1024,
            
            # OpenAI models
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            
            # Gemini models
            "embedding-001": 768,
            
            # Voyage models
            "voyage-3": 1024,
            "voyage-large-2": 1536,
            
            # Cohere models
            "embed-english-v3.0": 1024,
            "embed-multilingual-v3.0": 1024,
        }
        
        # Try to find dimension by model name
        for key, dim in dimensions.items():
            if key in model:
                return dim
        
        # Default dimensions by provider
        provider_defaults = {
            EmbeddingProvider.OLLAMA: 768,
            EmbeddingProvider.OPENAI: 1536,
            EmbeddingProvider.GEMINI: 768,
            EmbeddingProvider.VOYAGE: 1024,
            EmbeddingProvider.COHERE: 1024,
        }
        
        return provider_defaults.get(provider, 768)