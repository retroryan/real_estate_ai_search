"""
Comprehensive base models for all demo queries with strong typing and validation.

This module provides the foundation for type-safe Elasticsearch interactions across
all demo queries. It demonstrates best practices for:
- Data validation with Pydantic
- Type safety for Elasticsearch responses
- Clear separation of concerns
- Comprehensive documentation

DESIGN PRINCIPLES:
1. Immutability where possible (frozen=True for value objects)
2. Explicit over implicit (all fields clearly typed)
3. Fail fast (validation at boundaries)
4. Single responsibility (each model has one clear purpose)
"""

from typing import Dict, Any, Optional, List, Union, Literal, TypeVar, Generic
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field, model_validator
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class IndexName(str, Enum):
    """Elasticsearch index names used in the system."""
    PROPERTIES = "properties"
    NEIGHBORHOODS = "neighborhoods"
    WIKIPEDIA = "wikipedia"


class EntityType(str, Enum):
    """Types of entities in the search system."""
    PROPERTY = "property"
    NEIGHBORHOOD = "neighborhood"
    WIKIPEDIA = "wikipedia"


class PropertyType(str, Enum):
    """Types of real estate properties."""
    SINGLE_FAMILY = "Single Family"
    CONDO = "Condo"
    TOWNHOUSE = "Townhouse"
    MULTI_FAMILY = "Multi-Family"
    LAND = "Land"
    OTHER = "Other"


class QueryType(str, Enum):
    """Types of Elasticsearch queries used in demos."""
    MATCH = "match"
    TERM = "term"
    RANGE = "range"
    BOOL = "bool"
    FUNCTION_SCORE = "function_score"
    GEO_DISTANCE = "geo_distance"
    KNN = "knn"
    MULTI_MATCH = "multi_match"
    MATCH_PHRASE = "match_phrase"


class AggregationType(str, Enum):
    """Types of Elasticsearch aggregations."""
    TERMS = "terms"
    AVG = "avg"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    STATS = "stats"
    HISTOGRAM = "histogram"
    DATE_HISTOGRAM = "date_histogram"
    RANGE = "range"


# ============================================================================
# BASE MODELS
# ============================================================================

class TimestampedModel(BaseModel):
    """Base model with timestamp fields."""
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    model_config = ConfigDict(extra="ignore")


class ScoredModel(BaseModel):
    """Base model for entities with Elasticsearch scores."""
    _score: Optional[float] = Field(None, ge=0, description="Elasticsearch relevance score")
    _index: Optional[str] = Field(None, description="Source index")
    _id: Optional[str] = Field(None, description="Document ID")
    
    @computed_field  # type: ignore
    @property
    def has_score(self) -> bool:
        """Check if this entity has a relevance score."""
        return self._score is not None and self._score > 0


# ============================================================================
# LOCATION MODELS
# ============================================================================

class GeoPoint(BaseModel):
    """Geographic coordinate point."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    
    model_config = ConfigDict(frozen=True)
    
    @computed_field  # type: ignore
    @property
    def as_list(self) -> List[float]:
        """Return as [lon, lat] for Elasticsearch."""
        return [self.lon, self.lat]
    
    @computed_field  # type: ignore
    @property
    def as_string(self) -> str:
        """Return as 'lat,lon' string."""
        return f"{self.lat},{self.lon}"


class Address(BaseModel):
    """Comprehensive address model."""
    street: Optional[str] = Field(None, description="Street address")
    unit: Optional[str] = Field(None, description="Unit/Apt number")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, min_length=2, max_length=2, description="State code")
    zip_code: Optional[str] = Field(None, pattern=r"^\d{5}(-\d{4})?$", description="ZIP code")
    county: Optional[str] = Field(None, description="County name")
    country: str = Field("US", description="Country code")
    location: Optional[GeoPoint] = Field(None, description="Geographic coordinates")
    
    model_config = ConfigDict(extra="ignore")
    
    @computed_field  # type: ignore
    @property
    def full_address(self) -> str:
        """Generate complete address string."""
        parts = []
        if self.street:
            parts.append(self.street)
            if self.unit:
                parts.append(f"Unit {self.unit}")
        if self.city and self.state:
            parts.append(f"{self.city}, {self.state}")
        if self.zip_code:
            parts.append(self.zip_code)
        return " ".join(parts) if parts else "Address not available"
    
    @computed_field  # type: ignore
    @property
    def city_state(self) -> str:
        """Get city, state string."""
        if self.city and self.state:
            return f"{self.city}, {self.state}"
        return self.city or self.state or "Location unknown"


# ============================================================================
# PROPERTY MODELS
# ============================================================================

class PropertyFeatures(BaseModel):
    """Detailed property features."""
    bedrooms: Optional[int] = Field(None, ge=0, le=20, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, ge=0, le=20, description="Number of bathrooms")
    square_feet: Optional[int] = Field(None, ge=0, le=100000, description="Square footage")
    lot_size: Optional[float] = Field(None, ge=0, description="Lot size in acres")
    year_built: Optional[int] = Field(None, ge=1600, le=2100, description="Year built")
    stories: Optional[int] = Field(None, ge=1, le=10, description="Number of stories")
    garage_spaces: Optional[int] = Field(None, ge=0, le=10, description="Garage spaces")
    
    model_config = ConfigDict(extra="ignore")
    
    @computed_field  # type: ignore
    @property
    def rooms_total(self) -> Optional[int]:
        """Calculate total rooms (bedrooms + 1 for each bathroom)."""
        if self.bedrooms is not None and self.bathrooms is not None:
            return self.bedrooms + int(self.bathrooms)
        return None


class PropertyListing(BaseModel):
    """Complete property listing model."""
    listing_id: str = Field(..., description="Unique listing identifier")
    property_type: Optional[PropertyType] = Field(None, description="Type of property")
    status: Optional[str] = Field("active", description="Listing status")
    
    # Location
    address: Address = Field(..., description="Property address")
    neighborhood_id: Optional[str] = Field(None, description="Associated neighborhood")
    school_district: Optional[str] = Field(None, description="School district")
    
    # Pricing
    price: Optional[float] = Field(None, ge=0, description="Listing price")
    price_per_sqft: Optional[float] = Field(None, ge=0, description="Price per square foot")
    hoa_fee: Optional[float] = Field(None, ge=0, description="HOA monthly fee")
    tax_annual: Optional[float] = Field(None, ge=0, description="Annual property tax")
    
    # Features
    features: PropertyFeatures = Field(default_factory=PropertyFeatures, description="Property features")
    amenities: List[str] = Field(default_factory=list, description="List of amenities")
    
    # Descriptions
    title: Optional[str] = Field(None, max_length=200, description="Listing title")
    description: Optional[str] = Field(None, description="Full description")
    highlights: List[str] = Field(default_factory=list, description="Key highlights")
    
    # Dates
    list_date: Optional[datetime] = Field(None, description="Date listed")
    last_sold_date: Optional[datetime] = Field(None, description="Last sale date")
    last_sold_price: Optional[float] = Field(None, ge=0, description="Last sale price")
    
    # Media
    photo_count: Optional[int] = Field(None, ge=0, description="Number of photos")
    virtual_tour_url: Optional[str] = Field(None, description="Virtual tour URL")
    
    # Scoring and metadata
    _score: Optional[float] = Field(None, description="Search relevance score")
    _highlights: Optional[Dict[str, List[str]]] = Field(None, description="Search highlights")
    
    model_config = ConfigDict(extra="ignore", use_enum_values=True)
    
    @computed_field  # type: ignore
    @property
    def display_price(self) -> str:
        """Format price for display."""
        if self.price:
            return f"${self.price:,.0f}"
        return "Price not available"
    
    @computed_field  # type: ignore
    @property
    def summary(self) -> str:
        """Generate property summary."""
        parts = []
        if self.features.bedrooms:
            parts.append(f"{self.features.bedrooms} bed")
        if self.features.bathrooms:
            parts.append(f"{self.features.bathrooms} bath")
        if self.features.square_feet:
            parts.append(f"{self.features.square_feet:,} sqft")
        if self.property_type:
            parts.append(self.property_type.value)
        return " | ".join(parts) if parts else "Property details not available"


# ============================================================================
# NEIGHBORHOOD MODELS
# ============================================================================

class Demographics(BaseModel):
    """Neighborhood demographic information."""
    population: Optional[int] = Field(None, ge=0, description="Total population")
    households: Optional[int] = Field(None, ge=0, description="Number of households")
    median_age: Optional[float] = Field(None, ge=0, le=120, description="Median age")
    median_income: Optional[float] = Field(None, ge=0, description="Median household income")
    median_home_value: Optional[float] = Field(None, ge=0, description="Median home value")
    
    model_config = ConfigDict(extra="ignore")


class SchoolRatings(BaseModel):
    """School ratings for a neighborhood."""
    elementary: Optional[float] = Field(None, ge=0, le=10, description="Elementary school rating")
    middle: Optional[float] = Field(None, ge=0, le=10, description="Middle school rating")
    high: Optional[float] = Field(None, ge=0, le=10, description="High school rating")
    
    @computed_field  # type: ignore
    @property
    def average_rating(self) -> Optional[float]:
        """Calculate average school rating."""
        ratings = [r for r in [self.elementary, self.middle, self.high] if r is not None]
        return sum(ratings) / len(ratings) if ratings else None


class Neighborhood(BaseModel):
    """Complete neighborhood model."""
    neighborhood_id: str = Field(..., description="Unique neighborhood identifier")
    name: str = Field(..., description="Neighborhood name")
    
    # Location
    city: str = Field(..., description="City name")
    state: str = Field(..., min_length=2, max_length=2, description="State code")
    county: Optional[str] = Field(None, description="County name")
    boundaries: Optional[Dict[str, Any]] = Field(None, description="Geographic boundaries")
    center_point: Optional[GeoPoint] = Field(None, description="Center coordinates")
    
    # Characteristics
    description: Optional[str] = Field(None, description="Neighborhood description")
    established_year: Optional[int] = Field(None, ge=1600, le=2100, description="Year established")
    area_sqmi: Optional[float] = Field(None, ge=0, description="Area in square miles")
    
    # Amenities and features
    amenities: List[str] = Field(default_factory=list, description="Neighborhood amenities")
    public_transport: List[str] = Field(default_factory=list, description="Public transport options")
    nearby_schools: List[str] = Field(default_factory=list, description="Nearby schools")
    parks: List[str] = Field(default_factory=list, description="Parks and recreation")
    
    # Statistics
    demographics: Optional[Demographics] = Field(None, description="Demographic information")
    school_ratings: Optional[SchoolRatings] = Field(None, description="School ratings")
    crime_rate: Optional[str] = Field(None, description="Crime rate category")
    walkability_score: Optional[int] = Field(None, ge=0, le=100, description="Walk score")
    
    # Property statistics
    avg_price: Optional[float] = Field(None, ge=0, description="Average property price")
    avg_price_per_sqft: Optional[float] = Field(None, ge=0, description="Average price per sqft")
    property_count: Optional[int] = Field(None, ge=0, description="Number of properties")
    
    # Wikipedia correlations
    wikipedia_correlations: Optional[Dict[str, Any]] = Field(None, description="Related Wikipedia articles")
    
    # Metadata
    _score: Optional[float] = Field(None, description="Search relevance score")
    
    model_config = ConfigDict(extra="ignore")
    
    @computed_field  # type: ignore
    @property
    def display_name(self) -> str:
        """Get display name with city."""
        return f"{self.name}, {self.city}"


# ============================================================================
# WIKIPEDIA MODELS
# ============================================================================

class WikipediaArticle(BaseModel):
    """Wikipedia article model."""
    page_id: str = Field(..., description="Wikipedia page ID")
    title: str = Field(..., description="Article title")
    url: Optional[str] = Field(None, description="Article URL")
    
    # Content
    summary: Optional[str] = Field(None, description="Article summary")
    content: Optional[str] = Field(None, description="Article content")
    full_content: Optional[str] = Field(None, description="Full HTML content")
    content_length: Optional[int] = Field(None, ge=0, description="Content length")
    
    # Location relevance
    city: Optional[str] = Field(None, description="Associated city")
    state: Optional[str] = Field(None, description="Associated state")
    best_city: Optional[str] = Field(None, description="Best matched city")
    best_state: Optional[str] = Field(None, description="Best matched state")
    relevance_score: Optional[float] = Field(None, ge=0, le=100, description="Location relevance")
    
    # Classification
    categories: List[str] = Field(default_factory=list, description="Wikipedia categories")
    topics: List[str] = Field(default_factory=list, description="Article topics")
    content_category: Optional[str] = Field(None, description="Content category")
    
    # Metadata
    _score: Optional[float] = Field(None, description="Search relevance score")
    _relationship: Optional[str] = Field(None, description="Relationship to parent entity")
    _confidence: Optional[float] = Field(None, ge=0, le=1, description="Relationship confidence")
    
    model_config = ConfigDict(extra="ignore")
    
    @computed_field  # type: ignore
    @property
    def location_string(self) -> str:
        """Get location as string."""
        city = self.best_city or self.city
        state = self.best_state or self.state
        if city and state:
            return f"{city}, {state}"
        return city or state or "Location unknown"


# ============================================================================
# AGGREGATION MODELS
# ============================================================================

class BucketAggregation(BaseModel):
    """Single bucket in an aggregation result."""
    key: Union[str, int, float] = Field(..., description="Bucket key")
    doc_count: int = Field(..., ge=0, description="Document count")
    sub_aggregations: Optional[Dict[str, Any]] = Field(None, description="Nested aggregations")
    
    model_config = ConfigDict(extra="ignore")


class StatsAggregation(BaseModel):
    """Statistical aggregation result."""
    count: int = Field(..., ge=0, description="Document count")
    min: Optional[float] = Field(None, description="Minimum value")
    max: Optional[float] = Field(None, description="Maximum value")
    avg: Optional[float] = Field(None, description="Average value")
    sum: Optional[float] = Field(None, description="Sum of values")
    
    model_config = ConfigDict(extra="ignore")
    
    @computed_field  # type: ignore
    @property
    def range(self) -> Optional[float]:
        """Calculate range (max - min)."""
        if self.max is not None and self.min is not None:
            return self.max - self.min
        return None


class AggregationResult(BaseModel):
    """Container for aggregation results."""
    name: str = Field(..., description="Aggregation name")
    type: AggregationType = Field(..., description="Type of aggregation")
    buckets: Optional[List[BucketAggregation]] = Field(None, description="Bucket results")
    stats: Optional[StatsAggregation] = Field(None, description="Statistical results")
    value: Optional[Union[float, int]] = Field(None, description="Single value result")
    
    model_config = ConfigDict(extra="ignore", use_enum_values=True)


# ============================================================================
# SEARCH MODELS
# ============================================================================

class SearchHit(BaseModel):
    """Individual search hit from Elasticsearch."""
    _index: str = Field(..., description="Index name")
    _id: str = Field(..., description="Document ID")
    _score: Optional[float] = Field(None, description="Relevance score")
    _source: Dict[str, Any] = Field(..., description="Document source")
    highlight: Optional[Dict[str, List[str]]] = Field(None, description="Highlighted fields")
    
    model_config = ConfigDict(extra="allow")
    
    def to_entity(self) -> Optional[Union[PropertyListing, Neighborhood, WikipediaArticle]]:
        """Convert to appropriate entity type based on index."""
        try:
            source = self._source.copy()
            if self._score is not None:
                source['_score'] = self._score
            
            if self._index == IndexName.PROPERTIES.value:
                # Handle nested address structure
                if 'address' in source and isinstance(source['address'], dict):
                    source['address'] = Address(**source['address'])
                if 'features' not in source:
                    # Extract features from top-level fields
                    source['features'] = PropertyFeatures(
                        bedrooms=source.get('bedrooms'),
                        bathrooms=source.get('bathrooms'),
                        square_feet=source.get('square_feet'),
                        year_built=source.get('year_built')
                    )
                return PropertyListing(**source)
            
            elif self._index == IndexName.NEIGHBORHOODS.value:
                if 'demographics' in source and isinstance(source['demographics'], dict):
                    source['demographics'] = Demographics(**source['demographics'])
                if 'school_ratings' in source and isinstance(source['school_ratings'], dict):
                    source['school_ratings'] = SchoolRatings(**source['school_ratings'])
                return Neighborhood(**source)
            
            elif self._index == IndexName.WIKIPEDIA.value:
                return WikipediaArticle(**source)
            
        except Exception as e:
            logger.error(f"Failed to convert hit to entity: {e}")
        
        return None


class SearchRequest(BaseModel):
    """Search request configuration."""
    index: Union[str, List[str]] = Field(..., description="Index(es) to search")
    query: Dict[str, Any] = Field(..., description="Query DSL")
    size: int = Field(10, ge=0, le=10000, description="Number of results")
    from_: int = Field(0, ge=0, alias="from", description="Starting offset")
    sort: Optional[List[Dict[str, Any]]] = Field(None, description="Sort criteria")
    aggs: Optional[Dict[str, Any]] = Field(None, description="Aggregations")
    highlight: Optional[Dict[str, Any]] = Field(None, description="Highlight configuration")
    _source: Optional[Union[bool, List[str], Dict[str, Any]]] = Field(True, description="Source filtering")
    
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Elasticsearch query dict."""
        query_dict = {
            "query": self.query,
            "size": self.size,
            "from": self.from_
        }
        
        if self.sort:
            query_dict["sort"] = self.sort
        if self.aggs:
            query_dict["aggs"] = self.aggs
        if self.highlight:
            query_dict["highlight"] = self.highlight
        if self._source is not None:
            query_dict["_source"] = self._source
            
        return query_dict


class SearchResponse(BaseModel):
    """Search response from Elasticsearch."""
    took: int = Field(..., description="Query execution time in ms")
    timed_out: bool = Field(False, description="Whether query timed out")
    total_hits: int = Field(..., description="Total matching documents")
    max_score: Optional[float] = Field(None, description="Maximum relevance score")
    hits: List[SearchHit] = Field(default_factory=list, description="Search results")
    aggregations: Optional[Dict[str, Any]] = Field(None, description="Aggregation results")
    
    model_config = ConfigDict(extra="ignore")
    
    @classmethod
    def from_elasticsearch(cls, response: Dict[str, Any]) -> "SearchResponse":
        """Create from raw Elasticsearch response."""
        return cls(
            took=response.get("took", 0),
            timed_out=response.get("timed_out", False),
            total_hits=response.get("hits", {}).get("total", {}).get("value", 0),
            max_score=response.get("hits", {}).get("max_score"),
            hits=[SearchHit(**hit) for hit in response.get("hits", {}).get("hits", [])],
            aggregations=response.get("aggregations")
        )
    
    def to_entities(self) -> List[Union[PropertyListing, Neighborhood, WikipediaArticle]]:
        """Convert all hits to entity objects."""
        entities = []
        for hit in self.hits:
            entity = hit.to_entity()
            if entity:
                entities.append(entity)
        return entities


# ============================================================================
# QUERY BUILDER MODELS
# ============================================================================

class QueryClause(BaseModel):
    """Single query clause in a compound query."""
    type: QueryType = Field(..., description="Type of query")
    field: Optional[str] = Field(None, description="Field to query")
    value: Optional[Any] = Field(None, description="Query value")
    params: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")
    
    model_config = ConfigDict(extra="ignore", use_enum_values=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Elasticsearch query clause."""
        if self.type == QueryType.MATCH:
            return {"match": {self.field: {"query": self.value, **self.params}}}
        elif self.type == QueryType.TERM:
            return {"term": {self.field: self.value}}
        elif self.type == QueryType.RANGE:
            return {"range": {self.field: self.value}}
        else:
            return {self.type.value: self.params}


class BoolQuery(BaseModel):
    """Boolean compound query."""
    must: List[QueryClause] = Field(default_factory=list, description="Must match all")
    should: List[QueryClause] = Field(default_factory=list, description="Should match any")
    must_not: List[QueryClause] = Field(default_factory=list, description="Must not match")
    filter: List[QueryClause] = Field(default_factory=list, description="Filter without scoring")
    minimum_should_match: Optional[int] = Field(None, description="Minimum should clauses")
    
    model_config = ConfigDict(extra="ignore")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Elasticsearch bool query."""
        query: Dict[str, Any] = {"bool": {}}
        
        if self.must:
            query["bool"]["must"] = [clause.to_dict() for clause in self.must]
        if self.should:
            query["bool"]["should"] = [clause.to_dict() for clause in self.should]
        if self.must_not:
            query["bool"]["must_not"] = [clause.to_dict() for clause in self.must_not]
        if self.filter:
            query["bool"]["filter"] = [clause.to_dict() for clause in self.filter]
        if self.minimum_should_match is not None:
            query["bool"]["minimum_should_match"] = self.minimum_should_match
            
        return query


# ============================================================================
# DEMO RESULT MODELS
# ============================================================================

T = TypeVar('T', PropertyListing, Neighborhood, WikipediaArticle)


class TypedDemoResult(BaseModel, Generic[T]):
    """Type-safe demo query result."""
    query_name: str = Field(..., description="Name of the demo query")
    query_description: str = Field(..., description="What this query demonstrates")
    
    # Timing
    execution_time_ms: int = Field(0, ge=0, description="Query execution time")
    
    # Results
    total_hits: int = Field(0, ge=0, description="Total matching documents")
    returned_hits: int = Field(0, ge=0, description="Number of returned documents")
    entities: List[T] = Field(default_factory=list, description="Typed result entities")
    
    # Aggregations
    aggregations: Optional[List[AggregationResult]] = Field(None, description="Aggregation results")
    
    # Query details
    query_dsl: Dict[str, Any] = Field(default_factory=dict, description="Query DSL used")
    explanation: Optional[str] = Field(None, description="Explanation of results")
    
    # Metadata
    index_used: Optional[str] = Field(None, description="Elasticsearch index queried")
    
    model_config = ConfigDict(extra="ignore")
    
    @computed_field  # type: ignore
    @property
    def success(self) -> bool:
        """Check if query was successful."""
        return self.total_hits > 0 or self.aggregations is not None
    
    def to_legacy_format(self) -> Dict[str, Any]:
        """Convert to legacy dictionary format for backward compatibility."""
        return {
            "query_name": self.query_name,
            "execution_time_ms": self.execution_time_ms,
            "total_hits": self.total_hits,
            "returned_hits": self.returned_hits,
            "results": [entity.model_dump(exclude_none=True) for entity in self.entities],
            "aggregations": self.aggregations,
            "query_dsl": self.query_dsl,
            "explanation": self.explanation
        }