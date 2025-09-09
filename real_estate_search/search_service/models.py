"""
Pydantic models for search service requests and responses.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

from ..models.wikipedia import WikipediaArticle


class SearchError(BaseModel):
    """Error response model."""
    
    error_type: str = Field(description="Type of error")
    message: str = Field(description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")


class GeoLocation(BaseModel):
    """Geographic location coordinates."""
    
    lat: float = Field(description="Latitude")
    lon: float = Field(description="Longitude")


class PropertyType(str, Enum):
    """Property type enumeration."""
    
    SINGLE_FAMILY = "single_family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    MULTI_FAMILY = "multi_family"
    APARTMENT = "apartment"
    LAND = "land"
    OTHER = "other"


class PropertyFilter(BaseModel):
    """Filters for property search."""
    
    property_types: Optional[List[PropertyType]] = Field(default=None, description="Property types to filter by")
    min_price: Optional[float] = Field(default=None, description="Minimum price")
    max_price: Optional[float] = Field(default=None, description="Maximum price")
    min_bedrooms: Optional[int] = Field(default=None, description="Minimum bedrooms")
    max_bedrooms: Optional[int] = Field(default=None, description="Maximum bedrooms")
    min_bathrooms: Optional[float] = Field(default=None, description="Minimum bathrooms")
    max_bathrooms: Optional[float] = Field(default=None, description="Maximum bathrooms")
    min_square_feet: Optional[int] = Field(default=None, description="Minimum square feet")
    max_square_feet: Optional[int] = Field(default=None, description="Maximum square feet")


class PropertySearchRequest(BaseModel):
    """Request model for property search."""
    
    model_config = ConfigDict(extra='forbid')
    
    query: Optional[str] = Field(default=None, description="Text search query")
    filters: Optional[PropertyFilter] = Field(default=None, description="Property filters")
    geo_location: Optional[GeoLocation] = Field(default=None, description="Center point for geo search")
    geo_distance_km: Optional[float] = Field(default=None, description="Search radius in kilometers")
    reference_property_id: Optional[str] = Field(default=None, description="Property ID for similarity search")
    size: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    from_offset: int = Field(default=0, ge=0, description="Pagination offset")
    include_highlights: bool = Field(default=False, description="Include highlighted snippets")


class PropertyAddress(BaseModel):
    """Property address information."""
    
    street: str = Field(description="Street address")
    city: str = Field(description="City")
    state: str = Field(description="State")
    zip_code: str = Field(description="ZIP code")


class PropertyResult(BaseModel):
    """Individual property search result."""
    
    listing_id: str = Field(description="Property listing ID")
    property_type: str = Field(description="Type of property")
    price: float = Field(description="Property price")
    bedrooms: int = Field(description="Number of bedrooms")
    bathrooms: float = Field(description="Number of bathrooms")
    square_feet: int = Field(description="Square footage")
    address: PropertyAddress = Field(description="Property address")
    description: str = Field(description="Property description")
    features: List[str] = Field(default_factory=list, description="Property features")
    score: float = Field(description="Search relevance score")
    distance_km: Optional[float] = Field(default=None, description="Distance from search center")
    highlights: Optional[Dict[str, List[str]]] = Field(default=None, description="Highlighted text snippets")


class PropertyAggregation(BaseModel):
    """Property aggregation results."""
    
    avg_price: float = Field(description="Average price")
    min_price: float = Field(description="Minimum price")
    max_price: float = Field(description="Maximum price")
    property_count: int = Field(description="Total property count")
    property_type_distribution: Dict[str, int] = Field(description="Count by property type")


class PropertySearchResponse(BaseModel):
    """Response model for property search."""
    
    results: List[PropertyResult] = Field(description="Search results")
    total_hits: int = Field(description="Total number of matching properties")
    execution_time_ms: int = Field(description="Query execution time in milliseconds")
    applied_filters: Optional[PropertyFilter] = Field(default=None, description="Filters that were applied")
    aggregations: Optional[PropertyAggregation] = Field(default=None, description="Aggregation results")


class NeighborhoodSearchRequest(BaseModel):
    """Request model for neighborhood search."""
    
    model_config = ConfigDict(extra='forbid')
    
    city: Optional[str] = Field(default=None, description="City name")
    state: Optional[str] = Field(default=None, description="State name")
    query: Optional[str] = Field(default=None, description="Free text search query")
    include_statistics: bool = Field(default=False, description="Include aggregated property statistics")
    include_related_properties: bool = Field(default=False, description="Include related properties")
    include_related_wikipedia: bool = Field(default=False, description="Include related Wikipedia articles")
    size: int = Field(default=10, ge=1, le=100, description="Number of results to return")


class NeighborhoodResult(BaseModel):
    """Individual neighborhood search result."""
    
    name: str = Field(description="Neighborhood name")
    city: str = Field(description="City")
    state: str = Field(description="State")
    description: Optional[str] = Field(default=None, description="Neighborhood description")
    score: float = Field(description="Search relevance score")


class NeighborhoodStatistics(BaseModel):
    """Neighborhood statistics."""
    
    total_properties: int = Field(description="Total properties in neighborhood")
    avg_price: float = Field(description="Average property price")
    avg_bedrooms: float = Field(description="Average number of bedrooms")
    avg_square_feet: float = Field(description="Average square footage")
    property_types: Dict[str, int] = Field(description="Distribution of property types")


class RelatedProperty(BaseModel):
    """Related property summary."""
    
    listing_id: str = Field(description="Property listing ID")
    address: str = Field(description="Property address")
    price: float = Field(description="Property price")
    property_type: str = Field(description="Property type")


class RelatedWikipediaArticle(BaseModel):
    """Related Wikipedia article summary."""
    
    page_id: str = Field(description="Wikipedia page ID")
    title: str = Field(description="Article title")
    summary: str = Field(description="Article summary")
    relevance_score: float = Field(description="Relevance score")


class NeighborhoodSearchResponse(BaseModel):
    """Response model for neighborhood search."""
    
    results: List[NeighborhoodResult] = Field(description="Search results")
    total_hits: int = Field(description="Total number of matching neighborhoods")
    execution_time_ms: int = Field(description="Query execution time in milliseconds")
    statistics: Optional[NeighborhoodStatistics] = Field(default=None, description="Aggregated statistics")
    related_properties: Optional[List[RelatedProperty]] = Field(default=None, description="Related properties")
    related_wikipedia: Optional[List[RelatedWikipediaArticle]] = Field(default=None, description="Related Wikipedia articles")


class WikipediaSearchType(str, Enum):
    """Wikipedia search type enumeration."""
    
    FULL_TEXT = "full_text"
    CHUNKS = "chunks"
    SUMMARIES = "summaries"


class WikipediaSearchRequest(BaseModel):
    """Request model for Wikipedia search."""
    
    model_config = ConfigDict(extra='forbid')
    
    query: str = Field(description="Search query")
    search_type: WikipediaSearchType = Field(default=WikipediaSearchType.FULL_TEXT, description="Type of search")
    categories: Optional[List[str]] = Field(default=None, description="Filter by categories")
    include_highlights: bool = Field(default=True, description="Include highlighted content")
    highlight_fragment_size: int = Field(default=150, ge=50, le=500, description="Size of highlight fragments")
    size: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    from_offset: int = Field(default=0, ge=0, description="Pagination offset")


class WikipediaSearchResponse(BaseModel):
    """Response model for Wikipedia search."""
    
    results: List[WikipediaArticle] = Field(description="Search results")
    total_hits: int = Field(description="Total number of matching articles")
    execution_time_ms: int = Field(description="Query execution time in milliseconds")
    search_type: WikipediaSearchType = Field(description="Type of search performed")
    applied_categories: Optional[List[str]] = Field(default=None, description="Categories filter applied")