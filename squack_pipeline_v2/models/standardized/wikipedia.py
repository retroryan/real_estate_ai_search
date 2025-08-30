"""Standardized Wikipedia article model with cleaned data."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class StandardizedWikipediaArticle(BaseModel):
    """Standardized Wikipedia article with validated and cleaned data."""
    
    model_config = ConfigDict(frozen=True)
    
    # Core identifiers
    page_id: str = Field(description="Wikipedia page ID")
    title: str = Field(description="Cleaned article title")
    
    # Content (processed)
    summary: str = Field(description="Cleaned summary")
    content: str = Field(description="Cleaned full content")
    content_chunks: list[str] = Field(default_factory=list, description="Content split into chunks")
    
    # Metadata (normalized)
    categories: list[str] = Field(default_factory=list, description="Normalized categories")
    url: str = Field(description="Canonical Wikipedia URL")
    
    # Statistics (calculated)
    word_count: int = Field(ge=0, description="Word count")
    sentence_count: int = Field(ge=0, description="Sentence count")
    readability_score: float = Field(ge=0, le=100, description="Readability score")
    
    # Geographic relevance
    is_location: bool = Field(default=False, description="Is location-related")
    latitude: Optional[float] = Field(default=None, ge=-90, le=90, description="Location latitude")
    longitude: Optional[float] = Field(default=None, ge=-180, le=180, description="Location longitude")
    
    # Relationships
    related_neighborhoods: list[str] = Field(default_factory=list, description="Related neighborhood IDs")
    related_pages: list[str] = Field(default_factory=list, description="Related Wikipedia page IDs")
    
    # Content features
    has_infobox: bool = Field(default=False, description="Has infobox")
    has_coordinates: bool = Field(default=False, description="Has geographic coordinates")
    image_urls: list[str] = Field(default_factory=list, description="Cleaned image URLs")
    
    # Quality metrics
    content_quality_score: float = Field(ge=0, le=1, description="Content quality score")
    relevance_score: float = Field(ge=0, le=1, description="Geographic relevance score")
    
    # Metadata
    last_modified: Optional[datetime] = Field(default=None, description="Last modification date")
    processing_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Processing time")