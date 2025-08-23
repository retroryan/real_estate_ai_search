"""
Pydantic models for enriched property data.
"""

from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from .base import BaseEnrichedModel, generate_uuid
from .embedding import EmbeddingData


class PropertyType(str, Enum):
    """Property type enumeration."""
    HOUSE = "house"
    CONDO = "condo"
    APARTMENT = "apartment"
    TOWNHOUSE = "townhouse"
    LAND = "land"
    COMMERCIAL = "commercial"
    OTHER = "other"


class PropertyStatus(str, Enum):
    """Property listing status."""
    ACTIVE = "active"
    PENDING = "pending"
    SOLD = "sold"
    OFF_MARKET = "off_market"
    COMING_SOON = "coming_soon"


class GeoLocation(BaseModel):
    """Geographic coordinates."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    
    @field_validator('lat')
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        """Validate latitude is within valid range."""
        if not -90 <= v <= 90:
            raise ValueError(f"Latitude {v} is out of valid range [-90, 90]")
        return v
    
    @field_validator('lon')
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        """Validate longitude is within valid range."""
        if not -180 <= v <= 180:
            raise ValueError(f"Longitude {v} is out of valid range [-180, 180]")
        return v


class GeoPolygon(BaseModel):
    """Geographic polygon for boundaries."""
    points: List[GeoLocation] = Field(..., min_length=3)
    
    @field_validator('points')
    @classmethod
    def validate_polygon(cls, v: List[GeoLocation]) -> List[GeoLocation]:
        """Validate polygon has at least 3 points."""
        if len(v) < 3:
            raise ValueError("Polygon must have at least 3 points")
        return v


class EnrichedAddress(BaseModel):
    """
    Enriched address with normalized city and state.
    """
    street: str = Field(..., description="Street address")
    city: str = Field(..., description="Normalized city name (e.g., 'San Francisco', not 'SF')")
    state: str = Field(..., description="Full state name (e.g., 'California', not 'CA')")
    zip_code: str = Field(..., description="ZIP code")
    coordinates: Optional[GeoLocation] = Field(None, description="Validated geographic coordinates")
    
    @field_validator('city')
    @classmethod
    def validate_city(cls, v: str) -> str:
        """Ensure city is not empty."""
        if not v or not v.strip():
            raise ValueError("City cannot be empty")
        return v.strip()
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Ensure state is not empty."""
        if not v or not v.strip():
            raise ValueError("State cannot be empty")
        return v.strip()


class EnrichedProperty(BaseEnrichedModel):
    """
    Enriched property with all normalization and validation applied.
    
    This model represents a fully enriched property ready for consumption
    by downstream modules. All addresses are normalized, features are
    deduplicated, and optional embeddings can be attached.
    """
    
    # Primary identifiers
    listing_id: str = Field(..., description="Primary property identifier")
    embedding_id: Optional[str] = Field(
        default_factory=generate_uuid,
        description="UUID for embedding correlation"
    )
    
    # Core property details
    property_type: PropertyType = Field(..., description="Type of property")
    price: Decimal = Field(..., gt=0, description="Property price")
    bedrooms: int = Field(..., ge=0, description="Number of bedrooms")
    bathrooms: float = Field(..., ge=0, description="Number of bathrooms")
    square_feet: Optional[int] = Field(None, gt=0, description="Property size in square feet")
    year_built: Optional[int] = Field(None, gt=1800, le=2100, description="Year property was built")
    lot_size: Optional[float] = Field(None, gt=0, description="Lot size in square feet")
    
    # Location
    address: EnrichedAddress = Field(..., description="Normalized and validated address")
    
    # Features and amenities (normalized and deduplicated)
    features: List[str] = Field(default_factory=list, description="Normalized, deduplicated features")
    amenities: List[str] = Field(default_factory=list, description="Property amenities")
    
    # Additional details
    description: Optional[str] = Field(None, description="Property description")
    status: PropertyStatus = Field(PropertyStatus.ACTIVE, description="Listing status")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    virtual_tour_url: Optional[str] = Field(None, description="Virtual tour URL")
    mls_number: Optional[str] = Field(None, description="MLS listing number")
    hoa_fee: Optional[Decimal] = Field(None, ge=0, description="HOA monthly fee")
    
    # Embedding data (populated when include_embeddings=True)
    embedding: Optional[EmbeddingData] = Field(None, description="Vector embedding data")
    
    @field_validator('features', 'amenities')
    @classmethod
    def normalize_string_list(cls, v: List[str]) -> List[str]:
        """Normalize and deduplicate string lists."""
        if not v:
            return []
        # Convert to lowercase, strip whitespace, remove duplicates, sort
        normalized = sorted(list(set(item.lower().strip() for item in v if item and item.strip())))
        return normalized
    
    @field_validator('listing_id')
    @classmethod
    def validate_listing_id(cls, v: str) -> str:
        """Ensure listing_id is not empty."""
        if not v or not v.strip():
            raise ValueError("listing_id cannot be empty")
        return v.strip()


class EnrichedNeighborhood(BaseEnrichedModel):
    """
    Enriched neighborhood data with normalized location information.
    """
    
    # Primary identifiers
    neighborhood_id: str = Field(
        default_factory=generate_uuid,
        description="Primary neighborhood identifier"
    )
    embedding_id: Optional[str] = Field(
        default_factory=generate_uuid,
        description="UUID for embedding correlation"
    )
    
    # Core neighborhood details
    name: str = Field(..., description="Neighborhood name")
    city: str = Field(..., description="Normalized city name")
    state: str = Field(..., description="Full state name")
    
    # Geographic data
    boundaries: Optional[GeoPolygon] = Field(None, description="Neighborhood boundaries")
    center_point: Optional[GeoLocation] = Field(None, description="Center point of neighborhood")
    
    # Demographic and statistical data
    demographics: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Demographic information"
    )
    poi_count: int = Field(0, ge=0, description="Number of points of interest")
    
    # Additional metadata
    description: Optional[str] = Field(None, description="Neighborhood description")
    characteristics: List[str] = Field(default_factory=list, description="Neighborhood characteristics")
    
    # Embedding data
    embedding: Optional[EmbeddingData] = Field(None, description="Vector embedding data")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not empty."""
        if not v or not v.strip():
            raise ValueError("Neighborhood name cannot be empty")
        return v.strip()
    
    @field_validator('characteristics')
    @classmethod
    def normalize_characteristics(cls, v: List[str]) -> List[str]:
        """Normalize and deduplicate characteristics."""
        if not v:
            return []
        normalized = sorted(list(set(item.lower().strip() for item in v if item and item.strip())))
        return normalized