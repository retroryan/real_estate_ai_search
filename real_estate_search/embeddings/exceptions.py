"""
Exception classes for the embedding service.

Provides specific exception types for better error handling and debugging.
"""


class EmbeddingException(Exception):
    """Base exception for embedding-related errors."""
    pass


class ConfigurationError(EmbeddingException):
    """Raised when configuration is invalid or missing."""
    pass


class EmbeddingServiceError(EmbeddingException):
    """Raised when embedding service operations fail."""
    
    def __init__(self, message: str, original_error: Exception = None):
        """
        Initialize service error.
        
        Args:
            message: Error message
            original_error: Original exception if any
        """
        self.original_error = original_error
        super().__init__(message)


class EmbeddingGenerationError(EmbeddingException):
    """Raised when embedding generation fails."""
    
    def __init__(self, query: str, message: str, original_error: Exception = None):
        """
        Initialize embedding generation error.
        
        Args:
            query: Query text that failed to embed
            message: Error message
            original_error: Original exception if any
        """
        self.query = query[:100] + "..." if len(query) > 100 else query
        self.original_error = original_error
        super().__init__(f"Failed to generate embedding for query '{self.query}': {message}")