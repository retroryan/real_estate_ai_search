"""Re-export configuration models for vector embeddings"""
# Re-export the Pydantic models from config for backward compatibility
# This allows existing code to continue importing from vectors.models
from ..config.models import (
    VectorIndexConfig,
    EmbeddingConfig,
    SearchConfig,
    VoyageModelConfig,
    OllamaModelConfig,
    OpenAIModelConfig,
    GeminiModelConfig
)

__all__ = [
    'VectorIndexConfig',
    'EmbeddingConfig', 
    'SearchConfig',
    'VoyageModelConfig',
    'OllamaModelConfig',
    'OpenAIModelConfig',
    'GeminiModelConfig'
]