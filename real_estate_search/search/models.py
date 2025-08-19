"""
Pydantic models for search operations.
All search requests and responses use these models.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic.types import NonNegativeInt, NonNegativeFloat, PositiveInt

from ..indexer.enums import PropertyType, PropertyStatus, SortOrder, FieldName
from ..indexer.models import Property, Address, Neighborhood
from .enums import QueryType, GeoDistanceUnit, AggregationName


class GeoPoint(BaseModel):
    """Geographic point for search."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")


class SearchFilters(BaseModel):
    """Structured search filters with validation."""
    model_config = ConfigDict(str_strip_whitespace=True, use_enum_values=False)
    
    # Price filters
    min_price: Optional[NonNegativeFloat] = None
    max_price: Optional[NonNegativeFloat] = None
    
    # Size filters
    min_bedrooms: Optional[NonNegativeInt] = None
    max_bedrooms: Optional[NonNegativeInt] = None
    min_bathrooms: Optional[NonNegativeFloat] = None
    max_bathrooms: Optional[NonNegativeFloat] = None
    min_square_feet: Optional[NonNegativeInt] = None
    max_square_feet: Optional[NonNegativeInt] = None
    
    # Type and status filters
    property_types: Optional[List[PropertyType]] = Field(default_factory=list)
    status: Optional[PropertyStatus] = PropertyStatus.ACTIVE
    
    # Location filters
    cities: Optional[List[str]] = Field(default_factory=list)
    states: Optional[List[str]] = Field(default_factory=list)
    zip_codes: Optional[List[str]] = Field(default_factory=list)
    neighborhood_ids: Optional[List[str]] = Field(default_factory=list)
    
    # Feature filters
    features: Optional[List[str]] = Field(default_factory=list)
    amenities: Optional[List[str]] = Field(default_factory=list)
    must_have_parking: Optional[bool] = None
    min_parking_spaces: Optional[NonNegativeInt] = None
    
    # Date filters
    max_days_on_market: Optional[NonNegativeInt] = None
    listed_after: Optional[datetime] = None
    listed_before: Optional[datetime] = None
    
    # Other filters
    min_year_built: Optional[int] = Field(None, ge=1800)
    max_year_built: Optional[int] = None
    max_hoa_fee: Optional[NonNegativeFloat] = None
    
    @field_validator('cities', 'states', 'features', 'amenities')
    @classmethod
    def lowercase_lists(cls, v: List[str]) -> List[str]:
        """Normalize string lists to lowercase."""
        if v:
            return [item.lower().strip() for item in v if item.strip()]
        return v
    
    @field_validator('states')
    @classmethod
    def uppercase_states(cls, v: List[str]) -> List[str]:
        """Ensure state codes are uppercase."""
        if v:
            return [state.upper() for state in v]
        return v


class GeoSearchParams(BaseModel):
    """Parameters for geographic search."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    center: GeoPoint
    distance: PositiveInt = Field(..., description="Search radius")
    unit: GeoDistanceUnit = GeoDistanceUnit.KILOMETERS
    filters: Optional[SearchFilters] = None


class SearchRequest(BaseModel):
    """Complete search request model."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Query parameters
    query_type: QueryType = QueryType.TEXT
    query_text: Optional[str] = Field(None, min_length=1, max_length=500)
    filters: Optional[SearchFilters] = None
    
    # Geo search parameters
    geo_params: Optional[GeoSearchParams] = None
    
    # Pagination
    page: PositiveInt = Field(default=1, le=100)
    size: PositiveInt = Field(default=20, le=100)
    
    # Sorting
    sort_by: SortOrder = SortOrder.RELEVANCE
    
    # Options
    include_aggregations: bool = True
    include_highlights: bool = False
    exclude_fields: Optional[List[FieldName]] = Field(default_factory=list)
    
    # Similar properties
    similar_to_id: Optional[str] = Field(None, description="Property ID for similarity search")
    
    @field_validator('query_text')
    @classmethod
    def clean_query_text(cls, v: Optional[str]) -> Optional[str]:
        """Clean and validate query text."""
        if v:
            return v.strip()
        return v


class PropertyHit(BaseModel):
    """Single property search result."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Property data
    property: Property
    
    # Search metadata
    score: Optional[float] = Field(None, description="Relevance score")
    distance: Optional[float] = Field(None, description="Distance from search center")
    highlights: Optional[Dict[str, List[str]]] = Field(default_factory=dict)
    
    # Internal ID
    doc_id: str = Field(..., description="Elasticsearch document ID")


class Aggregation(BaseModel):
    """Base aggregation result."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: AggregationName
    type: str = Field(..., description="Aggregation type")


class BucketAggregation(Aggregation):
    """Bucket aggregation result."""
    buckets: List[Dict[str, Any]] = Field(default_factory=list)


class StatsAggregation(Aggregation):
    """Statistical aggregation result."""
    count: int = 0
    min: Optional[float] = None
    max: Optional[float] = None
    avg: Optional[float] = None
    sum: Optional[float] = None


class SearchResponse(BaseModel):
    """Complete search response model."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Results
    hits: List[PropertyHit] = Field(default_factory=list)
    total: NonNegativeInt = Field(..., description="Total matching documents")
    
    # Pagination
    page: PositiveInt
    size: PositiveInt
    total_pages: PositiveInt
    
    # Performance
    took_ms: NonNegativeInt = Field(..., description="Query execution time in milliseconds")
    
    # Aggregations
    aggregations: Optional[Dict[AggregationName, Union[BucketAggregation, StatsAggregation]]] = None
    
    # Request echo
    request: SearchRequest
    
    @classmethod
    def from_elasticsearch(
        cls,
        es_response: Dict[str, Any],
        request: SearchRequest,
        properties: List[Property]
    ) -> 'SearchResponse':
        """
        Create SearchResponse from Elasticsearch response.
        
        Args:
            es_response: Raw Elasticsearch response
            request: Original search request
            properties: List of Property models
            
        Returns:
            Populated SearchResponse model
        """
        hits_data = es_response.get('hits', {})
        total = hits_data.get('total', {}).get('value', 0)
        
        # Create PropertyHit objects
        hits = []
        for i, hit in enumerate(hits_data.get('hits', [])):
            if i < len(properties):
                property_hit = PropertyHit(
                    property=properties[i],
                    score=hit.get('_score'),
                    highlights=hit.get('highlight', {}),
                    doc_id=hit.get('_id', '')
                )
                
                # Add distance if present
                if 'sort' in hit and isinstance(hit['sort'], list):
                    for sort_value in hit['sort']:
                        if isinstance(sort_value, (int, float)):
                            property_hit.distance = sort_value
                            break
                
                hits.append(property_hit)
        
        # Calculate pagination (ensure at least 1 page even with 0 results)
        if total == 0:
            total_pages = 1
        elif request.size > 0:
            total_pages = (total + request.size - 1) // request.size
        else:
            total_pages = 1
        
        # Process aggregations
        aggregations = None
        if 'aggregations' in es_response and request.include_aggregations:
            aggregations = cls._process_aggregations(es_response['aggregations'])
        
        return cls(
            hits=hits,
            total=total,
            page=request.page,
            size=request.size,
            total_pages=total_pages,
            took_ms=es_response.get('took', 0),
            aggregations=aggregations,
            request=request
        )
    
    @staticmethod
    def _process_aggregations(
        es_aggregations: Dict[str, Any]
    ) -> Dict[AggregationName, Union[BucketAggregation, StatsAggregation]]:
        """Process Elasticsearch aggregations into typed models."""
        result = {}
        
        for agg_name, agg_data in es_aggregations.items():
            try:
                agg_enum = AggregationName(agg_name)
                
                # Determine aggregation type
                if 'buckets' in agg_data:
                    result[agg_enum] = BucketAggregation(
                        name=agg_enum,
                        type='terms' if 'doc_count_error_upper_bound' in agg_data else 'range',
                        buckets=agg_data['buckets']
                    )
                elif any(k in agg_data for k in ['count', 'min', 'max', 'avg', 'sum']):
                    result[agg_enum] = StatsAggregation(
                        name=agg_enum,
                        type='stats',
                        count=agg_data.get('count', 0),
                        min=agg_data.get('min'),
                        max=agg_data.get('max'),
                        avg=agg_data.get('avg'),
                        sum=agg_data.get('sum')
                    )
            except ValueError:
                # Skip unknown aggregation names
                continue
        
        return result


class SimilarPropertiesRequest(BaseModel):
    """Request for finding similar properties."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    property_id: str = Field(..., min_length=1, description="Source property ID")
    max_results: PositiveInt = Field(default=10, le=50)
    filters: Optional[SearchFilters] = None
    include_source: bool = Field(default=False, description="Include source property in results")