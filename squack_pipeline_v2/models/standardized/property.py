"""Standardized property model with cleaned data."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class StandardizedProperty(BaseModel):
    """Standardized property with validated and cleaned data.
    
    This model represents the Silver layer output - data that has been:
    - Cleaned (trimmed, normalized case)
    - Standardized (consistent formats, units)
    - Validated (within reasonable ranges)
    
    NO computed fields or enrichments - those belong in EnrichedProperty.
    """
    
    model_config = ConfigDict(frozen=True)
    
    # Core identifiers (standardized from listing_id)
    listing_id: str = Field(description="Standardized property ID")
    
    # Price information (validated, not computed)
    price: float = Field(gt=0, description="Validated listing price")
    
    # Property details (normalized)
    bedrooms: int = Field(ge=0, le=20, description="Number of bedrooms")
    bathrooms: float = Field(ge=0, le=20, description="Number of bathrooms")
    square_feet: int = Field(gt=0, le=50000, description="Property square footage")
    lot_size_sqft: int = Field(ge=0, description="Lot size (0 if unknown)")
    year_built: Optional[int] = Field(default=None, ge=1800, le=2025, description="Year built")
    property_type: str = Field(description="Normalized property type")
    
    # Location (standardized)
    street_address: str = Field(description="Cleaned street address")
    city: str = Field(description="Standardized city name")
    state: str = Field(pattern="^[A-Z]{2}$", description="2-letter state code")
    zip_code: str = Field(pattern="^\\d{5}$", description="5-digit ZIP code")
    neighborhood_id: Optional[str] = Field(default=None, description="Linked neighborhood")
    
    # Coordinates (validated)
    latitude: float = Field(ge=-90, le=90, description="Valid latitude")
    longitude: float = Field(ge=-180, le=180, description="Valid longitude")
    
    # Features (normalized booleans)
    has_garage: bool = Field(description="Has garage")
    has_pool: bool = Field(description="Has pool")
    has_ac: bool = Field(description="Has air conditioning")
    has_heating: bool = Field(description="Has heating")
    parking_spaces: int = Field(ge=0, description="Parking spaces")
    
    # Text fields (cleaned but not analyzed)
    description: str = Field(description="Cleaned description")
    amenities: str = Field(description="Cleaned amenities string")
    
    # Status (normalized)
    listing_status: str = Field(description="Normalized status (active/pending/sold/inactive)")
    days_on_market: int = Field(ge=0, description="Days on market")
    
