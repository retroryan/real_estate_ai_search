"""Wikipedia API Client Models."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from property_finder_models import EnrichedWikipediaArticle, WikipediaSummary

from .models import PaginatedRequest, PaginatedResponse


class WikipediaArticleListRequest(PaginatedRequest):
    """Request model for Wikipedia articles list endpoint."""
    
    city: Optional[str] = Field(None, description="Filter by city name")
    state: Optional[str] = Field(None, description="Filter by state name")
    relevance_min: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum relevance score")
    sort_by: str = Field("relevance", description="Sort by field")
    include_embeddings: bool = Field(False, description="Include embedding data")
    collection_name: Optional[str] = Field(None, description="ChromaDB collection name")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class WikipediaSummaryListRequest(PaginatedRequest):
    """Request model for Wikipedia summaries list endpoint."""
    
    city: Optional[str] = Field(None, description="Filter by city name")
    state: Optional[str] = Field(None, description="Filter by state name")
    confidence_min: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum confidence score")
    include_key_topics: bool = Field(True, description="Include key topics")
    include_embeddings: bool = Field(False, description="Include embedding data")
    collection_name: Optional[str] = Field(None, description="ChromaDB collection name")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class WikipediaResponseMetadata(BaseModel):
    """Wikipedia API response metadata."""
    
    total_count: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total pages")
    has_next: bool = Field(..., description="Has next page")
    has_previous: bool = Field(..., description="Has previous page")
    timestamp: Optional[float] = Field(None, description="Response timestamp")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class WikipediaResponseLinks(BaseModel):
    """Wikipedia API pagination links."""
    
    self: str = Field(..., description="Current page URL")
    first: str = Field(..., description="First page URL") 
    last: str = Field(..., description="Last page URL")
    next: Optional[str] = Field(None, description="Next page URL")
    previous: Optional[str] = Field(None, description="Previous page URL")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class WikipediaArticleResponse(BaseModel):
    """Single Wikipedia article response."""
    
    data: EnrichedWikipediaArticle = Field(..., description="Enriched Wikipedia article data")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class WikipediaArticleListResponse(BaseModel):
    """Wikipedia articles list response with pagination."""
    
    data: List[EnrichedWikipediaArticle] = Field(..., description="List of Wikipedia articles")
    metadata: WikipediaResponseMetadata = Field(..., description="Response metadata")
    links: Optional[WikipediaResponseLinks] = Field(None, description="Pagination links")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class WikipediaSummaryResponse(BaseModel):
    """Single Wikipedia summary response."""
    
    data: WikipediaSummary = Field(..., description="Wikipedia summary data")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class WikipediaSummaryListResponse(BaseModel):
    """Wikipedia summaries list response with pagination."""
    
    data: List[WikipediaSummary] = Field(..., description="List of Wikipedia summaries")
    metadata: WikipediaResponseMetadata = Field(..., description="Response metadata")
    links: Optional[WikipediaResponseLinks] = Field(None, description="Pagination links")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")