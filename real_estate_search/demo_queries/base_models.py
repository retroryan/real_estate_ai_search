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

from __future__ import annotations

from typing import Dict, Any, Optional, List, Literal, TypeVar, Generic
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
    
    @classmethod
    def _missing_(cls, value):
        """Handle case variations and unknown values."""
        if value:
            # Try case-insensitive match
            value_lower = str(value).lower()
            for member in cls:
                if member.value.lower() == value_lower:
                    return member
        # Default to OTHER for unknown types
        return cls.OTHER


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
    score: Optional[float] = Field(None, alias="_score", ge=0, description="Elasticsearch relevance score")
    index: Optional[str] = Field(None, alias="_index", description="Source index")
    id: Optional[str] = Field(None, alias="_id", description="Document ID")
    
    model_config = ConfigDict(populate_by_name=True)
    
    @computed_field  # type: ignore
    @property
    def has_score(self) -> bool:
        """Check if this entity has a relevance score."""
        return self.score is not None and self.score > 0


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
    state: Optional[str] = Field(None, description="State code or name")
    zip_code: Optional[str] = Field(None, pattern=r"^\d{5}(-\d{4})?$", description="ZIP code")
    county: Optional[str] = Field(None, description="County name")
    country: str = Field("US", description="Country code")
    location: Optional[Dict[str, float]] = Field(None, description="Geographic coordinates in ES geo_point format")
    
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




# ============================================================================
# NEIGHBORHOOD MODELS
# ============================================================================

class Demographics(BaseModel):
    """Neighborhood demographic information."""
    population: Optional[int] = Field(None, ge=0, description="Total population")
    households: Optional[int] = Field(None, ge=0, description="Number of households")
    median_age: Optional[float] = Field(None, ge=0, le=120, description="Median age")
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
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State code or name")
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
    score: Optional[float] = Field(None, alias="_score", description="Search relevance score")
    
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    
    @computed_field  # type: ignore
    @property
    def display_name(self) -> str:
        """Get display name with city."""
        return f"{self.name}, {self.city}"




# ============================================================================
# AGGREGATION MODELS
# ============================================================================

class BucketAggregation(BaseModel):
    """Single bucket in an aggregation result."""
    key: str = Field(..., description="Bucket key (converted to string)")
    key_as_string: Optional[str] = Field(None, description="String representation of key")
    doc_count: int = Field(..., ge=0, description="Document count")
    sub_aggregations: Optional[Dict[str, Any]] = Field(None, description="Nested aggregations")
    
    @field_validator('key', mode='before')
    @classmethod
    def convert_key_to_string(cls, v):
        """Convert any key type to string."""
        return str(v) if v is not None else "unknown"
    
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
    value: Optional[float] = Field(None, description="Single value result")
    
    @field_validator('value', mode='before')
    @classmethod
    def convert_value_to_float(cls, v):
        """Convert int to float if needed."""
        if v is not None:
            return float(v)
        return v
    
    model_config = ConfigDict(extra="ignore", use_enum_values=True)


# ============================================================================
# SEARCH MODELS
# ============================================================================

class SearchHit(BaseModel):
    """Individual search hit from Elasticsearch."""
    index: str = Field(..., alias="_index", description="Index name")
    id: str = Field(..., alias="_id", description="Document ID")
    score: Optional[float] = Field(None, alias="_score", description="Relevance score")
    source: Dict[str, Any] = Field(..., alias="_source", description="Document source")
    highlight: Optional[Dict[str, List[str]]] = Field(None, description="Highlighted fields")
    
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class SourceFilter(BaseModel):
    """Source filtering configuration."""
    includes: Optional[List[str]] = Field(None, description="Fields to include")
    excludes: Optional[List[str]] = Field(None, description="Fields to exclude")
    
    def to_dict(self) -> Dict[str, List[str]]:
        """Convert to ES source filter format."""
        result = {}
        if self.includes:
            result["includes"] = self.includes
        if self.excludes:
            result["excludes"] = self.excludes
        return result if result else True


class SearchRequest(BaseModel):
    """Search request configuration."""
    index: List[str] = Field(..., description="Index(es) to search")
    query: Dict[str, Any] = Field(..., description="Query DSL")
    size: int = Field(10, ge=0, le=10000, description="Number of results")
    from_: int = Field(0, ge=0, alias="from", description="Starting offset")
    sort: Optional[List[Dict[str, Any]]] = Field(None, description="Sort criteria")
    aggs: Optional[Dict[str, Any]] = Field(None, description="Aggregations")
    highlight: Optional[Dict[str, Any]] = Field(None, description="Highlight configuration")
    source: Optional[SourceFilter] = Field(None, alias="_source", description="Source filtering")
    source_enabled: bool = Field(True, description="Whether to return source at all")
    
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
        if not self.source_enabled:
            query_dict["_source"] = False
        elif self.source:
            query_dict["_source"] = self.source.to_dict()
            
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
    def from_elasticsearch(cls, response: Dict[str, Any]) -> SearchResponse:
        """Create from raw Elasticsearch response."""
        return cls(
            took=response.get("took", 0),
            timed_out=response.get("timed_out", False),
            total_hits=response.get("hits", {}).get("total", {}).get("value", 0),
            max_score=response.get("hits", {}).get("max_score"),
            hits=[SearchHit(**hit) for hit in response.get("hits", {}).get("hits", [])],
            aggregations=response.get("aggregations")
        )


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