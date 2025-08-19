"""Property-related Pydantic models"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

class PropertyType(str, Enum):
    """Property type categories"""
    SINGLE_FAMILY = "single-family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    MULTI_FAMILY = "multi-family"
    UNKNOWN = "unknown"

class Coordinates(BaseModel):
    """Geographic coordinates"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude", alias="lat")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude", alias="lng")
    
    class Config:
        populate_by_name = True  # Allow both field name and alias

class Address(BaseModel):
    """Property address"""
    street: str
    city: str
    state: str
    zip: str
    
    def to_string(self) -> str:
        """Convert address to string format"""
        return f"{self.street}, {self.city}, {self.state} {self.zip}"

class PropertyDetails(BaseModel):
    """Property physical details"""
    type: Optional[str] = Field(default="unknown", description="Property type")
    bedrooms: int = Field(default=0, ge=0, description="Number of bedrooms")
    bathrooms: float = Field(default=0, ge=0, description="Number of bathrooms")
    square_feet: int = Field(default=0, ge=0, description="Square footage")
    year_built: Optional[int] = Field(default=None, ge=1800, le=2025, description="Year built")
    
    @validator('type')
    def normalize_type(cls, v):
        """Normalize property type"""
        if v:
            return v.lower().replace('_', '-')
        return "unknown"

class Property(BaseModel):
    """Property model for graph database"""
    listing_id: str = Field(..., description="Unique listing identifier")
    neighborhood_id: str = Field(..., description="Neighborhood identifier")
    address: Optional[Dict[str, str] | str] = Field(default=None, description="Property address")
    coordinates: Optional[Coordinates | Dict[str, float]] = Field(default=None, description="Geographic coordinates")
    property_details: Optional[PropertyDetails | Dict[str, Any]] = Field(default=None, description="Property details")
    listing_price: float = Field(..., gt=0, description="Listing price")
    price_per_sqft: Optional[float] = Field(default=None, gt=0, description="Price per square foot")
    description: Optional[str] = Field(default="", description="Property description")
    features: Optional[List[str]] = Field(default_factory=list, description="Property features")
    listing_date: Optional[str] = Field(default=None, description="Listing date")
    
    # Added fields for graph processing
    city: Optional[str] = None
    state: Optional[str] = None
    
    @validator('coordinates', pre=True)
    def parse_coordinates(cls, v):
        """Parse coordinates from dict if needed"""
        if isinstance(v, dict):
            return Coordinates(**v)
        return v
    
    @validator('property_details', pre=True)
    def parse_details(cls, v):
        """Parse property details from dict if needed"""
        if isinstance(v, dict):
            return PropertyDetails(**v)
        return v
    
    def get_address_string(self) -> str:
        """Get address as string"""
        if isinstance(self.address, dict):
            return f"{self.address.get('street', '')} {self.address.get('city', '')} {self.address.get('state', '')} {self.address.get('zip', '')}".strip()
        elif isinstance(self.address, str):
            return self.address
        return ""
    
    def get_coordinates_dict(self) -> Dict[str, float]:
        """Get coordinates as dict"""
        if isinstance(self.coordinates, Coordinates):
            return {"lat": self.coordinates.latitude, "lng": self.coordinates.longitude}
        elif isinstance(self.coordinates, dict):
            # Handle both lat/lng and latitude/longitude keys
            if 'latitude' in self.coordinates:
                return {"lat": self.coordinates.get('latitude', 0), "lng": self.coordinates.get('longitude', 0)}
            else:
                return {"lat": self.coordinates.get('lat', 0), "lng": self.coordinates.get('lng', 0)}
        return {"lat": 0.0, "lng": 0.0}
    
    def get_property_type(self) -> str:
        """Get property type from details"""
        if isinstance(self.property_details, PropertyDetails):
            return self.property_details.type or 'unknown'
        elif isinstance(self.property_details, dict):
            return self.property_details.get('type', 'unknown')
        return 'unknown'
    
    def get_bedrooms(self) -> int:
        """Get number of bedrooms"""
        if isinstance(self.property_details, PropertyDetails):
            return self.property_details.bedrooms
        elif isinstance(self.property_details, dict):
            return self.property_details.get('bedrooms', 0)
        return 0
    
    def get_bathrooms(self) -> float:
        """Get number of bathrooms"""
        if isinstance(self.property_details, PropertyDetails):
            return self.property_details.bathrooms
        elif isinstance(self.property_details, dict):
            return self.property_details.get('bathrooms', 0)
        return 0
    
    def get_square_feet(self) -> int:
        """Get square footage"""
        if isinstance(self.property_details, PropertyDetails):
            return self.property_details.square_feet
        elif isinstance(self.property_details, dict):
            return self.property_details.get('square_feet', 0)
        return 0
    
    def get_year_built(self) -> Optional[int]:
        """Get year built"""
        if isinstance(self.property_details, PropertyDetails):
            return self.property_details.year_built
        elif isinstance(self.property_details, dict):
            return self.property_details.get('year_built')
        return None
    
    def calculate_price_range(self) -> str:
        """Calculate price range category"""
        if self.listing_price < 500000:
            return "0-500k"
        elif self.listing_price < 1000000:
            return "500k-1M"
        elif self.listing_price < 2000000:
            return "1M-2M"
        elif self.listing_price < 3000000:
            return "2M-3M"
        else:
            return "3M+"