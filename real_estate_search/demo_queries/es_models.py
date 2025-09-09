"""
Elasticsearch data models that match the exact structure stored in indices.

These models represent data as it's actually stored in Elasticsearch,
without any runtime conversions or transformations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from real_estate_search.models import PropertyListing



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