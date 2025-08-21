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
    county: Optional[str] = None
    state: str
    zip: str
    
    def to_string(self) -> str:
        """Convert address to string format"""
        return f"{self.street}, {self.city}, {self.state} {self.zip}"

class PropertyDetails(BaseModel):
    """Property physical details"""
    property_type: Optional[str] = Field(default="unknown", description="Property type", alias="type")
    bedrooms: int = Field(default=0, ge=0, description="Number of bedrooms")
    bathrooms: float = Field(default=0, ge=0, description="Number of bathrooms")
    square_feet: int = Field(default=0, ge=0, description="Square footage")
    year_built: Optional[int] = Field(default=None, ge=1800, le=2030, description="Year built")
    lot_size: Optional[float] = Field(default=None, ge=0, description="Lot size in acres")
    stories: Optional[int] = Field(default=None, ge=0, description="Number of stories")
    garage_spaces: Optional[int] = Field(default=None, ge=0, description="Number of garage spaces")
    
    class Config:
        populate_by_name = True  # Allow both field name and alias
    
    @validator('property_type', pre=True)
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
            return self.property_details.property_type or 'unknown'
        elif isinstance(self.property_details, dict):
            return self.property_details.get('property_type', self.property_details.get('type', 'unknown'))
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
        elif self.listing_price < 5000000:
            return "3M-5M"
        else:
            return "5M+"


class PriceRange(BaseModel):
    """Price range category"""
    range_id: str = Field(..., description="Price range identifier")
    label: str = Field(..., description="Human-readable label")
    min_price: int = Field(..., ge=0, description="Minimum price")
    max_price: Optional[int] = Field(None, description="Maximum price (None for unlimited)")
    
    @classmethod
    def get_standard_ranges(cls) -> List['PriceRange']:
        """Get standard price range categories"""
        return [
            cls(range_id="range_0_500k", label="Under $500k", min_price=0, max_price=500000),
            cls(range_id="range_500k_1m", label="$500k-$1M", min_price=500000, max_price=1000000),
            cls(range_id="range_1m_2m", label="$1M-$2M", min_price=1000000, max_price=2000000),
            cls(range_id="range_2m_3m", label="$2M-$3M", min_price=2000000, max_price=3000000),
            cls(range_id="range_3m_5m", label="$3M-$5M", min_price=3000000, max_price=5000000),
            cls(range_id="range_5m_plus", label="$5M+", min_price=5000000, max_price=None),
        ]


class Feature(BaseModel):
    """Property feature"""
    feature_id: str = Field(..., description="Feature identifier")
    name: str = Field(..., description="Feature name")
    category: Optional[str] = Field(None, description="Feature category")
    
    @validator('feature_id', pre=True)
    def generate_feature_id(cls, v, values):
        """Generate feature ID from name if not provided"""
        if not v and 'name' in values:
            return values['name'].lower().replace(' ', '_').replace('-', '_')
        return v


class PropertyLoadResult(BaseModel):
    """Result of property loading operation"""
    properties_loaded: int = 0
    nodes_created: int = 0
    
    # Node type counts
    property_nodes: int = 0
    feature_nodes: int = 0
    property_type_nodes: int = 0
    price_range_nodes: int = 0
    
    # Relationship counts
    neighborhood_relationships: int = 0
    city_relationships: int = 0
    county_relationships: int = 0
    feature_relationships: int = 0
    type_relationships: int = 0
    price_range_relationships: int = 0
    
    # Statistics
    unique_features: int = 0
    unique_property_types: int = 0
    avg_features_per_property: float = 0.0
    properties_without_neighborhoods: int = 0
    
    # Errors and warnings
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    duration_seconds: float = 0.0
    success: bool = True
    
    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str):
        """Add a warning message"""
        self.warnings.append(warning)