"""
Unified property listing model.

This is the single, authoritative PropertyListing model that serves as the 
sole source of truth for property data throughout the application.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field

from .address import Address
from .enums import PropertyType, PropertyStatus, ParkingType


class Parking(BaseModel):
    """Parking information for a property."""
    spaces: int = Field(default=0, ge=0, description="Number of parking spaces")
    type: ParkingType = Field(default=ParkingType.NONE, description="Type of parking")
    
    model_config = ConfigDict(extra="ignore", use_enum_values=True)


class PropertyListing(BaseModel):
    """
    Unified property listing model.
    
    This model consolidates all property-related fields from various models
    throughout the codebase into a single, comprehensive structure.
    """
    
    # === Core Identification ===
    listing_id: str = Field(..., description="Unique listing identifier")
    neighborhood_id: Optional[str] = Field(default="", description="Associated neighborhood ID")
    
    # === Property Classification ===
    property_type: PropertyType = Field(..., description="Type of property")
    status: PropertyStatus = Field(default=PropertyStatus.ACTIVE, description="Listing status")
    
    # === Location ===
    address: Address = Field(..., description="Property address")
    school_district: Optional[str] = Field(default=None, description="School district")
    
    # === Pricing ===
    price: float = Field(..., ge=0, description="Listing price")
    price_per_sqft: Optional[float] = Field(default=0.0, ge=0, description="Price per square foot")
    hoa_fee: Optional[float] = Field(default=None, ge=0, description="HOA monthly fee")
    tax_annual: Optional[float] = Field(default=None, ge=0, description="Annual property tax")
    last_sold_price: Optional[float] = Field(default=None, ge=0, description="Last sale price")
    
    # === Physical Attributes ===
    bedrooms: int = Field(default=0, ge=0, le=50, description="Number of bedrooms")
    bathrooms: float = Field(default=0.0, ge=0, le=50, description="Number of bathrooms")
    square_feet: int = Field(default=0, ge=0, le=100000, description="Square footage")
    lot_size: int = Field(default=0, ge=0, description="Lot size in square feet")
    year_built: Optional[int] = Field(default=0, ge=1600, le=2100, description="Year built")
    stories: Optional[int] = Field(default=None, ge=1, le=10, description="Number of stories")
    
    # === Parking ===
    parking: Optional[Parking] = Field(default_factory=Parking, description="Parking information")
    
    # === Descriptions and Features ===
    title: Optional[str] = Field(default=None, max_length=200, description="Listing title")
    description: str = Field(default="", description="Full property description")
    features: List[str] = Field(default_factory=list, description="Property features/amenities", alias="amenities")
    highlights: List[str] = Field(default_factory=list, description="Key highlights")
    
    # === Dates and Timeline ===
    listing_date: Optional[str] = Field(default="", description="Date listed (string for ES compatibility)")
    list_date: Optional[datetime] = Field(default=None, description="Date listed (datetime)")
    last_sold_date: Optional[datetime] = Field(default=None, description="Last sale date")
    days_on_market: int = Field(default=0, ge=0, description="Days on market")
    
    # === Media ===
    images: List[str] = Field(default_factory=list, description="Image URLs")
    photo_count: Optional[int] = Field(default=None, ge=0, description="Number of photos")
    virtual_tour_url: Optional[str] = Field(default="", description="Virtual tour URL")
    
    # === Embeddings and Search Metadata ===
    embedding: List[float] = Field(default_factory=list, description="Vector embedding")
    embedding_model: str = Field(default="", description="Embedding model used")
    embedding_dimension: int = Field(default=0, description="Embedding dimension")
    embedded_at: Optional[datetime] = Field(default=None, description="When embedded")
    
    # === Search Result Metadata ===
    score: Optional[float] = Field(default=None, alias="_score", description="Search relevance score")
    distance_km: Optional[float] = Field(default=None, description="Distance from search center")
    search_highlights: Optional[Dict[str, List[str]]] = Field(
        default=None, 
        alias="highlights",
        description="Search result highlights"
    )
    
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        extra="allow",  # Allow extra fields from Elasticsearch
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )
    
    # === Validators ===
    
    @field_validator('price_per_sqft', mode='before')
    @classmethod
    def calculate_price_per_sqft(cls, v, values):
        """Calculate price per sqft if not provided."""
        if v is None or v == 0:
            price = values.data.get('price', 0)
            sqft = values.data.get('square_feet', 0)
            if price > 0 and sqft > 0:
                return price / sqft
        return v or 0.0
    
    @field_validator('listing_date', mode='before')
    @classmethod
    def convert_listing_date(cls, v):
        """Ensure listing_date is a string for ES compatibility."""
        # Try to call isoformat if it exists (datetime object)
        try:
            return v.isoformat()
        except (AttributeError, TypeError):
            # Not a datetime, return as string
            return v or ""
    
    # === Display Properties ===
    
    @computed_field
    @property
    def display_price(self) -> str:
        """Format price for display."""
        return f"${self.price/1000000:.1f}M"
    
    @computed_field
    @property
    def display_property_type(self) -> str:
        """Format property type for display."""
        # Map internal values to display values
        display_map = {
            "single-family": "Single Family",
            "condo": "Condo",
            "townhouse": "Townhouse",
            "multi-family": "Multi-Family",
            "apartment": "Apartment",
            "land": "Land",
            "other": "Other"
        }
        return display_map.get(self.property_type, self.property_type.replace("-", " ").title())
    
    @computed_field
    @property
    def summary(self) -> str:
        """Generate property summary line."""
        parts = []
        
        # Bedrooms/Bathrooms
        if self.bedrooms or self.bathrooms:
            bed_bath = []
            if self.bedrooms:
                bed_bath.append(f"{self.bedrooms}bd")
            if self.bathrooms:
                bath_int = int(self.bathrooms)
                if self.bathrooms % 1 == 0.5:
                    bed_bath.append(f"{bath_int}.5ba")
                else:
                    bed_bath.append(f"{bath_int}ba")
            parts.append("/".join(bed_bath))
        
        # Square feet
        if self.square_feet:
            parts.append(f"{self.square_feet:,} sqft")
        
        # Property type
        parts.append(self.display_property_type)
        
        return " | ".join(parts) if parts else "Property details not available"
    
    @computed_field
    @property
    def has_score(self) -> bool:
        """Check if this property has a relevance score from search."""
        return self.score is not None and self.score > 0
    
    @computed_field
    @property
    def rooms_total(self) -> Optional[int]:
        """Calculate total rooms."""
        if self.bedrooms is not None and self.bathrooms is not None:
            return self.bedrooms + int(self.bathrooms)
        return None
    
    @computed_field
    @property
    def parking_display(self) -> str:
        """Format parking information for display."""
        if self.parking and self.parking.spaces > 0:
            return f"{self.parking.spaces} {self.parking.type} space{'s' if self.parking.spaces > 1 else ''}"
        return "No parking"
    
    @computed_field
    @property
    def listing_date_display(self) -> str:
        """Format listing date for display."""
        if self.list_date:
            return self.list_date.strftime("%B %d, %Y")
        elif self.listing_date:
            try:
                dt = datetime.fromisoformat(self.listing_date.replace('Z', '+00:00'))
                return dt.strftime("%B %d, %Y")
            except (ValueError, AttributeError):
                return self.listing_date
        return "N/A"
    
    # === Elasticsearch Compatibility Methods ===
    
    def to_elasticsearch(self) -> Dict[str, Any]:
        """Convert to Elasticsearch document format."""
        doc = self.model_dump(
            exclude={'score', 'distance_km', 'search_highlights', 'list_date', 'last_sold_date'},
            exclude_none=True,
            by_alias=False
        )
        
        # Ensure dates are strings for ES
        if self.list_date:
            doc['listing_date'] = self.list_date.isoformat()
        if self.last_sold_date:
            doc['last_sold_date'] = self.last_sold_date.isoformat()
        if self.embedded_at:
            doc['embedded_at'] = self.embedded_at.isoformat()
            
        return doc
    
    @classmethod
    def from_elasticsearch(cls, source: Dict[str, Any], score: Optional[float] = None) -> "PropertyListing":
        """Create from Elasticsearch document."""
        # Add score if provided
        if score is not None:
            source['_score'] = score
        
        # Handle date conversions
        for date_field in ['list_date', 'last_sold_date', 'embedded_at']:
            if date_field in source and source[date_field]:
                try:
                    # Try to parse as ISO format string
                    source[date_field] = datetime.fromisoformat(
                        str(source[date_field]).replace('Z', '+00:00')
                    )
                except (ValueError, AttributeError, TypeError):
                    # Keep original value if not parseable
                    pass
        
        return cls(**source)