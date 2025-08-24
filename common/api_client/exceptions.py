"""API Client Exceptions."""

from typing import Optional


class APIError(Exception):
    """Base exception for API client errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data


class ValidationError(APIError):
    """Raised when request or response validation fails."""
    pass


class NotFoundError(APIError):
    """Raised when a resource is not found (404)."""
    pass


class TimeoutError(APIError):
    """Raised when a request times out."""
    pass


class ServerError(APIError):
    """Raised when server returns 5xx error."""
    pass


class ClientError(APIError):
    """Raised when client makes invalid request (4xx error)."""
    pass