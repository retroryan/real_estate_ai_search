"""
Elasticsearch data models that match the exact structure stored in indices.

These models represent data as it's actually stored in Elasticsearch,
without any runtime conversions or transformations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ESAddress(BaseModel):
    """Address as stored in Elasticsearch."""
    street: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    location: Dict[str, float] = Field(default_factory=dict)  # {"lat": ..., "lon": ...}
    
    model_config = ConfigDict(extra="allow")


class ESParking(BaseModel):
    """Parking info as stored in Elasticsearch."""
    spaces: int = 0
    type: str = "none"
    
    model_config = ConfigDict(extra="allow")


class ESProperty(BaseModel):
    """Property document as stored in Elasticsearch."""
    
    # Core fields
    listing_id: str
    neighborhood_id: str = ""
    
    # Property details - all at top level
    property_type: str  # "single-family", "condo", "townhouse" as stored
    price: float
    bedrooms: int
    bathrooms: float
    square_feet: int
    year_built: int = 0
    lot_size: int = 0
    price_per_sqft: float = 0.0
    
    # Nested objects
    address: ESAddress
    parking: ESParking = Field(default_factory=ESParking)
    
    # Text fields
    description: str = ""
    features: List[str] = Field(default_factory=list)  # This is amenities list
    
    # Metadata
    listing_date: str = ""
    days_on_market: int = 0
    virtual_tour_url: str = ""
    images: List[str] = Field(default_factory=list)
    
    # Embeddings
    embedding: List[float] = Field(default_factory=list)
    embedding_model: str = ""
    embedding_dimension: int = 0
    embedded_at: Optional[datetime] = None
    
    # Allow extra fields from ES response
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ESNeighborhood(BaseModel):
    """Neighborhood document as stored in Elasticsearch."""
    
    neighborhood_id: str
    name: str
    city: str
    state: str
    
    # Statistics
    population: int = 0
    walkability_score: float = 0.0
    school_rating: float = 0.0
    overall_livability_score: float = 0.0
    
    # Location
    location: List[float] = Field(default_factory=list)  # [lon, lat]
    
    # Text fields
    description: str = ""
    amenities: List[str] = Field(default_factory=list)
    demographics: Dict[str, Any] = Field(default_factory=dict)
    
    # Embeddings
    embedding: List[float] = Field(default_factory=list)
    embedding_model: str = ""
    embedding_dimension: int = 0
    embedded_at: Optional[datetime] = None
    
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ESWikipedia(BaseModel):
    """Wikipedia document as stored in Elasticsearch."""
    
    page_id: str
    title: str
    url: str = ""
    
    # Content fields
    long_summary: str = ""
    short_summary: str = ""
    full_content: str = ""
    content_length: int = 0
    
    # Metadata
    categories: List[str] = Field(default_factory=list)
    key_topics: List[str] = Field(default_factory=list)
    
    # Location
    city: str = ""
    state: str = ""
    
    # Quality metrics
    relevance_score: float = 0.0
    article_quality_score: float = 0.0
    article_quality: str = ""
    
    # Embeddings
    embedding: List[float] = Field(default_factory=list)
    embedding_model: str = ""
    embedding_dimension: int = 0
    embedded_at: Optional[datetime] = None
    
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ESSearchHit(BaseModel):
    """Search hit from Elasticsearch."""
    
    index: str = Field(alias="_index")
    id: str = Field(alias="_id")
    score: Optional[float] = Field(None, alias="_score")
    source: Dict[str, Any] = Field(alias="_source")
    
    model_config = ConfigDict(populate_by_name=True, extra="allow")
    
    def to_model(self) -> Optional[BaseModel]:
        """Convert to appropriate ES model based on index."""
        if "properties" in self.index:
            return ESProperty(**self.source)
        elif "neighborhoods" in self.index:
            return ESNeighborhood(**self.source)
        elif "wikipedia" in self.index:
            return ESWikipedia(**self.source)
        return None