"""Factory for creating and managing embedding models."""

from typing import Tuple, Any
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.embeddings.google import GeminiEmbedding
from llama_index.embeddings.voyageai import VoyageEmbedding
from wiki_embed.models import Config, EmbeddingProvider


def create_embedding_model(config: Config) -> Tuple[Any, str]:
    """
    Create embedding model and identifier from config.
    
    Args:
        config: Configuration object
        
    Returns:
        Tuple of (embed_model, model_identifier)
        
    Note:
        All identifiers follow consistent pattern: provider_modelname
    """
    provider = config.embedding.provider
    
    if provider == EmbeddingProvider.OLLAMA:
        embed_model = OllamaEmbedding(
            model_name=config.embedding.ollama_model,
            base_url=config.embedding.ollama_base_url
        )
        model_identifier = f"ollama_{config.embedding.ollama_model}"
        
    elif provider == EmbeddingProvider.GEMINI:
        embed_model = GeminiEmbedding(
            api_key=config.embedding.gemini_api_key,
            model_name=config.embedding.gemini_model
        )
        # Extract model name from path (e.g., "models/embedding-001" -> "embedding-001")
        model_name = config.embedding.gemini_model.split('/')[-1]
        model_identifier = f"gemini_{model_name}"
        
    elif provider == EmbeddingProvider.VOYAGE:
        embed_model = VoyageEmbedding(
            api_key=config.embedding.voyage_api_key,
            model_name=config.embedding.voyage_model
        )
        model_identifier = f"voyage_{config.embedding.voyage_model}"
        
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")
    
    return embed_model, model_identifier


def get_model_identifier(config: Config) -> str:
    """
    Get model identifier without creating the model.
    
    Args:
        config: Configuration object
        
    Returns:
        Model identifier string
    """
    provider = config.embedding.provider
    
    if provider == EmbeddingProvider.OLLAMA:
        return f"ollama_{config.embedding.ollama_model}"
    elif provider == EmbeddingProvider.GEMINI:
        model_name = config.embedding.gemini_model.split('/')[-1]
        return f"gemini_{model_name}"
    elif provider == EmbeddingProvider.VOYAGE:
        return f"voyage_{config.embedding.voyage_model}"
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")


def get_model_display_name(config: Config) -> str:
    """
    Get model name for display in CLI output.
    
    Args:
        config: Configuration object
        
    Returns:
        Display name string
    """
    return get_model_identifier(config)