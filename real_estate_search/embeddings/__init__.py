"""
Embedding service for real estate search.

Provides query embedding generation capabilities for semantic search.
"""

from .models import EmbeddingConfig, EmbeddingProvider
from .service import QueryEmbeddingService
from .exceptions import (
    EmbeddingException,
    ConfigurationError,
    EmbeddingServiceError,
    EmbeddingGenerationError
)

__all__ = [
    # Models
    'EmbeddingConfig',
    'EmbeddingProvider',
    
    # Service
    'QueryEmbeddingService',
    
    # Exceptions
    'EmbeddingException',
    'ConfigurationError',
    'EmbeddingServiceError',
    'EmbeddingGenerationError'
]