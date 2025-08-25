"""
Search request and response models.
Pure Pydantic models for search operations.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator

from .property import Property, PropertyHit, GeoLocation


class SearchMode(str, Enum):
    """Search mode enumeration."""
    standard = "standard"
    semantic = "semantic"
    geographic = "geographic"
    similarity = "similarity"
    lifestyle = "lifestyle"


class SortOrder(str, Enum):
    """Sort order for search results."""
    relevance = "relevance"
    price_asc = "price_asc"
    price_desc = "price_desc"
    newest = "newest"
    distance = "distance"
    bedrooms = "bedrooms"
    square_feet = "square_feet"


class GeoDistanceUnit(str, Enum):
    """Geographic distance units."""
    meters = "meters"
    kilometers = "kilometers"
    miles = "miles"


class PriceRange(BaseModel):
    """Price range filter."""
    
    min_price: Optional[float] = Field(None, gt=0, description="Minimum price")
    max_price: Optional[float] = Field(None, gt=0, description="Maximum price")
    
    @field_validator("max_price")
    @classmethod
    def validate_range(cls, v: Optional[float], info) -> Optional[float]:
        """Ensure max is greater than min."""
        if v is not None and info.data.get("min_price") is not None:
            if v <= info.data["min_price"]:
                raise ValueError("max_price must be greater than min_price")
        return v


class SearchFilters(BaseModel):
    """Search filters for property queries."""
    
    property_types: Optional[List[str]] = Field(None, description="Property types to include")
    price_range: Optional[PriceRange] = Field(None, description="Price range filter")
    min_bedrooms: Optional[int] = Field(None, ge=0, description="Minimum bedrooms")
    max_bedrooms: Optional[int] = Field(None, ge=0, description="Maximum bedrooms")
    min_bathrooms: Optional[float] = Field(None, ge=0, description="Minimum bathrooms")
    min_square_feet: Optional[int] = Field(None, gt=0, description="Minimum square feet")
    max_square_feet: Optional[int] = Field(None, gt=0, description="Maximum square feet")
    year_built_min: Optional[int] = Field(None, ge=1800, description="Minimum year built")
    year_built_max: Optional[int] = Field(None, le=2100, description="Maximum year built")
    cities: Optional[List[str]] = Field(None, description="Cities to include")
    states: Optional[List[str]] = Field(None, description="States to include")
    zip_codes: Optional[List[str]] = Field(None, description="ZIP codes to include")
    features: Optional[List[str]] = Field(None, description="Required features")
    amenities: Optional[List[str]] = Field(None, description="Required amenities")
    exclude_ids: Optional[List[str]] = Field(None, description="Property IDs to exclude")
    
    def to_elasticsearch_query(self) -> Dict[str, Any]:
        """Convert filters to Elasticsearch query clauses."""
        must = []
        filter_clauses = []
        must_not = []
        
        if self.property_types:
            filter_clauses.append({"terms": {"property_type": self.property_types}})
        
        if self.price_range:
            range_query = {}
            if self.price_range.min_price:
                range_query["gte"] = self.price_range.min_price
            if self.price_range.max_price:
                range_query["lte"] = self.price_range.max_price
            if range_query:
                filter_clauses.append({"range": {"price": range_query}})
        
        if self.min_bedrooms is not None:
            filter_clauses.append({"range": {"bedrooms": {"gte": self.min_bedrooms}}})
        if self.max_bedrooms is not None:
            filter_clauses.append({"range": {"bedrooms": {"lte": self.max_bedrooms}}})
        
        if self.min_bathrooms is not None:
            filter_clauses.append({"range": {"bathrooms": {"gte": self.min_bathrooms}}})
        
        if self.min_square_feet is not None:
            filter_clauses.append({"range": {"square_feet": {"gte": self.min_square_feet}}})
        if self.max_square_feet is not None:
            filter_clauses.append({"range": {"square_feet": {"lte": self.max_square_feet}}})
        
        if self.year_built_min is not None:
            filter_clauses.append({"range": {"year_built": {"gte": self.year_built_min}}})
        if self.year_built_max is not None:
            filter_clauses.append({"range": {"year_built": {"lte": self.year_built_max}}})
        
        if self.cities:
            filter_clauses.append({"terms": {"address.city": self.cities}})
        if self.states:
            filter_clauses.append({"terms": {"address.state": self.states}})
        if self.zip_codes:
            filter_clauses.append({"terms": {"address.zip_code": self.zip_codes}})
        
        if self.features:
            for feature in self.features:
                filter_clauses.append({"term": {"features": feature}})
        
        if self.amenities:
            for amenity in self.amenities:
                filter_clauses.append({"term": {"amenities": amenity}})
        
        if self.exclude_ids:
            must_not.append({"ids": {"values": self.exclude_ids}})
        
        return {
            "must": must,
            "filter": filter_clauses,
            "must_not": must_not
        }


class PropertySearchParams(BaseModel):
    """Parameters for searching properties."""
    
    query: Optional[str] = Field(None, description="Natural language search query")
    location: Optional[str] = Field(None, description="City, neighborhood, or area")
    filters: Optional[SearchFilters] = Field(None, description="Search filters")
    mode: SearchMode = Field(SearchMode.standard, description="Search mode")
    sort_by: Optional[SortOrder] = Field(None, description="Sort order")
    max_results: int = Field(20, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Result offset for pagination")
    include_highlights: bool = Field(False, description="Include search highlights")
    include_aggregations: bool = Field(False, description="Include search aggregations")


class GeoSearchParams(BaseModel):
    """Parameters for geographic search."""
    
    center: GeoLocation = Field(..., description="Search center point")
    radius: float = Field(..., gt=0, description="Search radius")
    unit: GeoDistanceUnit = Field(GeoDistanceUnit.miles, description="Distance unit")
    filters: Optional[SearchFilters] = Field(None, description="Additional filters")
    sort_by_distance: bool = Field(True, description="Sort by distance from center")
    max_results: int = Field(20, ge=1, le=100, description="Maximum results")


class SearchResults(BaseModel):
    """Search results response."""
    
    properties: List[Property] = Field(..., description="Found properties")
    total: int = Field(..., ge=0, description="Total matching properties")
    hits: List[PropertyHit] = Field(default_factory=list, description="Detailed hit information")
    aggregations: Optional[Dict[str, Any]] = Field(None, description="Search aggregations")
    search_time_ms: Optional[int] = Field(None, description="Search execution time")
    
    @property
    def scores(self) -> List[float]:
        """Get scores for all properties."""
        return [hit.score or 0.0 for hit in self.hits]
    
    @property
    def took_ms(self) -> Optional[int]:
        """Alias for search_time_ms for backward compatibility."""
        return self.search_time_ms
    
    def get_page_info(self, page_size: int) -> Dict[str, int]:
        """Get pagination information."""
        total_pages = (self.total + page_size - 1) // page_size
        return {
            "total": self.total,
            "total_pages": total_pages,
            "results_count": len(self.properties)
        }


class SimilarPropertiesParams(BaseModel):
    """Parameters for finding similar properties."""
    
    property_id: str = Field(..., description="Reference property ID")
    max_results: int = Field(10, ge=1, le=50, description="Maximum similar properties")
    include_source: bool = Field(False, description="Include source property in results")
    filters: Optional[SearchFilters] = Field(None, description="Additional filters")
    similarity_threshold: float = Field(0.7, ge=0, le=1, description="Minimum similarity score")


class SimilarPropertiesResult(BaseModel):
    """Result for similar properties search."""
    
    reference: Property = Field(..., description="Reference property")
    similar_properties: List[Property] = Field(..., description="Similar properties")
    similarity_scores: Dict[str, float] = Field(default_factory=dict, description="Similarity scores")
    similarity_factors: Dict[str, Any] = Field(default_factory=dict, description="Factors used for similarity")