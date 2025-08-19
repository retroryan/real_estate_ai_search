"""
API request and response models with full Pydantic validation.
All models use strict typing and comprehensive validation.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..indexer.enums import PropertyType, PropertyStatus, SortOrder
from ..search.enums import QueryType, GeoDistanceUnit


class ErrorDetail(BaseModel):
    """Detailed error information."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard error response."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    error: str = Field(..., description="Main error message")
    status_code: int = Field(..., ge=400, le=599)
    request_id: Optional[str] = Field(None, description="Request tracking ID")
    errors: List[ErrorDetail] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    page: int = Field(default=1, ge=1, le=1000, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.size


class SearchFiltersRequest(BaseModel):
    """Search filter parameters."""
    model_config = ConfigDict(str_strip_whitespace=True, use_enum_values=False)
    
    # Price filters
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price")
    
    # Property characteristics
    min_bedrooms: Optional[int] = Field(None, ge=0, le=20)
    max_bedrooms: Optional[int] = Field(None, ge=0, le=20)
    min_bathrooms: Optional[float] = Field(None, ge=0, le=20)
    max_bathrooms: Optional[float] = Field(None, ge=0, le=20)
    min_square_feet: Optional[int] = Field(None, ge=0)
    max_square_feet: Optional[int] = Field(None, ge=0)
    
    # Property types and status
    property_types: Optional[List[PropertyType]] = Field(default_factory=list)
    property_status: Optional[PropertyStatus] = Field(None)
    
    # Location filters
    cities: Optional[List[str]] = Field(default_factory=list)
    neighborhoods: Optional[List[str]] = Field(default_factory=list)
    zip_codes: Optional[List[str]] = Field(default_factory=list)
    
    # Date filters
    min_year_built: Optional[int] = Field(None, ge=1800, le=2100)
    max_year_built: Optional[int] = Field(None, ge=1800, le=2100)
    listed_within_days: Optional[int] = Field(None, ge=1, le=365)
    
    # Features
    required_features: Optional[List[str]] = Field(default_factory=list)
    required_amenities: Optional[List[str]] = Field(default_factory=list)
    
    @field_validator('max_price')
    @classmethod
    def validate_price_range(cls, v: Optional[float], values: Dict) -> Optional[float]:
        """Ensure max_price >= min_price."""
        min_price = values.data.get('min_price')
        if v is not None and min_price is not None and v < min_price:
            raise ValueError("max_price must be greater than or equal to min_price")
        return v
    
    @field_validator('max_bedrooms')
    @classmethod
    def validate_bedroom_range(cls, v: Optional[int], values: Dict) -> Optional[int]:
        """Ensure max_bedrooms >= min_bedrooms."""
        min_bedrooms = values.data.get('min_bedrooms')
        if v is not None and min_bedrooms is not None and v < min_bedrooms:
            raise ValueError("max_bedrooms must be greater than or equal to min_bedrooms")
        return v


class SearchRequestAPI(BaseModel):
    """API search request."""
    model_config = ConfigDict(str_strip_whitespace=True, use_enum_values=False)
    
    # Query parameters
    query: Optional[str] = Field(None, min_length=1, max_length=500, description="Search query text")
    query_type: QueryType = Field(default=QueryType.TEXT, description="Type of search")
    
    # Filters
    filters: Optional[SearchFiltersRequest] = Field(default_factory=SearchFiltersRequest)
    
    # Sorting and pagination
    sort_by: SortOrder = Field(default=SortOrder.RELEVANCE)
    page: int = Field(default=1, ge=1, le=1000)
    size: int = Field(default=20, ge=1, le=100)
    
    # Options
    include_aggregations: bool = Field(default=False, description="Include facet aggregations")
    include_highlights: bool = Field(default=True, description="Include search highlights")
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v: Optional[str], values: Dict) -> Optional[str]:
        """Validate query is present for text search."""
        query_type = values.data.get('query_type', QueryType.TEXT)
        if query_type == QueryType.TEXT and not v:
            raise ValueError("Query text is required for text search")
        return v


class GeoSearchRequestAPI(BaseModel):
    """Geographic search request."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    latitude: float = Field(..., ge=-90, le=90, description="Center latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Center longitude")
    radius: float = Field(..., gt=0, le=500, description="Search radius")
    unit: GeoDistanceUnit = Field(default=GeoDistanceUnit.KILOMETERS)
    
    # Optional filters
    filters: Optional[SearchFiltersRequest] = Field(default_factory=SearchFiltersRequest)
    
    # Pagination
    page: int = Field(default=1, ge=1, le=1000)
    size: int = Field(default=20, ge=1, le=100)


class PropertySummary(BaseModel):
    """Summary property information for list views."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    id: str = Field(..., description="Property document ID")
    listing_id: str = Field(..., description="MLS listing ID")
    property_type: str
    price: float
    bedrooms: int
    bathrooms: float
    square_feet: Optional[int] = None
    
    # Address summary
    street: str
    city: str
    state: str
    zip_code: str
    
    # Search metadata
    score: Optional[float] = Field(None, description="Search relevance score")
    distance: Optional[float] = Field(None, description="Distance from search center (km)")
    
    # Key features for display
    main_image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    days_on_market: Optional[int] = None
    
    @classmethod
    def from_search_hit(cls, hit: Dict[str, Any], doc_id: str) -> 'PropertySummary':
        """Create from Elasticsearch hit."""
        source = hit.get('_source', {})
        address = source.get('address', {})
        
        return cls(
            id=doc_id,
            listing_id=source.get('listing_id', ''),
            property_type=source.get('property_type', 'other'),
            price=source.get('price', 0),
            bedrooms=source.get('bedrooms', 0),
            bathrooms=source.get('bathrooms', 0),
            square_feet=source.get('square_feet'),
            street=address.get('street', ''),
            city=address.get('city', ''),
            state=address.get('state', ''),
            zip_code=address.get('zip_code', ''),
            score=hit.get('_score'),
            distance=hit.get('sort', [None])[0] if 'sort' in hit else None,
            main_image_url=source.get('images', [None])[0] if source.get('images') else None,
            days_on_market=source.get('days_on_market')
        )


class PropertyDetail(BaseModel):
    """Full property details."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Core identifiers
    id: str = Field(..., description="Document ID")
    listing_id: str
    mls_number: Optional[str] = None
    
    # Property details
    property_type: str
    status: str
    price: float
    bedrooms: int
    bathrooms: float
    square_feet: Optional[int] = None
    year_built: Optional[int] = None
    lot_size: Optional[float] = None
    
    # Address
    address: Dict[str, Any]
    
    # Neighborhood
    neighborhood: Optional[Dict[str, Any]] = None
    
    # Descriptions and features
    description: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)
    
    # Financial
    price_per_sqft: Optional[float] = None
    hoa_fee: Optional[float] = None
    tax_assessed_value: Optional[float] = None
    annual_tax: Optional[float] = None
    
    # Dates
    listing_date: Optional[str] = None
    last_updated: Optional[str] = None
    days_on_market: Optional[int] = None
    
    # Media
    images: List[str] = Field(default_factory=list)
    virtual_tour_url: Optional[str] = None
    
    # Parking
    parking: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_elasticsearch(cls, doc: Dict[str, Any], doc_id: str) -> 'PropertyDetail':
        """Create from Elasticsearch document."""
        return cls(
            id=doc_id,
            listing_id=doc.get('listing_id', ''),
            mls_number=doc.get('mls_number'),
            property_type=doc.get('property_type', 'other'),
            status=doc.get('status', 'unknown'),
            price=doc.get('price', 0),
            bedrooms=doc.get('bedrooms', 0),
            bathrooms=doc.get('bathrooms', 0),
            square_feet=doc.get('square_feet'),
            year_built=doc.get('year_built'),
            lot_size=doc.get('lot_size'),
            address=doc.get('address', {}),
            neighborhood=doc.get('neighborhood'),
            description=doc.get('description'),
            features=doc.get('features', []),
            amenities=doc.get('amenities', []),
            price_per_sqft=doc.get('price_per_sqft'),
            hoa_fee=doc.get('hoa_fee'),
            tax_assessed_value=doc.get('tax_assessed_value'),
            annual_tax=doc.get('annual_tax'),
            listing_date=doc.get('listing_date'),
            last_updated=doc.get('last_updated'),
            days_on_market=doc.get('days_on_market'),
            images=doc.get('images', []),
            virtual_tour_url=doc.get('virtual_tour_url'),
            parking=doc.get('parking')
        )


class SearchResponseAPI(BaseModel):
    """API search response."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Results
    properties: List[PropertySummary]
    total: int = Field(..., ge=0, description="Total matching properties")
    
    # Pagination
    page: int
    size: int
    total_pages: int = Field(..., ge=1)
    
    # Performance
    took_ms: int = Field(..., ge=0, description="Query execution time")
    
    # Aggregations (optional)
    aggregations: Optional[Dict[str, Any]] = None
    
    # Request tracking
    request_id: Optional[str] = None
    
    @property
    def has_next_page(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages
    
    @property
    def has_previous_page(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1


class HealthStatus(BaseModel):
    """Health check status."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    status: str = Field(..., pattern="^(healthy|degraded|unhealthy)$")
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = Field(default="1.0.0")
    
    # Component statuses
    elasticsearch: Dict[str, Any]
    index: Dict[str, Any]
    
    # Performance metrics
    metrics: Optional[Dict[str, Any]] = None
    
    @property
    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        return self.status == "healthy"


class SimilarPropertiesRequest(BaseModel):
    """Request for similar properties."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    max_results: int = Field(default=10, ge=1, le=50)
    include_source: bool = Field(default=False, description="Include source property in results")
    filters: Optional[SearchFiltersRequest] = None


class APIMetadata(BaseModel):
    """API metadata for responses."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    api_version: str = Field(default="1.0.0")
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    response_time_ms: int