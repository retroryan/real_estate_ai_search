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


class WikipediaArticleFilter(BaseModel):
    """
    Filter parameters for Wikipedia article endpoints.
    
    Allows filtering articles by location, relevance, and sorting options.
    """
    
    city: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Filter by city name (case-insensitive)"
    )
    state: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Filter by state name (case-insensitive)"
    )
    relevance_min: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score (0.0 to 1.0)"
    )
    sort_by: Optional[str] = Field(
        default="relevance",
        regex="^(relevance|title|page_id)$",
        description="Sort articles by: relevance, title, or page_id"
    )
    include_embeddings: bool = Field(
        default=False,
        description="Include embedding data in response"
    )


class WikipediaSummaryFilter(BaseModel):
    """
    Filter parameters for Wikipedia summary endpoints.
    
    Allows filtering summaries by location and confidence thresholds.
    """
    
    city: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Filter by city name (case-insensitive)"
    )
    state: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Filter by state name (case-insensitive)"
    )
    confidence_min: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score (0.0 to 1.0)"
    )
    include_key_topics: bool = Field(
        default=True,
        description="Include key topics in response"
    )
    include_embeddings: bool = Field(
        default=False,
        description="Include embedding data in response"
    )