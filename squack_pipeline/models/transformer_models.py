"""Pydantic models for transformer outputs."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class AddressModel(BaseModel):
    """Address structure for properties."""
    
    model_config = ConfigDict(extra='forbid')
    
    street: Optional[str] = Field(default=None)
    city: Optional[str] = Field(default=None)
    county: Optional[str] = Field(default=None)
    state: Optional[str] = Field(default=None)
    zip_code: Optional[str] = Field(default=None, description="ZIP code (renamed from 'zip')")


class PropertyDetailsModel(BaseModel):
    """Property details structure."""
    
    model_config = ConfigDict(extra='allow')  # Allow extra fields for flexibility
    
    square_feet: Optional[int] = Field(default=None)
    bedrooms: Optional[int] = Field(default=None)
    bathrooms: Optional[float] = Field(default=None)
    property_type: Optional[str] = Field(default=None)
    year_built: Optional[int] = Field(default=None)
    lot_size: Optional[float] = Field(default=None)
    stories: Optional[int] = Field(default=None)
    garage_spaces: Optional[int] = Field(default=None)


class CoordinatesModel(BaseModel):
    """Geographic coordinates."""
    
    model_config = ConfigDict(extra='forbid')
    
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class ParkingModel(BaseModel):
    """Parking information."""
    
    model_config = ConfigDict(extra='allow')
    
    garage: Optional[int] = Field(default=None)
    spaces: Optional[int] = Field(default=None)
    type: Optional[str] = Field(default=None)


class TransformedProperty(BaseModel):
    """Property document transformed for Elasticsearch."""
    
    model_config = ConfigDict(extra='allow')  # Allow extra fields for flexibility
    
    # Core identifiers
    listing_id: str = Field(description="Unique listing identifier")
    neighborhood_id: Optional[str] = Field(default=None)
    
    # Price fields
    price: Optional[float] = Field(default=None)
    price_per_sqft: Optional[float] = Field(default=None)
    calculated_price_per_sqft: Optional[float] = Field(default=None)
    days_on_market: Optional[int] = Field(default=None)
    
    # Nested structures
    address: Optional[AddressModel] = Field(default=None)
    property_details: Optional[PropertyDetailsModel] = Field(default=None)
    coordinates: Optional[CoordinatesModel] = Field(default=None)
    parking: Optional[ParkingModel] = Field(default=None)
    
    # Denormalized fields
    city: Optional[str] = Field(default=None)
    state: Optional[str] = Field(default=None)
    bedrooms: Optional[int] = Field(default=None)
    bathrooms: Optional[float] = Field(default=None)
    property_type: Optional[str] = Field(default=None)
    square_feet: Optional[int] = Field(default=None)
    
    # Location for geo_point
    location: Optional[List[float]] = Field(default=None, description="[lon, lat] for Elasticsearch geo_point")
    
    # Arrays
    features: Optional[List[str]] = Field(default=None)
    images: Optional[List[str]] = Field(default=None)
    price_history: Optional[List[Dict[str, Any]]] = Field(default=None)
    
    # Text fields
    description: Optional[str] = Field(default=None)
    virtual_tour_url: Optional[str] = Field(default=None)
    
    # Metadata
    entity_type: str = Field(default="property")
    gold_processed_at: Optional[datetime] = Field(default=None)
    processing_version: Optional[str] = Field(default=None)
    
    # Embeddings
    embedding: Optional[List[float]] = Field(default=None)
    embedding_model: Optional[str] = Field(default=None)
    embedding_dimension: Optional[int] = Field(default=None)
    
    def to_elasticsearch_dict(self) -> dict:
        """Convert to dictionary for Elasticsearch, handling datetime serialization."""
        data = self.model_dump(exclude_none=True)
        
        # Convert datetime to ISO string
        if 'gold_processed_at' in data and isinstance(data['gold_processed_at'], datetime):
            data['gold_processed_at'] = data['gold_processed_at'].isoformat()
        
        # Convert nested models to dicts
        if 'address' in data and isinstance(data['address'], dict):
            data['address'] = data['address']
        
        return data


class TransformedNeighborhood(BaseModel):
    """Neighborhood document transformed for Elasticsearch."""
    
    model_config = ConfigDict(extra='allow')
    
    # Core identifiers
    neighborhood_id: str = Field(description="Unique neighborhood identifier")
    name: str = Field(description="Neighborhood name")
    city: str = Field(description="City name")
    county: Optional[str] = Field(default=None)
    state: str = Field(description="State code")
    
    # Coordinates
    coordinates: Optional[CoordinatesModel] = Field(default=None)
    location: Optional[List[float]] = Field(default=None, description="[lon, lat] for Elasticsearch geo_point")
    
    # Characteristics
    characteristics: Optional[Dict[str, Any]] = Field(default=None)
    demographics: Optional[Dict[str, Any]] = Field(default=None)
    wikipedia_correlations: Optional[Dict[str, Any]] = Field(default=None)
    
    # Scores
    walkability_score: Optional[int] = Field(default=None)
    transit_score: Optional[int] = Field(default=None)
    school_rating: Optional[float] = Field(default=None)
    safety_rating: Optional[float] = Field(default=None)
    
    # Statistics
    population: Optional[int] = Field(default=None)
    median_household_income: Optional[float] = Field(default=None)
    median_home_price: Optional[float] = Field(default=None)
    
    # Arrays
    amenities: Optional[List[str]] = Field(default=None)
    lifestyle_tags: Optional[List[str]] = Field(default=None)
    
    # Text
    description: Optional[str] = Field(default=None)
    
    # Metadata
    entity_type: str = Field(default="neighborhood")
    gold_processed_at: Optional[datetime] = Field(default=None)
    processing_version: Optional[str] = Field(default=None)
    
    # Embeddings
    embedding: Optional[List[float]] = Field(default=None)
    embedding_model: Optional[str] = Field(default=None)
    embedding_dimension: Optional[int] = Field(default=None)
    
    def to_elasticsearch_dict(self) -> dict:
        """Convert to dictionary for Elasticsearch."""
        data = self.model_dump(exclude_none=True)
        
        # Convert datetime to ISO string
        if 'gold_processed_at' in data and isinstance(data['gold_processed_at'], datetime):
            data['gold_processed_at'] = data['gold_processed_at'].isoformat()
        
        return data


class TransformedWikipedia(BaseModel):
    """Wikipedia document transformed for Elasticsearch."""
    
    model_config = ConfigDict(extra='allow')
    
    # Core identifiers
    id: Optional[str] = Field(default=None)
    page_id: str = Field(description="Wikipedia page ID as string")
    location_id: Optional[str] = Field(default=None)
    title: str = Field(description="Article title")
    
    # URLs and files
    url: Optional[str] = Field(default=None)
    html_file: Optional[str] = Field(default=None)
    article_filename: Optional[str] = Field(default=None, description="For enrichment workflow")
    
    # Content
    extract: Optional[str] = Field(default=None)
    extract_length: Optional[int] = Field(default=None)
    
    # Content enrichment tracking
    content_loaded: bool = Field(default=False)
    
    # Arrays
    categories: Optional[List[str]] = Field(default=None)
    
    # Coordinates
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    location: Optional[List[float]] = Field(default=None, description="[lon, lat] for Elasticsearch geo_point")
    
    # Relevance
    relevance_score: Optional[float] = Field(default=None)
    relevance_category: Optional[str] = Field(default=None)
    
    # Metadata
    depth: Optional[int] = Field(default=None)
    crawled_at: Optional[datetime] = Field(default=None)
    file_hash: Optional[str] = Field(default=None)
    image_url: Optional[str] = Field(default=None)
    links_count: Optional[int] = Field(default=None)
    
    # Processing metadata
    entity_type: str = Field(default="wikipedia")
    gold_processed_at: Optional[datetime] = Field(default=None)
    processing_version: Optional[str] = Field(default=None)
    
    # Embeddings
    embedding: Optional[List[float]] = Field(default=None)
    embedding_model: Optional[str] = Field(default=None)
    embedding_dimension: Optional[int] = Field(default=None)
    
    def to_elasticsearch_dict(self) -> dict:
        """Convert to dictionary for Elasticsearch."""
        data = self.model_dump(exclude_none=True)
        
        # Convert datetime to ISO string
        if 'gold_processed_at' in data and isinstance(data['gold_processed_at'], datetime):
            data['gold_processed_at'] = data['gold_processed_at'].isoformat()
        if 'crawled_at' in data and isinstance(data['crawled_at'], datetime):
            data['crawled_at'] = data['crawled_at'].isoformat()
        
        return data