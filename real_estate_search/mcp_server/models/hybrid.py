"""Hybrid search request and response models using Pydantic."""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class HybridSearchRequest(BaseModel):
    """Hybrid search request model."""
    
    model_config = ConfigDict(extra='forbid')
    
    query: str = Field(..., min_length=1, max_length=500, description="Natural language property search query")
    size: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    include_location_extraction: bool = Field(default=False, description="Include location extraction details in response")
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate query is not empty or only whitespace."""
        if not v.strip():
            raise ValueError("Query cannot be empty or only whitespace")
        return v.strip()


class LocationExtractionMetadata(BaseModel):
    """Location extraction metadata."""
    
    model_config = ConfigDict(extra='forbid')
    
    city: Optional[str] = Field(None, description="Extracted city name")
    state: Optional[str] = Field(None, description="Extracted state name") 
    has_location: bool = Field(..., description="Whether location information was found")
    cleaned_query: str = Field(..., description="Query text with location terms removed")


class HybridSearchMetadata(BaseModel):
    """Hybrid search execution metadata."""
    
    model_config = ConfigDict(extra='forbid')
    
    query: str = Field(..., description="Original search query")
    total_hits: int = Field(..., ge=0, description="Total number of matching properties")
    returned_hits: int = Field(..., ge=0, description="Number of results returned")
    execution_time_ms: int = Field(..., ge=0, description="Total execution time in milliseconds")
    location_extracted: Optional[LocationExtractionMetadata] = Field(None, description="Location extraction details")


class PropertyAddress(BaseModel):
    """Property address information."""
    
    model_config = ConfigDict(extra='forbid')
    
    street: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State abbreviation")
    zip_code: Optional[str] = Field(None, description="ZIP code")


class HybridSearchProperty(BaseModel):
    """Individual property result from hybrid search."""
    
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    
    listing_id: Optional[str] = Field(None, description="Unique listing identifier")
    property_type: Optional[str] = Field(None, description="Type of property (House, Condo, Townhouse, etc.)")
    address: PropertyAddress = Field(..., description="Property address information")
    price: Optional[float] = Field(None, ge=0, description="Property price in USD")
    bedrooms: Optional[int] = Field(None, ge=0, le=20, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, ge=0, le=20, description="Number of bathrooms")
    square_feet: Optional[int] = Field(None, ge=0, le=50000, description="Property square footage")
    description: Optional[str] = Field(None, max_length=500, description="Property description (truncated to 500 chars)")
    features: List[str] = Field(default_factory=list, description="Property features and amenities")
    hybrid_score: Optional[float] = Field(None, ge=0, description="Hybrid search relevance score")
    
    @field_validator('features')
    @classmethod
    def validate_features(cls, v: List[str]) -> List[str]:
        """Validate features list."""
        if not isinstance(v, list):
            return []
        return [str(feature).strip() for feature in v if feature and str(feature).strip()]


class HybridSearchResponse(BaseModel):
    """Hybrid search response model."""
    
    model_config = ConfigDict(extra='forbid')
    
    results: List[HybridSearchProperty] = Field(default_factory=list, description="Property search results")
    metadata: HybridSearchMetadata = Field(..., description="Search execution metadata")
    
    @model_validator(mode='after')
    def validate_results_consistency(self) -> 'HybridSearchResponse':
        """Validate that returned_hits matches actual results count."""
        if len(self.results) != self.metadata.returned_hits:
            raise ValueError(f"Results count ({len(self.results)}) doesn't match metadata ({self.metadata.returned_hits})")
        return self


