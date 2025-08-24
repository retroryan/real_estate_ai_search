"""
Response schemas for API endpoints.

Defines Pydantic models for structured API responses with metadata and pagination.
"""

import time
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

from property_finder_models import (
    EnrichedProperty,
    EnrichedNeighborhood,
    EnrichedWikipediaArticle,
    WikipediaSummary
)


class ResponseMetadata(BaseModel):
    """
    Standard metadata for API responses.
    
    Provides consistent metadata across all API responses including
    pagination, timing, and data source information.
    """
    
    total_count: int = Field(
        ge=0,
        description="Total number of items available (not just in this page)"
    )
    page: int = Field(
        ge=1,
        description="Current page number"
    )
    page_size: int = Field(
        ge=1,
        description="Number of items per page"
    )
    total_pages: int = Field(
        ge=0,
        description="Total number of pages available"
    )
    timestamp: float = Field(
        default_factory=time.time,
        description="Response generation timestamp"
    )
    has_next: bool = Field(
        description="Whether there are more pages available"
    )
    has_previous: bool = Field(
        description="Whether there are previous pages available"
    )


class ResponseLinks(BaseModel):
    """
    Navigation links for paginated responses.
    
    Provides URLs for pagination navigation following REST conventions.
    """
    
    self: str = Field(description="URL for current page")
    first: str = Field(description="URL for first page")
    last: str = Field(description="URL for last page")
    next: Optional[str] = Field(default=None, description="URL for next page")
    previous: Optional[str] = Field(default=None, description="URL for previous page")


class PropertyResponse(BaseModel):
    """
    Single property response.
    
    Wraps an EnrichedProperty with additional API metadata.
    """
    
    data: EnrichedProperty = Field(description="Enriched property data")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the property"
    )


class PropertyListResponse(BaseModel):
    """
    Property list response with pagination.
    
    Provides paginated list of properties with metadata and navigation links.
    """
    
    data: List[EnrichedProperty] = Field(description="List of enriched properties")
    metadata: ResponseMetadata = Field(description="Response metadata and pagination info")
    links: Optional[ResponseLinks] = Field(default=None, description="Pagination navigation links")


class NeighborhoodResponse(BaseModel):
    """
    Single neighborhood response.
    
    Wraps an EnrichedNeighborhood with additional API metadata.
    """
    
    data: EnrichedNeighborhood = Field(description="Enriched neighborhood data")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the neighborhood"
    )


class NeighborhoodListResponse(BaseModel):
    """
    Neighborhood list response with pagination.
    
    Provides paginated list of neighborhoods with metadata and navigation links.
    """
    
    data: List[EnrichedNeighborhood] = Field(description="List of enriched neighborhoods")
    metadata: ResponseMetadata = Field(description="Response metadata and pagination info")
    links: Optional[ResponseLinks] = Field(default=None, description="Pagination navigation links")


class ErrorResponse(BaseModel):
    """
    Standard error response format.
    
    Provides consistent error structure across all API endpoints.
    """
    
    error: Dict[str, Any] = Field(description="Error details")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "INVALID_PARAMETER",
                    "message": "City 'InvalidCity' not found",
                    "status_code": 400,
                    "correlation_id": "abc123-def456",
                    "details": {
                        "parameter": "city",
                        "valid_values": ["San Francisco", "Park City", "Oakland"]
                    }
                }
            }
        }
    )


class WikipediaArticleResponse(BaseModel):
    """
    Single Wikipedia article response.
    
    Wraps an EnrichedWikipediaArticle with additional API metadata.
    """
    
    data: EnrichedWikipediaArticle = Field(description="Enriched Wikipedia article data")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the article"
    )


class WikipediaArticleListResponse(BaseModel):
    """
    Wikipedia article list response with pagination.
    
    Provides paginated list of Wikipedia articles with metadata and navigation links.
    """
    
    data: List[EnrichedWikipediaArticle] = Field(description="List of enriched Wikipedia articles")
    metadata: ResponseMetadata = Field(description="Response metadata and pagination info")
    links: Optional[ResponseLinks] = Field(default=None, description="Pagination navigation links")


class WikipediaSummaryResponse(BaseModel):
    """
    Single Wikipedia summary response.
    
    Wraps a WikipediaSummary with additional API metadata.
    """
    
    data: WikipediaSummary = Field(description="Wikipedia summary data")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the summary"
    )


class WikipediaSummaryListResponse(BaseModel):
    """
    Wikipedia summary list response with pagination.
    
    Provides paginated list of Wikipedia summaries with metadata and navigation links.
    """
    
    data: List[WikipediaSummary] = Field(description="List of Wikipedia summaries")
    metadata: ResponseMetadata = Field(description="Response metadata and pagination info")
    links: Optional[ResponseLinks] = Field(default=None, description="Pagination navigation links")