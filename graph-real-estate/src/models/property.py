"""Property-related Pydantic models"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
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
    
    @field_validator('property_type', mode='before')
    @classmethod
    def normalize_type(cls, v):
        """Normalize property type"""
        if v:
            return v.lower().replace('_', '-')
        return "unknown"

class Property(BaseModel):
    """Property model for graph database
    
    This model automatically transforms nested dictionaries into proper Pydantic models
    during instantiation. This ensures type safety throughout the application.
    
    How it works:
    1. When you create a Property with Property(**data), Pydantic's validation pipeline starts
    2. The @model_validator(mode='before') decorator registers transform_all_nested_fields() 
       to run AUTOMATICALLY before field validation
    3. This method transforms any dict inputs into proper Pydantic models (Address, Coordinates, etc.)
    4. After transformation, all fields are guaranteed to be either the proper model type or None
    5. This eliminates the need for isinstance() checks throughout the codebase
    
    Example:
        # Input data with nested dicts (e.g., from JSON)
        data = {
            'listing_id': 'prop-123',
            'neighborhood_id': 'hood-456',
            'address': {'street': '123 Main', 'city': 'SF', 'state': 'CA', 'zip': '94102'},
            'coordinates': {'latitude': 37.7, 'longitude': -122.4},
            'listing_price': 1000000
        }
        
        # Create Property - transform_all_nested_fields runs automatically
        prop = Property(**data)
        
        # Now prop.address is an Address model, not a dict
        # prop.coordinates is a Coordinates model, not a dict
        # All getter methods can safely assume the proper types
    """
    listing_id: str = Field(..., description="Unique listing identifier")
    neighborhood_id: str = Field(..., description="Neighborhood identifier")
    
    # These fields only store proper Pydantic models after validation
    address: Optional[Address] = Field(default=None, description="Property address")
    coordinates: Optional[Coordinates] = Field(default=None, description="Geographic coordinates")
    property_details: Optional[PropertyDetails] = Field(default=None, description="Property details")
    
    listing_price: float = Field(..., gt=0, description="Listing price")
    price_per_sqft: Optional[float] = Field(default=None, gt=0, description="Price per square foot")
    description: Optional[str] = Field(default="", description="Property description")
    features: Optional[List[str]] = Field(default_factory=list, description="Property features")
    listing_date: Optional[str] = Field(default=None, description="Listing date")
    
    # Added fields for graph processing
    city: Optional[str] = None
    state: Optional[str] = None
    
    @model_validator(mode='before')
    @classmethod
    def transform_all_nested_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Transform ALL nested dict/string inputs to proper Pydantic models at input boundary
        
        This method is called AUTOMATICALLY by Pydantic before field validation.
        You never call this method directly - the @model_validator decorator registers it
        with Pydantic's validation pipeline.
        
        The 'mode="before"' parameter means this runs BEFORE individual field validation,
        allowing us to transform raw input data (dicts) into proper Pydantic models.
        
        This is the key to eliminating isinstance() checks throughout the codebase:
        - Input: Nested dicts from JSON, databases, or APIs
        - Output: Proper Pydantic models (Address, Coordinates, PropertyDetails)
        - Result: Type safety - fields are guaranteed to be the correct type or None
        """
        
        # Transform address - handle dict, string, or Address object
        if 'address' in values and values['address'] is not None:
            addr = values['address']
            if isinstance(addr, dict):
                values['address'] = Address(**addr)
            elif isinstance(addr, str):
                # Parse string address into components
                parts = [p.strip() for p in addr.split(',')]
                values['address'] = Address(
                    street=parts[0] if len(parts) > 0 else "",
                    city=parts[1] if len(parts) > 1 else "",
                    state=parts[2][:2] if len(parts) > 2 else "",
                    zip=parts[-1] if len(parts) > 3 else "",
                    county=None
                )
        
        # Transform coordinates - handle dict or Coordinates object
        if 'coordinates' in values and values['coordinates'] is not None:
            coords = values['coordinates']
            if isinstance(coords, dict):
                values['coordinates'] = Coordinates(**coords)
        
        # Transform property details - handle dict or PropertyDetails object
        if 'property_details' in values and values['property_details'] is not None:
            details = values['property_details']
            if isinstance(details, dict):
                values['property_details'] = PropertyDetails(**details)
        
        return values
    
    def get_address_string(self) -> str:
        """Get address as formatted string
        
        Returns the full address string if address exists, empty string otherwise.
        The address field is guaranteed to be an Address model or None after validation.
        """
        return self.address.to_string() if self.address else ""
    
    def get_coordinates_dict(self) -> Dict[str, float]:
        """Get coordinates as dictionary for APIs and serialization
        
        Returns coordinates in lat/lng format for compatibility with mapping APIs.
        The coordinates field is guaranteed to be a Coordinates model or None after validation.
        """
        if self.coordinates:
            return {"lat": self.coordinates.latitude, "lng": self.coordinates.longitude}
        return {"lat": 0.0, "lng": 0.0}
    
    def get_property_type(self) -> str:
        """Get property type from details
        
        Returns the property type if details exist, 'unknown' otherwise.
        The property_details field is guaranteed to be a PropertyDetails model or None after validation.
        """
        return self.property_details.property_type if self.property_details else 'unknown'
    
    def get_bedrooms(self) -> int:
        """Get number of bedrooms
        
        Returns the bedroom count from property details, 0 if details don't exist.
        """
        return self.property_details.bedrooms if self.property_details else 0
    
    def get_bathrooms(self) -> float:
        """Get number of bathrooms
        
        Returns the bathroom count from property details, 0 if details don't exist.
        """
        return self.property_details.bathrooms if self.property_details else 0
    
    def get_square_feet(self) -> int:
        """Get square footage
        
        Returns the square footage from property details, 0 if details don't exist.
        """
        return self.property_details.square_feet if self.property_details else 0
    
    def get_year_built(self) -> Optional[int]:
        """Get year built
        
        Returns the year built from property details, None if details don't exist or year is not set.
        """
        return self.property_details.year_built if self.property_details else None
    
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
    
    @field_validator('feature_id', mode='before')
    @classmethod
    def generate_feature_id(cls, v, info):
        """Generate feature ID from name if not provided"""
        if not v and 'name' in info.data:
            return info.data['name'].lower().replace(' ', '_').replace('-', '_')
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
    wikipedia_property_relationships: int = 0
    
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