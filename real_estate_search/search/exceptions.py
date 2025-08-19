"""
Custom exceptions for search operations.
Provides typed error handling for search-related failures.
"""

from typing import Optional, Any


class SearchError(Exception):
    """Base exception for search errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Any] = None
    ):
        """
        Initialize the search exception.
        
        Args:
            message: Error message
            error_code: Error code for categorization
            details: Additional error details
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


class QueryValidationError(SearchError):
    """Raised when search query validation fails."""
    pass


class AggregationError(SearchError):
    """Raised when aggregation processing fails."""
    pass


class ResultProcessingError(SearchError):
    """Raised when result processing fails."""
    pass


class SearchTimeoutError(SearchError):
    """Raised when search operation times out."""
    pass


class CircuitBreakerError(SearchError):
    """Raised when circuit breaker is open due to failures."""
    pass