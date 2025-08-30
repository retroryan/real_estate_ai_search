"""Embeddings generation module for Gold data.

Following DuckDB best practices:
- Reads embedding_text from Gold tables via SQL
- Generates embeddings via external providers
- Stores embeddings back in DuckDB
- Uses Pydantic only for API validation
"""

from squack_pipeline_v2.embeddings.generator import EmbeddingGenerator
from squack_pipeline_v2.embeddings.providers import (
    VoyageProvider,
    OpenAIProvider,
    EmbeddingProvider
)

__all__ = [
    "EmbeddingGenerator",
    "VoyageProvider", 
    "OpenAIProvider",
    "EmbeddingProvider"
]