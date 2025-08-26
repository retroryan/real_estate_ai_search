"""
Custom exceptions for property indexer.
Provides typed error handling with error codes.
"""

from typing import Optional, Any
from .enums import ErrorCode


class PropertyIndexerError(Exception):
    """Base exception for property indexer errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[ErrorCode] = None,
        details: Optional[Any] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Error message.
            error_code: Error code from ErrorCode enum.
            details: Additional error details.
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details
    
    def __str__(self) -> str:
        """String representation of the error."""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class IndexCreationError(PropertyIndexerError):
    """Raised when index creation fails."""
    pass


class BulkIndexingError(PropertyIndexerError):
    """Raised when bulk indexing operations fail."""
    pass


class ConnectionError(PropertyIndexerError):
    """Raised when connection to Elasticsearch fails."""
    pass


class ValidationError(PropertyIndexerError):
    """Raised when data validation fails."""
    pass


class ConfigurationError(PropertyIndexerError):
    """Raised when configuration is invalid."""
    pass


class ElasticsearchIndexError(PropertyIndexerError):
    """Raised when Elasticsearch index operations fail."""
    pass