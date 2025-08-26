"""
Custom exceptions for the embeddings module.

Provides a hierarchy of exceptions for different error scenarios.
"""


class PropertyFinderError(Exception):
    """Base exception for all Property Finder errors."""
    pass


class ConfigurationError(PropertyFinderError):
    """Raised when configuration is invalid or missing."""
    pass


class DataLoadingError(PropertyFinderError):
    """Raised when data cannot be loaded from source."""
    pass


class StorageError(PropertyFinderError):
    """Raised when storage operations fail."""
    pass


class ValidationError(PropertyFinderError):
    """Raised when data validation fails."""
    pass


class MetadataError(PropertyFinderError):
    """Raised when metadata operations fail."""
    pass


class EmbeddingGenerationError(PropertyFinderError):
    """Raised when embedding generation fails."""
    pass


class ChunkingError(PropertyFinderError):
    """Raised when text chunking fails."""
    pass


class ProviderError(PropertyFinderError):
    """Raised when embedding provider operations fail."""
    
    def __init__(self, provider: str, message: str, original_error: Exception = None):
        """
        Initialize provider error.
        
        Args:
            provider: Name of the provider
            message: Error message
            original_error: Original exception if any
        """
        super().__init__(f"Provider '{provider}' error: {message}")
        self.provider = provider
        self.original_error = original_error