"""Wikipedia article data models using Pydantic."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


class WikipediaArticle(BaseModel):
    """Wikipedia article model."""
    
    model_config = ConfigDict(extra='forbid')
    
    # Core fields
    page_id: str = Field(..., description="Wikipedia page ID")
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Wikipedia URL")
    
    # Content fields
    long_summary: Optional[str] = Field(None, description="Long summary of article")
    short_summary: Optional[str] = Field(None, description="Short summary of article")
    full_content: Optional[str] = Field(None, description="Full article content")
    content_length: Optional[int] = Field(None, ge=0, description="Content length in characters")
    
    # Loading status
    content_loaded: bool = Field(default=False, description="Whether content is loaded")
    content_loaded_at: Optional[datetime] = Field(None, description="Content load timestamp")
    
    # Location fields
    best_city: Optional[str] = Field(None, description="Best matching city")
    best_state: Optional[str] = Field(None, description="Best matching state")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    
    # Metadata
    key_topics: List[str] = Field(default_factory=list, description="Key topics")
    categories: List[str] = Field(default_factory=list, description="Article categories")
    article_quality: Optional[str] = Field(None, description="Article quality rating")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    relevance_score: Optional[float] = Field(None, ge=0, le=1, description="Relevance score")
    
    # Embedding fields
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    embedding_model: Optional[str] = Field(None, description="Embedding model used")
    embedding_dimension: Optional[int] = Field(None, description="Embedding dimension")
    embedded_at: Optional[datetime] = Field(None, description="Embedding timestamp")
    
    @field_validator('latitude')
    @classmethod
    def validate_latitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not -90 <= v <= 90:
            raise ValueError(f"Latitude must be between -90 and 90, got {v}")
        return v
    
    @field_validator('longitude')
    @classmethod
    def validate_longitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not -180 <= v <= 180:
            raise ValueError(f"Longitude must be between -180 and 180, got {v}")
        return v
    
    @field_validator('best_state')
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) != 2:
            raise ValueError(f"State must be 2-letter code, got {v}")
        return v.upper() if v else v


class WikipediaSearchResult(BaseModel):
    """Wikipedia search result with metadata."""
    
    model_config = ConfigDict(extra='forbid')
    
    article: WikipediaArticle = Field(..., description="Wikipedia article data")
    score: float = Field(..., description="Relevance score")
    highlights: Optional[Dict[str, List[str]]] = Field(None, description="Highlighted matches")
    explanation: Optional[str] = Field(None, description="Score explanation")
    
    
class WikipediaChunk(BaseModel):
    """Wikipedia article chunk for chunked search."""
    
    model_config = ConfigDict(extra='forbid')
    
    page_id: str = Field(..., description="Wikipedia page ID")
    chunk_id: str = Field(..., description="Unique chunk ID")
    title: str = Field(..., description="Article title")
    chunk_text: str = Field(..., description="Chunk text content")
    chunk_index: int = Field(..., ge=0, description="Chunk index in article")
    total_chunks: int = Field(..., ge=1, description="Total chunks in article")
    
    # Metadata from parent article
    best_city: Optional[str] = Field(None, description="Best matching city")
    best_state: Optional[str] = Field(None, description="Best matching state")
    categories: List[str] = Field(default_factory=list, description="Article categories")
    
    # Embedding
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    
    
class WikipediaChunkSearchResult(BaseModel):
    """Wikipedia chunk search result."""
    
    model_config = ConfigDict(extra='forbid')
    
    chunk: WikipediaChunk = Field(..., description="Wikipedia chunk data")
    score: float = Field(..., description="Relevance score")
    highlights: Optional[Dict[str, List[str]]] = Field(None, description="Highlighted matches")