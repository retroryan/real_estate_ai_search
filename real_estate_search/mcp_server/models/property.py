"""
Property data models using Pydantic.
Clean, type-safe models with no Marshmallow dependencies.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict


class PropertyType(str, Enum):
    """Property type enumeration."""
    single_family = "single_family"
    condo = "condo"
    townhouse = "townhouse"
    multi_family = "multi_family"
    land = "land"
    other = "other"


class GeoLocation(BaseModel):
    """Geographic coordinates."""
    
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    
    model_config = ConfigDict(frozen=True)


class Address(BaseModel):
    """Property address information."""
    
    street: str = Field(..., min_length=1, description="Street address")
    city: str = Field(..., min_length=1, description="City name")
    state: str = Field(..., min_length=2, max_length=2, description="State code")
    zip_code: str = Field(..., pattern=r"^\d{5}(-\d{4})?$", description="ZIP code")
    location: Optional[GeoLocation] = Field(None, description="Geographic coordinates")
    
    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Validate and uppercase state code."""
        return v.upper()


class Property(BaseModel):
    """Complete property information."""
    
    id: str = Field(..., description="Unique property ID")
    listing_id: str = Field(..., description="MLS listing ID")
    property_type: PropertyType = Field(..., description="Type of property")
    price: float = Field(..., gt=0, description="Listing price")
    bedrooms: int = Field(..., ge=0, description="Number of bedrooms")
    bathrooms: float = Field(..., ge=0, description="Number of bathrooms")
    square_feet: Optional[int] = Field(None, gt=0, description="Living area square footage")
    lot_size: Optional[float] = Field(None, gt=0, description="Lot size in acres")
    year_built: Optional[int] = Field(None, ge=1800, le=2100, description="Year built")
    address: Address = Field(..., description="Property address")
    description: Optional[str] = Field(None, max_length=5000, description="Property description")
    features: List[str] = Field(default_factory=list, description="Property features")
    amenities: List[str] = Field(default_factory=list, description="Property amenities")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    listing_date: Optional[datetime] = Field(None, description="Date listed")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    
    # Enrichment fields
    location_quality_score: Optional[float] = Field(None, ge=0, le=100, description="Location quality score")
    neighborhood_desirability: Optional[float] = Field(None, ge=0, le=10, description="Neighborhood score")
    
    @field_validator("features", "amenities")
    @classmethod
    def clean_list_items(cls, v: List[str]) -> List[str]:
        """Clean and deduplicate list items."""
        return list(set(item.strip() for item in v if item.strip()))
    
    @field_validator("images")
    @classmethod
    def validate_image_urls(cls, v: List[str]) -> List[str]:
        """Validate image URLs are properly formatted."""
        cleaned = []
        for url in v:
            url = url.strip()
            if url and (url.startswith("http://") or url.startswith("https://")):
                cleaned.append(url)
        return cleaned
    
    def get_display_address(self) -> str:
        """Get formatted display address."""
        return f"{self.address.street}, {self.address.city}, {self.address.state} {self.address.zip_code}"
    
    @property
    def price_per_sqft(self) -> Optional[float]:
        """Calculate price per square foot."""
        if self.square_feet and self.square_feet > 0:
            return self.price / self.square_feet
        return None
    
    def get_summary(self) -> str:
        """Get property summary for display."""
        return (
            f"{self.bedrooms} bed, {self.bathrooms} bath {self.property_type.value.replace('_', ' ')} "
            f"in {self.address.city}, {self.address.state} - ${self.price:,.0f}"
        )


class PropertyHit(BaseModel):
    """Search result hit for a property."""
    
    property: Property = Field(..., description="Property data")
    score: Optional[float] = Field(None, description="Search relevance score")
    distance: Optional[float] = Field(None, description="Distance from search center")
    highlights: Dict[str, List[str]] = Field(default_factory=dict, description="Search highlights")
    
    def get_sort_key(self, sort_by: str = "score") -> float:
        """Get sort key for ordering results."""
        if sort_by == "price":
            return self.property.price
        elif sort_by == "distance" and self.distance is not None:
            return self.distance
        elif sort_by == "score" and self.score is not None:
            return -self.score  # Negative for descending order
        return 0