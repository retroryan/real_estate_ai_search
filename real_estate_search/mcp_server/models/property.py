"""Property data models using Pydantic."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


class Address(BaseModel):
    """Property address model."""
    
    model_config = ConfigDict(extra='forbid')
    
    street: str = Field(..., description="Street address")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State code")
    zip_code: str = Field(..., description="ZIP code")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v: str) -> str:
        if len(v) != 2:
            raise ValueError(f"State must be 2-letter code, got {v}")
        return v.upper()
    
    @field_validator('latitude')
    @classmethod
    def validate_latitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not -90 <= v <= 90:
            raise ValueError(f"Latitude must be between -90 and 90, got {v}")
        return v
    
    @field_validator('longitude')
    @classmethod
    def validate_longitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not -180 <= v <= 180:
            raise ValueError(f"Longitude must be between -180 and 180, got {v}")
        return v


class Neighborhood(BaseModel):
    """Neighborhood information model."""
    
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(..., description="Neighborhood ID")
    name: str = Field(..., description="Neighborhood name")
    walkability_score: Optional[int] = Field(None, ge=0, le=100, description="Walkability score")
    school_rating: Optional[float] = Field(None, ge=0, le=10, description="School rating")


class Parking(BaseModel):
    """Parking information model."""
    
    model_config = ConfigDict(extra='forbid')
    
    spaces: int = Field(default=0, ge=0, description="Number of parking spaces")
    type: Optional[str] = Field(None, description="Parking type (garage, carport, street)")


class LocationContext(BaseModel):
    """Location context enriched from Wikipedia."""
    
    model_config = ConfigDict(extra='forbid')
    
    wikipedia_page_id: Optional[str] = Field(None, description="Wikipedia page ID")
    wikipedia_title: Optional[str] = Field(None, description="Wikipedia article title")
    location_summary: Optional[str] = Field(None, description="Location summary")
    historical_significance: Optional[str] = Field(None, description="Historical significance")
    key_topics: List[str] = Field(default_factory=list, description="Key topics")
    cultural_features: List[str] = Field(default_factory=list, description="Cultural features")
    recreational_features: List[str] = Field(default_factory=list, description="Recreational features")
    transportation: List[str] = Field(default_factory=list, description="Transportation options")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Confidence score")


class Property(BaseModel):
    """Complete property model."""
    
    model_config = ConfigDict(extra='forbid')
    
    # Core fields
    listing_id: str = Field(..., description="Unique listing ID")
    property_type: str = Field(..., description="Property type (House, Condo, etc.)")
    price: float = Field(..., ge=0, description="Property price")
    bedrooms: int = Field(..., ge=0, description="Number of bedrooms")
    bathrooms: float = Field(..., ge=0, description="Number of bathrooms")
    square_feet: int = Field(..., ge=0, description="Square footage")
    year_built: Optional[int] = Field(None, description="Year built")
    lot_size: Optional[int] = Field(None, ge=0, description="Lot size in square feet")
    
    # Complex fields
    address: Address = Field(..., description="Property address")
    neighborhood: Optional[Neighborhood] = Field(None, description="Neighborhood info")
    
    # Description and features
    description: str = Field(..., description="Property description")
    features: List[str] = Field(default_factory=list, description="Property features")
    amenities: List[str] = Field(default_factory=list, description="Property amenities")
    
    # Status and dates
    status: str = Field(default="active", description="Listing status")
    listing_date: Optional[datetime] = Field(None, description="Listing date")
    last_updated: Optional[datetime] = Field(None, description="Last update date")
    days_on_market: Optional[int] = Field(None, ge=0, description="Days on market")
    
    # Financial
    price_per_sqft: Optional[float] = Field(None, ge=0, description="Price per square foot")
    hoa_fee: Optional[float] = Field(None, ge=0, description="HOA fee")
    tax_assessed_value: Optional[int] = Field(None, ge=0, description="Tax assessed value")
    annual_tax: Optional[float] = Field(None, ge=0, description="Annual tax")
    
    # Additional fields
    parking: Optional[Parking] = Field(None, description="Parking information")
    virtual_tour_url: Optional[str] = Field(None, description="Virtual tour URL")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    mls_number: Optional[str] = Field(None, description="MLS number")
    
    # Enrichment fields
    location_context: Optional[LocationContext] = Field(None, description="Location context")
    search_tags: List[str] = Field(default_factory=list, description="Search tags")
    
    # Embedding fields
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    embedding_model: Optional[str] = Field(None, description="Embedding model used")
    embedding_dimension: Optional[int] = Field(None, description="Embedding dimension")
    embedded_at: Optional[datetime] = Field(None, description="Embedding timestamp")
    
    @field_validator('property_type')
    @classmethod
    def validate_property_type(cls, v: str) -> str:
        valid_types = ["House", "Condo", "Townhouse", "Multi-Family", "Land", "Other"]
        if v not in valid_types:
            raise ValueError(f"Invalid property type: {v}. Must be one of {valid_types}")
        return v
    
    @field_validator('bathrooms')
    @classmethod
    def validate_bathrooms(cls, v: float) -> float:
        # Allow half bathrooms
        if v % 0.5 != 0:
            raise ValueError(f"Bathrooms must be in increments of 0.5, got {v}")
        return v


class PropertySearchResult(BaseModel):
    """Property search result with metadata."""
    
    model_config = ConfigDict(extra='forbid')
    
    property: Property = Field(..., description="Property data")
    score: float = Field(..., description="Relevance score")
    highlights: Optional[Dict[str, List[str]]] = Field(None, description="Highlighted matches")
    explanation: Optional[str] = Field(None, description="Score explanation")