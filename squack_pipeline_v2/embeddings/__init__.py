"""Embeddings generation module.

Following DuckDB best practices:
- Embeddings now generated in Silver layer during transformation
- Providers available for Silver layer to use
- Uses Pydantic for validation
"""

# EmbeddingGenerator removed - embeddings now generated in Silver layer
from squack_pipeline_v2.embeddings.providers import (
    VoyageProvider,
    OpenAIProvider,
    EmbeddingProvider,
    create_provider
)

__all__ = [
    "VoyageProvider", 
    "OpenAIProvider",
    "EmbeddingProvider",
    "create_provider"
]