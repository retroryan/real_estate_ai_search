"""
Request schemas for API endpoints.

Defines Pydantic models for query parameters, filters, and request validation.
"""

from typing import Optional
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """
    Pagination parameters for list endpoints.
    
    Provides consistent pagination across all list endpoints.
    """
    
    page: int = Field(
        default=1,
        ge=1,
        le=1000,
        description="Page number (1-based)"
    )
    page_size: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Number of items per page"
    )
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit for database queries."""
        return self.page_size


class PropertyFilter(BaseModel):
    """
    Filter parameters for property endpoints.
    
    Allows filtering properties by city and other attributes.
    """
    
    city: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Filter by city name (case-insensitive)"
    )
    include_embeddings: bool = Field(
        default=False,
        description="Include embedding data in response"
    )


class NeighborhoodFilter(BaseModel):
    """
    Filter parameters for neighborhood endpoints.
    
    Allows filtering neighborhoods by city and other attributes.
    """
    
    city: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Filter by city name (case-insensitive)"
    )
    include_embeddings: bool = Field(
        default=False,
        description="Include embedding data in response"
    )