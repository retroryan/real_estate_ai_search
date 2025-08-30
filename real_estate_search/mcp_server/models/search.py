"""Search request and response models using Pydantic."""

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


class PropertyFilter(BaseModel):
    """Property search filters."""
    
    model_config = ConfigDict(extra='forbid')
    
    property_type: Optional[str] = Field(None, description="Property type filter")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price")
    min_bedrooms: Optional[int] = Field(None, ge=0, description="Minimum bedrooms")
    max_bedrooms: Optional[int] = Field(None, ge=0, description="Maximum bedrooms")
    min_bathrooms: Optional[float] = Field(None, ge=0, description="Minimum bathrooms")
    max_bathrooms: Optional[float] = Field(None, ge=0, description="Maximum bathrooms")
    min_square_feet: Optional[int] = Field(None, ge=0, description="Minimum square feet")
    max_square_feet: Optional[int] = Field(None, ge=0, description="Maximum square feet")
    
    # Location filters
    city: Optional[str] = Field(None, description="City filter")
    state: Optional[str] = Field(None, description="State filter")
    zip_code: Optional[str] = Field(None, description="ZIP code filter")
    neighborhood_id: Optional[str] = Field(None, description="Neighborhood ID filter")
    
    # Geographic filter
    center_lat: Optional[float] = Field(None, description="Center latitude for geo search")
    center_lon: Optional[float] = Field(None, description="Center longitude for geo search")
    radius_km: Optional[float] = Field(None, gt=0, description="Search radius in kilometers")
    
    # Status filters
    status: Optional[str] = Field(None, description="Listing status filter")
    max_days_on_market: Optional[int] = Field(None, ge=0, description="Maximum days on market")
    
    @field_validator('max_price')
    @classmethod
    def validate_max_price(cls, v: Optional[float], info) -> Optional[float]:
        if v is not None and 'min_price' in info.data:
            min_price = info.data.get('min_price')
            if min_price is not None and v < min_price:
                raise ValueError(f"max_price ({v}) must be >= min_price ({min_price})")
        return v
    
    @field_validator('max_bedrooms')
    @classmethod
    def validate_max_bedrooms(cls, v: Optional[int], info) -> Optional[int]:
        if v is not None and 'min_bedrooms' in info.data:
            min_bedrooms = info.data.get('min_bedrooms')
            if min_bedrooms is not None and v < min_bedrooms:
                raise ValueError(f"max_bedrooms ({v}) must be >= min_bedrooms ({min_bedrooms})")
        return v


class PropertySearchRequest(BaseModel):
    """Property search request."""
    
    model_config = ConfigDict(extra='forbid')
    
    query: str = Field(..., min_length=1, description="Natural language search query")
    filters: Optional[PropertyFilter] = Field(None, description="Property filters")
    size: int = Field(default=20, ge=1, le=100, description="Number of results")
    from_: int = Field(default=0, ge=0, alias="from", description="Pagination offset")
    
    # Search options
    search_type: Literal["semantic", "text", "hybrid"] = Field(
        default="hybrid",
        description="Search type"
    )
    include_highlights: bool = Field(default=True, description="Include highlights")
    include_aggregations: bool = Field(default=False, description="Include aggregations")
    explain: bool = Field(default=False, description="Include score explanation")
    
    # Sorting
    sort_by: Optional[Literal["relevance", "price", "date", "bedrooms"]] = Field(
        None,
        description="Sort field"
    )
    sort_order: Literal["asc", "desc"] = Field(default="desc", description="Sort order")


class WikipediaSearchRequest(BaseModel):
    """Wikipedia search request."""
    
    model_config = ConfigDict(extra='forbid')
    
    query: str = Field(..., min_length=1, description="Natural language search query")
    size: int = Field(default=20, ge=1, le=100, description="Number of results")
    from_: int = Field(default=0, ge=0, alias="from", description="Pagination offset")
    
    # Search options
    search_type: Literal["semantic", "text", "hybrid"] = Field(
        default="hybrid",
        description="Search type"
    )
    search_in: Literal["full", "summaries", "chunks"] = Field(
        default="full",
        description="What to search in"
    )
    include_highlights: bool = Field(default=True, description="Include highlights")
    explain: bool = Field(default=False, description="Include score explanation")
    
    # Filters
    city: Optional[str] = Field(None, description="Filter by city")
    state: Optional[str] = Field(None, description="Filter by state")
    categories: Optional[List[str]] = Field(None, description="Filter by categories")
    min_relevance: Optional[float] = Field(None, ge=0, le=1, description="Minimum relevance")


class SearchMetadata(BaseModel):
    """Search result metadata."""
    
    model_config = ConfigDict(extra='forbid')
    
    total_hits: int = Field(..., ge=0, description="Total number of hits")
    returned_hits: int = Field(..., ge=0, description="Number of returned hits")
    max_score: Optional[float] = Field(None, description="Maximum relevance score")
    execution_time_ms: int = Field(..., ge=0, description="Execution time in milliseconds")
    query_type: str = Field(..., description="Type of query executed")


class Aggregation(BaseModel):
    """Search aggregation result."""
    
    model_config = ConfigDict(extra='forbid')
    
    name: str = Field(..., description="Aggregation name")
    type: str = Field(..., description="Aggregation type")
    buckets: List[Dict[str, Any]] = Field(default_factory=list, description="Aggregation buckets")


class PropertySearchResponse(BaseModel):
    """Property search response."""
    
    model_config = ConfigDict(extra='forbid')
    
    metadata: SearchMetadata = Field(..., description="Search metadata")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Search results")
    aggregations: Optional[List[Aggregation]] = Field(None, description="Aggregations")
    
    # Request echo
    original_query: str = Field(..., description="Original search query")
    applied_filters: Optional[PropertyFilter] = Field(None, description="Applied filters")


class WikipediaSearchResponse(BaseModel):
    """Wikipedia search response."""
    
    model_config = ConfigDict(extra='forbid')
    
    metadata: SearchMetadata = Field(..., description="Search metadata")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Search results")
    
    # Request echo
    original_query: str = Field(..., description="Original search query")
    search_in: str = Field(..., description="What was searched")


class NaturalLanguageSearchRequest(BaseModel):
    """Natural language semantic search request."""
    
    model_config = ConfigDict(extra='forbid')
    
    query: str = Field(..., min_length=1, description="Natural language search query")
    size: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    search_type: Literal["semantic", "comparison", "examples"] = Field(
        default="semantic",
        description="Type of natural language search"
    )


class NaturalLanguageSearchResponse(BaseModel):
    """Natural language semantic search response."""
    
    model_config = ConfigDict(extra='forbid')
    
    query_name: str = Field(..., description="Name of the query executed")
    query_description: str = Field(..., description="Description of what was searched")
    execution_time_ms: int = Field(..., ge=0, description="Total execution time")
    total_hits: int = Field(..., ge=0, description="Total number of matches")
    returned_hits: int = Field(..., ge=0, description="Number of results returned")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Search results")
    search_features: List[str] = Field(default_factory=list, description="Search features used")
    original_query: str = Field(..., description="Original search query")


class SemanticComparisonResponse(BaseModel):
    """Response for semantic vs keyword comparison."""
    
    model_config = ConfigDict(extra='forbid')
    
    query: str = Field(..., description="Query that was compared")
    semantic: Dict[str, Any] = Field(..., description="Semantic search results")
    keyword: Dict[str, Any] = Field(..., description="Keyword search results")
    comparison: Dict[str, Any] = Field(..., description="Comparison metrics")
    execution_time_ms: int = Field(..., ge=0, description="Total execution time")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    
    model_config = ConfigDict(extra='forbid')
    
    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    services: Dict[str, Dict[str, Any]] = Field(..., description="Service statuses")
    version: str = Field(..., description="Server version")
    
    
class ErrorResponse(BaseModel):
    """Error response."""
    
    model_config = ConfigDict(extra='forbid')
    
    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")