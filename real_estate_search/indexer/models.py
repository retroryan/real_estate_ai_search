"""
Pydantic models for type-safe data validation.
All data structures in the system use these models.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from pydantic.types import NonNegativeInt, NonNegativeFloat, PositiveFloat

from .enums import PropertyType, PropertyStatus, ParkingType


class GeoLocation(BaseModel):
    """Geographic coordinates."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")


class Address(BaseModel):
    """Property address information."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    street: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(..., pattern=r"^\d{5}(-\d{4})?$")
    location: Optional[GeoLocation] = None
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Ensure state is uppercase."""
        return v.upper()


class Neighborhood(BaseModel):
    """Neighborhood information."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    neighborhood_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    walkability_score: Optional[int] = Field(None, ge=0, le=100)
    school_rating: Optional[float] = Field(None, ge=0, le=10)


class Parking(BaseModel):
    """Parking information."""
    spaces: NonNegativeInt = Field(default=0)
    type: Optional[ParkingType] = None


class Property(BaseModel):
    """Complete property data model."""
    model_config = ConfigDict(
        str_strip_whitespace=True
    )
    
    # Required fields
    listing_id: str = Field(..., min_length=1, max_length=50)
    property_type: PropertyType
    price: PositiveFloat
    bedrooms: NonNegativeInt
    bathrooms: NonNegativeFloat
    address: Address
    
    # Optional fields
    square_feet: Optional[NonNegativeInt] = None
    year_built: Optional[int] = Field(None, ge=1800, le=datetime.now().year)
    lot_size: Optional[NonNegativeFloat] = None
    neighborhood: Optional[Neighborhood] = None
    description: Optional[str] = Field(None, max_length=5000)
    features: List[str] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)
    status: PropertyStatus = PropertyStatus.ACTIVE
    listing_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    days_on_market: Optional[NonNegativeInt] = None
    price_per_sqft: Optional[PositiveFloat] = None
    hoa_fee: Optional[NonNegativeFloat] = None
    parking: Optional[Parking] = None
    virtual_tour_url: Optional[str] = Field(None, max_length=500)
    images: List[str] = Field(default_factory=list, max_length=50)
    mls_number: Optional[str] = Field(None, max_length=50)
    tax_assessed_value: Optional[NonNegativeFloat] = None
    annual_tax: Optional[NonNegativeFloat] = None
    search_tags: Optional[str] = None
    
    @field_validator('features', 'amenities')
    @classmethod
    def lowercase_list(cls, v: List[str]) -> List[str]:
        """Normalize features and amenities to lowercase."""
        return [item.lower().strip() for item in v if item.strip()]
    
    @model_validator(mode='after')
    def calculate_derived_fields(self) -> 'Property':
        """Calculate price per square foot and days on market."""
        # Calculate price per square foot
        if self.square_feet and self.square_feet > 0:
            self.price_per_sqft = round(self.price / self.square_feet, 2)
        
        # Calculate days on market
        if self.listing_date:
            delta = datetime.now() - self.listing_date
            self.days_on_market = delta.days
        
        # Set last updated
        if not self.last_updated:
            self.last_updated = datetime.now()
        
        # Generate search tags
        tags = []
        tags.append(self.property_type.value)
        tags.extend(self.features)
        tags.extend(self.amenities)
        self.search_tags = " ".join(tags)
        
        return self


class PropertyDocument(BaseModel):
    """Elasticsearch document representation of a property."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        use_enum_values=True,
        populate_by_name=True
    )
    
    # All fields from Property, flattened for ES
    listing_id: str
    property_type: str
    price: float
    bedrooms: int
    bathrooms: float
    square_feet: Optional[int] = None
    year_built: Optional[int] = None
    lot_size: Optional[float] = None
    
    # Address as nested object
    address: Dict[str, Any]
    
    # Neighborhood as nested object
    neighborhood: Optional[Dict[str, Any]] = None
    
    # Other fields
    description: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)
    status: str
    listing_date: Optional[str] = None
    last_updated: str
    days_on_market: Optional[int] = None
    price_per_sqft: Optional[float] = None
    hoa_fee: Optional[float] = None
    parking: Optional[Dict[str, Any]] = None
    virtual_tour_url: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    mls_number: Optional[str] = None
    tax_assessed_value: Optional[float] = None
    annual_tax: Optional[float] = None
    search_tags: Optional[str] = None
    
    @classmethod
    def from_property(cls, prop: Property) -> 'PropertyDocument':
        """Convert Property model to ES document."""
        doc_dict = {
            'listing_id': prop.listing_id,
            'property_type': prop.property_type.value,
            'price': prop.price,
            'bedrooms': prop.bedrooms,
            'bathrooms': prop.bathrooms,
            'square_feet': prop.square_feet,
            'year_built': prop.year_built,
            'lot_size': prop.lot_size,
            'address': {
                'street': prop.address.street,
                'city': prop.address.city,
                'state': prop.address.state,
                'zip_code': prop.address.zip_code,
            },
            'description': prop.description,
            'features': prop.features,
            'amenities': prop.amenities,
            'status': prop.status.value,
            'listing_date': prop.listing_date.isoformat() if prop.listing_date else None,
            'last_updated': prop.last_updated.isoformat() if prop.last_updated else datetime.now().isoformat(),
            'days_on_market': prop.days_on_market,
            'price_per_sqft': prop.price_per_sqft,
            'hoa_fee': prop.hoa_fee,
            'virtual_tour_url': prop.virtual_tour_url,
            'images': prop.images,
            'mls_number': prop.mls_number,
            'tax_assessed_value': prop.tax_assessed_value,
            'annual_tax': prop.annual_tax,
            'search_tags': prop.search_tags,
        }
        
        # Add location if available
        if prop.address.location:
            doc_dict['address']['location'] = {
                'lat': prop.address.location.lat,
                'lon': prop.address.location.lon
            }
        
        # Add neighborhood if available
        if prop.neighborhood:
            doc_dict['neighborhood'] = {
                'neighborhood_id': prop.neighborhood.neighborhood_id,
                'name': prop.neighborhood.name,
                'walkability_score': prop.neighborhood.walkability_score,
                'school_rating': prop.neighborhood.school_rating,
            }
        
        # Add parking if available
        if prop.parking:
            doc_dict['parking'] = {
                'spaces': prop.parking.spaces,
                'type': prop.parking.type.value if prop.parking.type else None
            }
        
        return cls(**doc_dict)


class IndexStats(BaseModel):
    """Statistics for indexing operations."""
    success: NonNegativeInt = 0
    failed: NonNegativeInt = 0
    total: NonNegativeInt = 0
    duration_seconds: Optional[float] = None
    errors: List[Dict[str, Any]] = Field(default_factory=list)