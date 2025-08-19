"""
FastAPI dependency injection utilities.
Provides clean dependency management for the API.
"""

from typing import Generator
from fastapi import Request, Depends
import uuid

from ..config.settings import Settings
from ..search.search_engine import PropertySearchEngine


def get_settings(request: Request) -> Settings:
    """
    Get application settings.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Settings instance
    """
    return request.app.state.settings


def get_search_engine(request: Request) -> PropertySearchEngine:
    """
    Get search engine instance.
    
    Args:
        request: FastAPI request object
        
    Returns:
        PropertySearchEngine instance
    """
    return request.app.state.search_engine


def get_request_id(request: Request) -> str:
    """
    Get or generate request ID.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Request ID string
    """
    if hasattr(request.state, 'request_id'):
        return request.state.request_id
    
    # Generate new ID if not present
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    return request_id


class RateLimiter:
    """
    Rate limiting dependency.
    Can be extended with Redis for distributed rate limiting.
    """
    
    def __init__(self, calls: int = 100, period: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            calls: Number of allowed calls
            period: Time period in seconds
        """
        self.calls = calls
        self.period = period
        self._storage = {}  # In-memory storage, replace with Redis in production
    
    async def __call__(self, request: Request) -> bool:
        """
        Check if request is rate limited.
        
        Args:
            request: FastAPI request
            
        Returns:
            True if allowed, raises HTTPException if rate limited
        """
        # Simple implementation - should use Redis in production
        client_id = request.client.host if request.client else "unknown"
        
        # For now, always allow (implement proper rate limiting with Redis)
        return True


# Create rate limiter instance
rate_limiter = RateLimiter(calls=100, period=60)