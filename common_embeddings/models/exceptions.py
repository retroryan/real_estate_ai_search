"""
Custom exceptions for the common embeddings module.

These exceptions provide clear error handling and debugging information.
"""


class CommonEmbeddingsError(Exception):
    """Base exception for all module errors."""
    pass


class ConfigurationError(CommonEmbeddingsError):
    """Raised when configuration is invalid or missing."""
    pass


class DataLoadingError(CommonEmbeddingsError):
    """Raised when data loading fails."""
    pass


class EmbeddingGenerationError(CommonEmbeddingsError):
    """Raised when embedding generation fails."""
    pass


class StorageError(CommonEmbeddingsError):
    """Raised when storage operations fail."""
    pass


class CorrelationError(CommonEmbeddingsError):
    """Raised when correlation operations fail."""
    pass


class ValidationError(CommonEmbeddingsError):
    """Raised when validation checks fail."""
    pass


class MetadataError(CommonEmbeddingsError):
    """Raised when metadata is invalid or incomplete."""
    
    def __init__(self, message: str, missing_fields: list = None):
        """
        Initialize metadata error.
        
        Args:
            message: Error message
            missing_fields: Optional list of missing field names
        """
        super().__init__(message)
        self.missing_fields = missing_fields or []


class ChunkingError(CommonEmbeddingsError):
    """Raised when text chunking fails."""
    pass


class ProviderError(CommonEmbeddingsError):
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