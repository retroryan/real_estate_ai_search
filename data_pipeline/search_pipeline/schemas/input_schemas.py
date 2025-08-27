"""Input schema definitions for search pipeline transformations.

These Pydantic models define the expected structure of input DataFrames
from the data pipeline, providing type safety and validation for DataFrame
transformations before indexing to Elasticsearch.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class AddressInput(BaseModel):
    """Address input model matching source data structure."""
    street: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    county: Optional[str] = Field(None, description="County name")
    state: Optional[str] = Field(None, description="State code")
    zip: Optional[str] = Field(None, description="ZIP code")


class CoordinatesInput(BaseModel):
    """Coordinates input model matching source data structure."""
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")


class PropertyDetailsInput(BaseModel):
    """Property details input model matching source data structure."""
    square_feet: Optional[int] = Field(None, description="Square footage")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, description="Number of bathrooms")
    property_type: Optional[str] = Field(None, description="Type of property")
    year_built: Optional[int] = Field(None, description="Year property was built")
    lot_size: Optional[float] = Field(None, description="Lot size in acres")
    stories: Optional[int] = Field(None, description="Number of stories")
    garage_spaces: Optional[int] = Field(None, description="Number of garage spaces")


class PriceHistoryInput(BaseModel):
    """Price history input model."""
    date: Optional[str] = Field(None, description="Price change date")
    price: Optional[float] = Field(None, description="Price at this date")
    event: Optional[str] = Field(None, description="Price event type")


class PropertyInput(BaseModel):
    """Input schema for property DataFrames from data pipeline."""
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",  # Ignore extra fields from enrichment
    )
    
    # Core property identification
    listing_id: str = Field(..., description="Property listing ID")
    neighborhood_id: Optional[str] = Field(None, description="Neighborhood ID")
    
    # Address and location
    address: Optional[AddressInput] = Field(None, description="Address object")
    coordinates: Optional[CoordinatesInput] = Field(None, description="Coordinates object")
    
    # Property details
    property_details: Optional[PropertyDetailsInput] = Field(None, description="Property details object")
    
    # Pricing information
    listing_price: Optional[float] = Field(None, description="Current listing price")
    price_per_sqft: Optional[float] = Field(None, description="Price per square foot")
    
    # Listing information
    description: Optional[str] = Field(None, description="Property description")
    features: List[str] = Field(default_factory=list, description="Property features")
    listing_date: Optional[str] = Field(None, description="Listing date")
    days_on_market: Optional[int] = Field(None, description="Days on market")
    
    # Media
    virtual_tour_url: Optional[str] = Field(None, description="Virtual tour URL")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    
    # Price history
    price_history: List[PriceHistoryInput] = Field(default_factory=list, description="Price history")
    
    # Enrichment fields (may be present)
    enriched_search_text: Optional[str] = Field(None, description="Enriched text for search")
    location_context: Optional[Dict[str, Any]] = Field(None, description="Location context from Wikipedia")
    neighborhood_context: Optional[Dict[str, Any]] = Field(None, description="Neighborhood context")
    nearby_poi: Optional[List[Dict[str, Any]]] = Field(None, description="Nearby points of interest")
    location_scores: Optional[Dict[str, Any]] = Field(None, description="Location quality scores")
    
    # Embedding fields (may be present after embedding generation)
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    embedding_model: Optional[str] = Field(None, description="Embedding model used")
    embedding_dimension: Optional[int] = Field(None, description="Embedding dimension")
    embedded_at: Optional[datetime] = Field(None, description="Embedding timestamp")

    @field_validator('listing_price', 'price_per_sqft')
    @classmethod
    def validate_positive_prices(cls, v: Optional[float]) -> Optional[float]:
        """Ensure prices are positive if provided."""
        if v is not None and v < 0:
            raise ValueError('Price must be non-negative')
        return v


class NeighborhoodCharacteristicsInput(BaseModel):
    """Neighborhood characteristics input model."""
    walkability_score: Optional[int] = Field(None, description="Walkability score")
    transit_score: Optional[int] = Field(None, description="Transit score")
    school_rating: Optional[int] = Field(None, description="School rating")
    safety_rating: Optional[int] = Field(None, description="Safety rating")
    nightlife_score: Optional[int] = Field(None, description="Nightlife score")
    family_friendly_score: Optional[int] = Field(None, description="Family friendly score")


class NeighborhoodDemographicsInput(BaseModel):
    """Neighborhood demographics input model."""
    primary_age_group: Optional[str] = Field(None, description="Primary age group")
    vibe: Optional[str] = Field(None, description="Neighborhood vibe")
    population: Optional[int] = Field(None, description="Population")
    median_household_income: Optional[int] = Field(None, description="Median household income")


class WikipediaCorrelationsInput(BaseModel):
    """Wikipedia correlations input model."""
    primary_wiki_article: Optional[Dict[str, Any]] = Field(None, description="Primary Wikipedia article")


class NeighborhoodInput(BaseModel):
    """Input schema for neighborhood DataFrames from data pipeline."""
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",  # Ignore extra fields from enrichment
    )
    
    # Core identification
    neighborhood_id: str = Field(..., description="Neighborhood ID")
    name: str = Field(..., description="Neighborhood name")
    
    # Location
    city: Optional[str] = Field(None, description="City name")
    county: Optional[str] = Field(None, description="County name")
    state: Optional[str] = Field(None, description="State code")
    coordinates: Optional[CoordinatesInput] = Field(None, description="Coordinates object")
    
    # Description
    description: Optional[str] = Field(None, description="Neighborhood description")
    
    # Characteristics
    characteristics: Optional[NeighborhoodCharacteristicsInput] = Field(None, description="Characteristics object")
    
    # Lifestyle
    amenities: List[str] = Field(default_factory=list, description="Neighborhood amenities")
    lifestyle_tags: List[str] = Field(default_factory=list, description="Lifestyle tags")
    
    # Economics
    median_home_price: Optional[int] = Field(None, description="Median home price")
    price_trend: Optional[str] = Field(None, description="Price trend")
    
    # Demographics
    demographics: Optional[NeighborhoodDemographicsInput] = Field(None, description="Demographics object")
    
    # Wikipedia correlations
    wikipedia_correlations: Optional[WikipediaCorrelationsInput] = Field(None, description="Wikipedia correlations")
    
    # Enrichment fields (may be present)
    enriched_search_text: Optional[str] = Field(None, description="Enriched text for search")
    location_context: Optional[Dict[str, Any]] = Field(None, description="Location context from Wikipedia")
    neighborhood_context: Optional[Dict[str, Any]] = Field(None, description="Neighborhood context")
    nearby_poi: Optional[List[Dict[str, Any]]] = Field(None, description="Nearby points of interest")
    location_scores: Optional[Dict[str, Any]] = Field(None, description="Location quality scores")
    
    # Embedding fields (may be present after embedding generation)
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    embedding_model: Optional[str] = Field(None, description="Embedding model used")
    embedding_dimension: Optional[int] = Field(None, description="Embedding dimension")
    embedded_at: Optional[datetime] = Field(None, description="Embedding timestamp")


class WikipediaInput(BaseModel):
    """Input schema for Wikipedia article DataFrames from data pipeline."""
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",  # Ignore extra fields from enrichment
    )
    
    # Core Wikipedia fields
    page_id: int = Field(..., description="Wikipedia page ID")
    title: str = Field(..., description="Article title")
    url: Optional[str] = Field(None, description="Wikipedia URL")
    
    # Content
    summary: Optional[str] = Field(None, description="Article summary")
    content: Optional[str] = Field(None, description="Full article content")
    
    # Location (if available)
    coordinates: Optional[CoordinatesInput] = Field(None, description="Article location coordinates")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State code")
    
    # Topics
    topics: List[str] = Field(default_factory=list, description="Article topics or categories")
    
    # Metadata
    last_modified: Optional[datetime] = Field(None, description="Last modification date")
    
    # Enrichment fields (may be present)
    enriched_search_text: Optional[str] = Field(None, description="Enriched text for search")
    location_context: Optional[Dict[str, Any]] = Field(None, description="Location context")
    neighborhood_context: Optional[Dict[str, Any]] = Field(None, description="Neighborhood context")
    nearby_poi: Optional[List[Dict[str, Any]]] = Field(None, description="Nearby points of interest")
    location_scores: Optional[Dict[str, Any]] = Field(None, description="Location quality scores")
    
    # Embedding fields (may be present after embedding generation)
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    embedding_model: Optional[str] = Field(None, description="Embedding model used")
    embedding_dimension: Optional[int] = Field(None, description="Embedding dimension")
    embedded_at: Optional[datetime] = Field(None, description="Embedding timestamp")