"""Raw property model matching source data."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class RawProperty(BaseModel):
    """Raw property data as it appears in source files."""
    
    model_config = ConfigDict(frozen=True)
    
    # Core identifiers
    listing_id: str = Field(description="Unique property identifier")
    
    # Price information
    listing_price: float = Field(description="Property listing price")
    price_per_sqft: Optional[float] = Field(default=None, description="Price per square foot")
    
    # Property details
    bedrooms: int = Field(description="Number of bedrooms")
    bathrooms: float = Field(description="Number of bathrooms")
    square_feet: int = Field(description="Property square footage")
    lot_size: Optional[int] = Field(default=None, description="Lot size in square feet")
    year_built: Optional[int] = Field(default=None, description="Year property was built")
    property_type: str = Field(description="Type of property")
    
    # Location
    address: str = Field(description="Street address")
    city: str = Field(description="City")
    state: str = Field(description="State code")
    zip_code: str = Field(description="ZIP code")
    neighborhood_id: Optional[str] = Field(default=None, description="Associated neighborhood ID")
    
    # Coordinates
    latitude: float = Field(description="Latitude coordinate")
    longitude: float = Field(description="Longitude coordinate")
    
    # Features
    description: Optional[str] = Field(default=None, description="Property description")
    amenities: Optional[str] = Field(default=None, description="Property amenities")
    parking_spaces: Optional[int] = Field(default=None, description="Number of parking spaces")
    has_garage: Optional[bool] = Field(default=None, description="Has garage")
    has_pool: Optional[bool] = Field(default=None, description="Has pool")
    has_ac: Optional[bool] = Field(default=None, description="Has air conditioning")
    has_heating: Optional[bool] = Field(default=None, description="Has heating")
    
    # Status
    listing_status: Optional[str] = Field(default=None, description="Current listing status")
    days_on_market: Optional[int] = Field(default=None, description="Days on market")
    
    # URLs
    listing_url: Optional[str] = Field(default=None, description="Listing URL")
    image_url: Optional[str] = Field(default=None, description="Primary image URL")