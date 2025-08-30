"""Enriched property model with computed fields and relationships."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, computed_field, ConfigDict


class EnrichedProperty(BaseModel):
    """Enriched property with all computed fields and relationships."""
    
    model_config = ConfigDict(frozen=True)
    
    # Core identifiers
    listing_id: str = Field(description="Property ID")
    
    # Base fields from standardized
    price: float = Field(gt=0, description="Listing price")
    bedrooms: int = Field(ge=0, description="Number of bedrooms")
    bathrooms: float = Field(ge=0, description="Number of bathrooms")
    square_feet: int = Field(gt=0, description="Square footage")
    lot_size_sqft: Optional[int] = Field(default=None, description="Lot size")
    year_built: Optional[int] = Field(default=None, description="Year built")
    property_type: str = Field(description="Property type")
    
    # Location
    street_address: str = Field(description="Street address")
    city: str = Field(description="City")
    state: str = Field(description="State")
    zip_code: str = Field(description="ZIP code")
    latitude: float = Field(description="Latitude")
    longitude: float = Field(description="Longitude")
    
    # Features
    has_garage: bool = Field(description="Has garage")
    has_pool: bool = Field(description="Has pool")
    has_ac: bool = Field(description="Has AC")
    has_heating: bool = Field(description="Has heating")
    parking_spaces: int = Field(description="Parking spaces")
    
    # Text fields
    description: str = Field(description="Description")
    amenities: list[str] = Field(description="Amenities")
    
    # Enriched neighborhood data
    neighborhood_id: Optional[str] = Field(default=None, description="Neighborhood ID")
    neighborhood_name: Optional[str] = Field(default=None, description="Neighborhood name")
    neighborhood_median_price: Optional[float] = Field(default=None, description="Neighborhood median price")
    neighborhood_walkability: Optional[int] = Field(default=None, description="Walkability score")
    neighborhood_school_score: Optional[float] = Field(default=None, description="School score")
    neighborhood_crime_score: Optional[float] = Field(default=None, description="Crime score")
    
    # Market analysis
    price_per_sqft: float = Field(gt=0, description="Price per square foot")
    price_vs_neighborhood: Optional[float] = Field(default=None, description="Price vs neighborhood median %")
    market_heat_score: float = Field(ge=0, le=10, description="Market heat score 0-10")
    value_score: float = Field(ge=0, le=10, description="Value score 0-10")
    
    # Property scores
    overall_condition_score: float = Field(ge=0, le=10, description="Condition score")
    amenity_score: float = Field(ge=0, le=10, description="Amenity score")
    location_score: float = Field(ge=0, le=10, description="Location score")
    
    # Investment metrics
    estimated_rent: float = Field(ge=0, description="Estimated monthly rent")
    rent_yield: float = Field(ge=0, description="Annual rent yield %")
    price_appreciation_forecast: float = Field(description="1-year price forecast %")
    
    # Search and embedding
    embedding_text: str = Field(description="Text for embedding generation")
    search_keywords: list[str] = Field(description="Search keywords")
    
    # Related entities
    nearby_properties: list[str] = Field(default_factory=list, description="Nearby property IDs")
    similar_properties: list[str] = Field(default_factory=list, description="Similar property IDs")
    wikipedia_articles: list[str] = Field(default_factory=list, description="Related Wikipedia pages")
    
    # Metadata
    data_quality_score: float = Field(ge=0, le=1, description="Data quality")
    enrichment_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Enrichment time")
    
    @computed_field
    @property
    def property_age(self) -> Optional[int]:
        """Calculate property age."""
        if self.year_built:
            return datetime.now().year - self.year_built
        return None
    
    @computed_field
    @property
    def rooms_total(self) -> float:
        """Total room count."""
        return self.bedrooms + self.bathrooms
    
    @computed_field
    @property
    def is_luxury(self) -> bool:
        """Determine if luxury property."""
        return (
            self.price > 1000000 or
            self.square_feet > 5000 or
            (self.amenity_score > 8 and self.location_score > 8)
        )
    
    @computed_field
    @property
    def investment_grade(self) -> str:
        """Calculate investment grade."""
        if self.rent_yield > 8 and self.value_score > 7:
            return "A"
        elif self.rent_yield > 6 and self.value_score > 5:
            return "B"
        elif self.rent_yield > 4:
            return "C"
        return "D"