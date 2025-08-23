"""
API request and response models for REST endpoints.

Provides models for pagination, filtering, and structured responses.
"""

import time
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """
    Standard pagination parameters for list endpoints.
    """
    
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate database offset from page number."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Database limit (same as page_size)."""
        return self.page_size


class PropertyFilter(BaseModel):
    """
    Filter parameters for property endpoints.
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
    min_price: Optional[float] = Field(
        default=None,
        ge=0,
        description="Minimum property price"
    )
    max_price: Optional[float] = Field(
        default=None,
        ge=0,
        description="Maximum property price"
    )
    min_bedrooms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minimum number of bedrooms"
    )
    property_type: Optional[str] = Field(
        default=None,
        description="Property type filter"
    )
    include_embeddings: bool = Field(
        default=False,
        description="Include embedding data in response"
    )


class NeighborhoodFilter(BaseModel):
    """
    Filter parameters for neighborhood endpoints.
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
        pattern="^(relevance|title|page_id)$",
        description="Sort articles by: relevance, title, or page_id"
    )
    include_embeddings: bool = Field(
        default=False,
        description="Include embedding data in response"
    )


class WikipediaSummaryFilter(BaseModel):
    """
    Filter parameters for Wikipedia summary endpoints.
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


class ResponseMetadata(BaseModel):
    """
    Standard metadata for API responses.
    """
    
    timestamp: float = Field(
        default_factory=time.time,
        description="Unix timestamp of response"
    )
    total_count: int = Field(description="Total number of items available")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    page_count: int = Field(description="Total number of pages")
    
    @classmethod
    def from_pagination(
        cls,
        total_count: int,
        page: int,
        page_size: int
    ) -> "ResponseMetadata":
        """Create metadata from pagination parameters."""
        page_count = (total_count + page_size - 1) // page_size
        return cls(
            total_count=total_count,
            page=page,
            page_size=page_size,
            page_count=page_count
        )


class ResponseLinks(BaseModel):
    """
    HATEOAS links for API navigation.
    """
    
    self: str = Field(description="Link to current page")
    first: Optional[str] = Field(None, description="Link to first page")
    last: Optional[str] = Field(None, description="Link to last page")
    next: Optional[str] = Field(None, description="Link to next page")
    prev: Optional[str] = Field(None, description="Link to previous page")


class PropertyResponse(BaseModel):
    """Single property response."""
    
    data: Any = Field(description="Enriched property data")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class PropertyListResponse(BaseModel):
    """Property list response with pagination."""
    
    data: List[Any] = Field(description="List of enriched properties")
    metadata: ResponseMetadata = Field(description="Response metadata and pagination info")
    links: Optional[ResponseLinks] = Field(None, description="Pagination navigation links")


class NeighborhoodResponse(BaseModel):
    """Single neighborhood response."""
    
    data: Any = Field(description="Enriched neighborhood data")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class NeighborhoodListResponse(BaseModel):
    """Neighborhood list response with pagination."""
    
    data: List[Any] = Field(description="List of enriched neighborhoods")
    metadata: ResponseMetadata = Field(description="Response metadata and pagination info")
    links: Optional[ResponseLinks] = Field(None, description="Pagination navigation links")


class WikipediaArticleResponse(BaseModel):
    """Single Wikipedia article response."""
    
    data: Any = Field(description="Enriched Wikipedia article data")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class WikipediaArticleListResponse(BaseModel):
    """Wikipedia article list response with pagination."""
    
    data: List[Any] = Field(description="List of enriched Wikipedia articles")
    metadata: ResponseMetadata = Field(description="Response metadata and pagination info")
    links: Optional[ResponseLinks] = Field(None, description="Pagination navigation links")


class WikipediaSummaryResponse(BaseModel):
    """Single Wikipedia summary response."""
    
    data: Any = Field(description="Wikipedia summary data")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class WikipediaSummaryListResponse(BaseModel):
    """Wikipedia summary list response with pagination."""
    
    data: List[Any] = Field(description="List of Wikipedia summaries")
    metadata: ResponseMetadata = Field(description="Response metadata and pagination info")
    links: Optional[ResponseLinks] = Field(None, description="Pagination navigation links")


class ErrorResponse(BaseModel):
    """
    Standard error response format.
    """
    
    error: str = Field(description="Error type or code")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    status_code: int = Field(description="HTTP status code")
    timestamp: float = Field(
        default_factory=time.time,
        description="Unix timestamp of error"
    )
    correlation_id: Optional[str] = Field(
        None,
        description="Request correlation ID for debugging"
    )