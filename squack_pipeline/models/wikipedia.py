"""Wikipedia article data models using Pydantic V2."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WikipediaArticle(BaseModel):
    """Wikipedia article model matching SQLite database and Elasticsearch template."""
    
    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    # Core fields from SQLite database
    page_id: int
    title: str
    url: str
    
    # Content fields from SQLite
    short_summary: Optional[str] = None
    long_summary: Optional[str] = None
    summary: Optional[str] = None  # Fallback/legacy field
    content: Optional[str] = None  # Full content if available
    
    # Geographic context from SQLite
    best_city: Optional[str] = None
    best_state: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    location: Optional[List[float]] = None  # [longitude, latitude] for geo_point
    
    # Topics and categories
    key_topics: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    
    # Relevance and metadata
    relevance_score: Optional[float] = Field(default=None, ge=0, le=1)
    
    # Additional metadata fields
    links: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
    section_titles: List[str] = Field(default_factory=list)
    related_pages: List[str] = Field(default_factory=list)
    
    # Timestamps
    last_updated: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    
    # Content metrics
    word_count: Optional[int] = Field(default=None, gt=0)
    language: str = Field(default="en")
    
    # Embedding fields for vector storage
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    embedding_dimension: Optional[int] = None
    embedded_at: Optional[datetime] = None
    
    @field_validator('embedding')
    @classmethod
    def validate_embedding_dimension(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        """Validate embedding dimensions if present."""
        if v is not None and len(v) > 0:
            # Voyage embeddings are typically 1024 or 1536 dimensions
            if len(v) not in [768, 1024, 1536]:  # Added 768 for other models
                raise ValueError(f"Invalid embedding dimension: {len(v)}")
        return v