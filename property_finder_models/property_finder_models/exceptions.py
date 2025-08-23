"""
Custom exceptions for the Property Finder ecosystem.

Provides a hierarchy of exceptions for different error scenarios.
"""


class PropertyFinderError(Exception):
    """Base exception for all Property Finder errors."""
    pass


class CommonEmbeddingsError(PropertyFinderError):
    """Base exception for embedding-related errors."""
    pass


class ConfigurationError(CommonEmbeddingsError):
    """Raised when configuration is invalid or missing."""
    pass


class DataLoadingError(CommonEmbeddingsError):
    """Raised when data cannot be loaded from source."""
    pass


class EmbeddingGenerationError(CommonEmbeddingsError):
    """Raised when embedding generation fails."""
    pass


class StorageError(CommonEmbeddingsError):
    """Raised when storage operations fail."""
    pass


class CorrelationError(CommonEmbeddingsError):
    """Raised when correlation between embeddings and source data fails."""
    pass


class ValidationError(CommonEmbeddingsError):
    """Raised when data validation fails."""
    pass


class MetadataError(CommonEmbeddingsError):
    """Raised when metadata operations fail."""
    pass


class ChunkingError(CommonEmbeddingsError):
    """Raised when text chunking fails."""
    pass


class ProviderError(CommonEmbeddingsError):
    """Raised when embedding provider operations fail."""
    pass