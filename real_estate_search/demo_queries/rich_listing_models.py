"""
Pydantic models for rich listing demo.
Clean data models with proper validation, no runtime type checking needed.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class AddressModel(BaseModel):
    """Property address with all fields."""
    street: str = Field(default="Address Not Available")
    city: str = Field(default="")
    state: str = Field(default="")
    zip_code: str = Field(default="", alias="zip")
    location: Optional[Dict[str, float]] = Field(default=None)
    
    model_config = ConfigDict(populate_by_name=True)


class ParkingModel(BaseModel):
    """Parking information structure."""
    type: str = Field(default="N/A")
    spaces: int = Field(default=0)
    
    @field_validator('spaces')
    @classmethod
    def validate_spaces(cls, v):
        """Ensure spaces is non-negative."""
        return max(0, v)


class NeighborhoodModel(BaseModel):
    """Neighborhood information with proper typing."""
    neighborhood_id: Optional[str] = Field(default=None)
    name: str = Field(default="Unknown")
    city: str = Field(default="")
    state: str = Field(default="")
    population: Optional[int] = Field(default=None)
    median_income: Optional[int] = Field(default=None)
    walkability_score: Optional[int] = Field(default=None)
    school_rating: Optional[float] = Field(default=None)
    description: Optional[str] = Field(default=None)
    amenities: List[str] = Field(default_factory=list)
    demographics: Optional[Dict[str, Any]] = Field(default=None)
    
    @field_validator('amenities', mode='before')
    @classmethod
    def ensure_amenities_list(cls, v):
        """Ensure amenities is always a list."""
        if v is None:
            return []
        # Check if it's a list-like structure
        try:
            # Try to convert to list
            result = list(v)
            return result
        except (TypeError, ValueError):
            # Not list-like, return empty list
            return []
    
    @field_validator('walkability_score')
    @classmethod
    def validate_walkability(cls, v):
        """Ensure walkability score is in valid range."""
        if v is not None:
            return max(0, min(100, v))
        return v
    
    @field_validator('school_rating')
    @classmethod
    def validate_school_rating(cls, v):
        """Ensure school rating is in valid range."""
        if v is not None:
            return max(0.0, min(5.0, v))
        return v


class WikipediaArticleModel(BaseModel):
    """Wikipedia article information."""
    page_id: str = Field(...)
    title: str = Field(...)
    url: Optional[str] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    city: Optional[str] = Field(default=None)
    state: Optional[str] = Field(default=None)
    relationship_type: str = Field(default="related")
    confidence: float = Field(default=0.0)
    relevance_score: Optional[float] = Field(default=None)


class PropertyModel(BaseModel):
    """Complete property data model with all fields properly typed."""
    listing_id: str = Field(...)
    property_type: str = Field(default="Property")
    price: Optional[float] = Field(default=None)
    bedrooms: Optional[int] = Field(default=None)
    bathrooms: Optional[float] = Field(default=None)
    square_feet: Optional[int] = Field(default=None)
    year_built: Optional[int] = Field(default=None)
    lot_size: Optional[int] = Field(default=None)
    price_per_sqft: Optional[float] = Field(default=None)
    days_on_market: Optional[int] = Field(default=None)
    listing_date: Optional[str] = Field(default=None)
    status: str = Field(default="Active")
    description: Optional[str] = Field(default=None)
    
    # Complex fields with proper models
    address: AddressModel = Field(default_factory=AddressModel)
    parking: Optional[ParkingModel] = Field(default=None)
    features: List[str] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)
    
    # Related data
    neighborhood: Optional[NeighborhoodModel] = Field(default=None)
    wikipedia_articles: List[WikipediaArticleModel] = Field(default_factory=list)
    
    # Additional fields
    hoa_fee: Optional[float] = Field(default=None)
    virtual_tour_url: Optional[str] = Field(default=None)
    images: List[str] = Field(default_factory=list)
    mls_number: Optional[str] = Field(default=None)
    tax_assessed_value: Optional[int] = Field(default=None)
    annual_tax: Optional[float] = Field(default=None)
    
    model_config = ConfigDict(extra="ignore")
    
    @field_validator('features', 'amenities', 'images', mode='before')
    @classmethod
    def ensure_list(cls, v):
        """Ensure field is always a list."""
        if v is None:
            return []
        # Check if it's a list-like structure
        try:
            # Try to convert to list
            result = list(v)
            return result
        except (TypeError, ValueError):
            # Not list-like, return empty list
            return []
    
    @field_validator('parking', mode='before')
    @classmethod
    def parse_parking(cls, v):
        """Parse parking data into ParkingModel."""
        if v is None:
            return None
        # Try to use v as dict directly
        try:
            # Attempt dict operations
            if 'type' in v or 'spaces' in v:
                return v
            # If we can iterate over items, it's dict-like
            return dict(v)
        except (TypeError, AttributeError, ValueError):
            # Not dict-like, create default parking with v as type
            return {'type': str(v), 'spaces': 0}
    
    @field_validator('address', mode='before')
    @classmethod
    def parse_address(cls, v):
        """Ensure address is proper format."""
        if v is None:
            return {}
        # Try to use v as dict directly
        try:
            # Attempt to access dict-like properties
            if 'street' in v or 'city' in v or 'state' in v or 'zip' in v:
                return v
            # Try to convert to dict
            return dict(v)
        except (TypeError, AttributeError, ValueError):
            # Not dict-like, return empty dict
            return {}
    
    @field_validator('neighborhood', mode='before')
    @classmethod
    def parse_neighborhood(cls, v):
        """Parse neighborhood data."""
        if v is None:
            return None
        # Try to use v as dict directly
        try:
            # Check for expected neighborhood fields
            if 'neighborhood_id' in v or 'name' in v or 'walkability_score' in v:
                return v
            # Try to convert to dict
            return dict(v)
        except (TypeError, AttributeError, ValueError):
            # Not dict-like, return None
            return None
    
    def format_price(self) -> str:
        """Format price with proper currency display."""
        if not self.price or self.price == 0:
            return "Price Upon Request"
        return f"${self.price:,.0f}"
    
    def format_listing_date(self) -> str:
        """Format listing date for display."""
        if not self.listing_date:
            return "N/A"
        
        # Try to parse as timestamp
        if self.listing_date.isdigit():
            try:
                # Unix timestamp in milliseconds
                timestamp = int(self.listing_date) / 1000
                return datetime.fromtimestamp(timestamp).strftime("%B %d, %Y")
            except:
                pass
        
        # Try to parse as ISO date
        try:
            dt = datetime.fromisoformat(self.listing_date.replace('Z', '+00:00'))
            return dt.strftime("%B %d, %Y")
        except:
            pass
        
        # Return as-is if can't parse
        return self.listing_date
    
    def get_full_address(self) -> str:
        """Get formatted full address."""
        parts = [self.address.street]
        
        if self.address.city and self.address.state:
            parts.append(f"{self.address.city}, {self.address.state}")
        
        if self.address.zip_code:
            if len(parts) > 1:
                parts[-1] += f" {self.address.zip_code}"
            else:
                parts.append(self.address.zip_code)
        
        return "\n".join(parts)
    
    def get_parking_display(self) -> str:
        """Get formatted parking information."""
        if not self.parking:
            return "N/A"
        
        if self.parking.spaces > 0:
            return f"{self.parking.type} ({self.parking.spaces} spaces)"
        return self.parking.type