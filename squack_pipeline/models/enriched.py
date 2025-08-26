"""Enriched data models that combine multiple data sources using Pydantic V2."""

from typing import List, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict, Field

from squack_pipeline.models.property import Property
from squack_pipeline.models.location import Neighborhood, Location
from squack_pipeline.models.wikipedia import WikipediaArticle


class EnrichedProperty(BaseModel):
    """Property enriched with neighborhood and location data."""
    
    model_config = ConfigDict(
        strict=True,
        validate_assignment=True
    )
    
    # Core property data
    property: Property
    
    # Enriched location data
    neighborhood: Optional[Neighborhood] = None
    location: Optional[Location] = None
    
    # Distance calculations
    distance_to_downtown: Optional[float] = Field(default=None, ge=0)
    distance_to_nearest_transit: Optional[float] = Field(default=None, ge=0)
    
    # Calculated metrics
    price_per_bedroom: Optional[float] = Field(default=None, gt=0)
    price_relative_to_neighborhood: Optional[float] = None
    
    # Wikipedia context
    related_wikipedia_articles: List[WikipediaArticle] = Field(default_factory=list)
    
    # Embeddings for similarity search
    description_embedding: Optional[List[float]] = None
    features_embedding: Optional[List[float]] = None
    combined_embedding: Optional[List[float]] = None
    
    def calculate_metrics(self) -> None:
        """Calculate derived metrics from property data."""
        if self.property.property_details.bedrooms > 0:
            self.price_per_bedroom = self.property.listing_price / self.property.property_details.bedrooms
        
        if self.neighborhood and self.neighborhood.median_home_price > 0:
            self.price_relative_to_neighborhood = (
                self.property.listing_price / self.neighborhood.median_home_price
            )


class EnrichedNeighborhood(BaseModel):
    """Neighborhood enriched with additional data."""
    
    model_config = ConfigDict(
        strict=True,
        validate_assignment=True
    )
    
    # Core neighborhood data
    neighborhood: Neighborhood
    
    # Property statistics
    total_properties: int = Field(default=0, ge=0)
    average_price: Optional[float] = Field(default=None, gt=0)
    average_sqft: Optional[float] = Field(default=None, gt=0)
    average_bedrooms: Optional[float] = Field(default=None, ge=0)
    
    # Wikipedia articles
    primary_article: Optional[WikipediaArticle] = None
    related_articles: List[WikipediaArticle] = Field(default_factory=list)
    
    # Embeddings
    description_embedding: Optional[List[float]] = None
    amenities_embedding: Optional[List[float]] = None
    combined_embedding: Optional[List[float]] = None
    
    # Additional metadata
    enrichment_timestamp: Optional[str] = None
    data_quality_score: Optional[float] = Field(default=None, ge=0, le=1)


class PipelineOutput(BaseModel):
    """Final output structure from the pipeline."""
    
    model_config = ConfigDict(
        strict=True,
        extra='forbid'
    )
    
    enriched_properties: List[EnrichedProperty]
    enriched_neighborhoods: List[EnrichedNeighborhood]
    wikipedia_articles: List[WikipediaArticle]
    
    # Pipeline metadata
    pipeline_version: str
    processing_timestamp: str
    total_processing_time_seconds: float = Field(gt=0)
    
    # Data quality metrics
    properties_processed: int = Field(ge=0)
    properties_enriched: int = Field(ge=0)
    embeddings_generated: int = Field(ge=0)
    
    # Configuration used
    config_hash: str
    environment: str = Field(default="development")