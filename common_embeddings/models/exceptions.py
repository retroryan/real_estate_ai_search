"""
Custom exceptions specific to embeddings processing.

Core exceptions (ConfigurationError, DataLoadingError, StorageError, 
ValidationError, MetadataError) are imported from common.
"""


class EmbeddingGenerationError(Exception):
    """Raised when embedding generation fails."""
    pass


class ChunkingError(Exception):
    """Raised when text chunking fails."""
    pass


class ProviderError(Exception):
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