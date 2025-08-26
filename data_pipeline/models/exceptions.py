"""
Exception classes for the data pipeline embedding system.

Provides specific exception types for better error handling.
"""


class EmbeddingException(Exception):
    """Base exception for embedding-related errors."""
    pass


class ConfigurationError(EmbeddingException):
    """Raised when configuration is invalid or missing."""
    pass


class ProviderError(EmbeddingException):
    """Raised when embedding provider operations fail."""
    
    def __init__(self, provider: str, message: str, original_error: Exception = None):
        """
        Initialize provider error.
        
        Args:
            provider: Name of the provider that failed
            message: Error message
            original_error: Original exception if any
        """
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"Provider '{provider}' error: {message}")


class EmbeddingGenerationError(EmbeddingException):
    """Raised when embedding generation fails."""
    
    def __init__(self, text: str, message: str, original_error: Exception = None):
        """
        Initialize embedding generation error.
        
        Args:
            text: Text that failed to embed
            message: Error message
            original_error: Original exception if any
        """
        self.text = text[:100] + "..." if len(text) > 100 else text
        self.original_error = original_error
        super().__init__(f"Failed to generate embedding for text: {message}")