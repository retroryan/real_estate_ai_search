"""
Custom exceptions for Elasticsearch indexing operations.
"""

from typing import Optional, Any
from .enums import ErrorCode


class ElasticsearchIndexError(Exception):
    """Base exception for Elasticsearch index operations."""
    
    def __init__(
        self,
        error_code: Optional[ErrorCode] = None,
        message: str = "",
        details: Optional[Any] = None
    ):
        """
        Initialize the exception.
        
        Args:
            error_code: Error code from ErrorCode enum.
            message: Error message.
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


class IndexCreationError(ElasticsearchIndexError):
    """Exception raised when index creation fails."""
    pass


class IndexMappingError(ElasticsearchIndexError):
    """Exception raised when mapping operations fail."""
    pass


class DocumentIndexError(ElasticsearchIndexError):
    """Exception raised when document indexing fails."""
    pass


class BulkIndexError(ElasticsearchIndexError):
    """Exception raised when bulk indexing operations fail."""
    pass


class IndexNotFoundError(ElasticsearchIndexError):
    """Exception raised when an index is not found."""
    pass


class IndexAlreadyExistsError(ElasticsearchIndexError):
    """Exception raised when trying to create an index that already exists."""
    pass