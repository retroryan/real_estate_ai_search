"""
Wikipedia article model.

This is the single, authoritative WikipediaArticle model that serves as the 
sole source of truth for Wikipedia article data throughout the application.
This model exactly matches the Elasticsearch template at:
real_estate_search/elasticsearch/templates/wikipedia.json
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, computed_field


class WikipediaArticle(BaseModel):
    """
    Wikipedia article model matching the Elasticsearch index mapping.
    
    This model represents the complete structure of a Wikipedia document
    as stored in Elasticsearch, serving as the single source of truth
    for all Wikipedia-related operations in the application.
    """
    
    # Primary identifiers
    page_id: str = Field(..., description="Wikipedia page ID")
    title: str = Field(..., description="Article title")
    url: Optional[str] = Field(None, description="Article URL")
    article_filename: Optional[str] = Field(None, description="Local file path for article HTML")
    
    # Content fields
    long_summary: Optional[str] = Field(None, description="Long summary of article")
    short_summary: Optional[str] = Field(None, description="Short summary of article")
    full_content: Optional[str] = Field(None, description="Full article content (HTML stripped)")
    content_length: Optional[int] = Field(None, ge=0, description="Length of content")
    content_loaded: Optional[bool] = Field(False, description="Whether full content has been loaded")
    content_loaded_at: Optional[datetime] = Field(None, description="When content was loaded")
    
    # Location fields
    city: Optional[str] = Field(None, description="Associated city")
    state: Optional[str] = Field(None, description="Associated state")
    location: Optional[Dict[str, float]] = Field(None, description="Geo point {lat, lon}")
    
    # Neighborhood association
    neighborhood_ids: List[str] = Field(default_factory=list, description="Associated neighborhood IDs")
    neighborhood_names: List[str] = Field(default_factory=list, description="Associated neighborhood names")
    primary_neighborhood_name: Optional[str] = Field(None, description="Primary neighborhood name")
    neighborhood_count: Optional[int] = Field(0, description="Number of associated neighborhoods")
    has_neighborhood_association: Optional[bool] = Field(False, description="Has neighborhood associations")
    
    # Classification and metadata
    key_topics: List[str] = Field(default_factory=list, description="Key topics/tags")
    categories: List[str] = Field(default_factory=list, description="Wikipedia categories")
    article_quality: Optional[str] = Field(None, description="Article quality classification")
    article_quality_score: Optional[float] = Field(None, description="Article quality score")
    relevance_score: Optional[float] = Field(None, description="Location relevance score")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Embedding fields
    embedding: Optional[List[float]] = Field(None, description="Dense vector embedding", exclude=True)
    embedding_model: Optional[str] = Field(None, description="Model used for embedding")
    embedding_dimension: Optional[int] = Field(None, description="Embedding vector dimension")
    embedded_at: Optional[datetime] = Field(None, description="When embedding was created")
    
    # Search result fields (optional, populated during search)
    score: Optional[float] = Field(None, description="Elasticsearch relevance score")
    confidence: float = Field(0.0, description="Search result confidence score")  # TODO: Fix proper confidence calculation
    relationship_type: Optional[str] = Field(None, description="Relationship type to property")  # TODO: Fix proper relationship mapping
    
    model_config = ConfigDict(extra="ignore")
    
    @computed_field  # type: ignore
    @property
    def location_string(self) -> str:
        """Get location as string."""
        if self.city and self.state:
            return f"{self.city}, {self.state}"
        return self.city or self.state or "Location unknown"
    
    @computed_field  # type: ignore
    @property
    def has_content(self) -> bool:
        """Check if article has content loaded."""
        return bool(self.full_content)
    
    @computed_field  # type: ignore
    @property
    def id(self) -> str:
        """Get document ID for ES operations."""
        return self.page_id
    
    @classmethod
    def from_elasticsearch(cls, hit: dict) -> "WikipediaArticle":
        """
        Create WikipediaArticle from Elasticsearch hit.
        
        Args:
            hit: Elasticsearch hit dictionary with _source and metadata
            
        Returns:
            WikipediaArticle instance
        """
        source = hit.get('_source', {})
        
        # Add score if present
        if '_score' in hit:
            source['score'] = hit['_score']
        
        # Handle location conversion if present
        if 'location' in source and source['location']:
            if isinstance(source['location'], dict):
                source['location'] = {
                    'lat': source['location'].get('lat'),
                    'lon': source['location'].get('lon')
                }
        
        # Handle datetime fields - they come as strings from ES
        for field in ['content_loaded_at', 'last_updated', 'embedded_at']:
            if field in source and source[field]:
                # Keep as string for now, Pydantic will handle conversion
                pass
        
        return cls(**source)