"""Property data models using Pydantic V2."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Address(BaseModel):
    """Address information for a property."""
    
    model_config = ConfigDict(strict=True)
    
    street: str
    city: str
    county: str
    state: str
    zip: str


class Coordinates(BaseModel):
    """Geographic coordinates."""
    
    model_config = ConfigDict(strict=True)
    
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class PropertyDetails(BaseModel):
    """Detailed property specifications."""
    
    model_config = ConfigDict(strict=True)
    
    square_feet: int = Field(gt=0)
    bedrooms: int = Field(ge=0)
    bathrooms: float = Field(ge=0)
    property_type: str
    year_built: int = Field(ge=1800, le=2100)
    lot_size: float = Field(ge=0)
    stories: int = Field(ge=1)
    garage_spaces: int = Field(ge=0)


class PriceHistory(BaseModel):
    """Price history event for a property."""
    
    model_config = ConfigDict(strict=True)
    
    date: date
    price: float = Field(gt=0)
    event: str


class Property(BaseModel):
    """Real estate property model."""
    
    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    listing_id: str
    neighborhood_id: Optional[str] = None
    address: Address
    coordinates: Coordinates
    property_details: PropertyDetails
    listing_price: float = Field(gt=0)
    price_per_sqft: float = Field(gt=0)
    description: str
    features: List[str] = Field(default_factory=list)
    listing_date: date
    days_on_market: int = Field(ge=0)
    virtual_tour_url: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    price_history: List[PriceHistory] = Field(default_factory=list)
    
    @field_validator('listing_price', 'price_per_sqft')
    @classmethod
    def validate_positive_price(cls, v: float) -> float:
        """Ensure price values are positive."""
        if v <= 0:
            raise ValueError('Price must be positive')
        return v
    
    @field_validator('features', 'images')
    @classmethod
    def validate_list_not_none(cls, v: Optional[List[str]]) -> List[str]:
        """Ensure lists are not None."""
        return v if v is not None else []