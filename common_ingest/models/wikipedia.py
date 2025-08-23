"""
Pydantic models for enriched Wikipedia data.
"""

from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator

from .base import BaseEnrichedModel, generate_uuid
from .embedding import EmbeddingData


class LocationInfo(BaseModel):
    """Location information for Wikipedia articles."""
    
    city: Optional[str] = Field(None, description="Associated city")
    state: Optional[str] = Field(None, description="Associated state")
    country: str = Field("United States", description="Country")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")


class EnrichedWikipediaArticle(BaseEnrichedModel):
    """
    Enriched Wikipedia article with parsed metadata and optional embeddings.
    
    This model represents a fully processed Wikipedia article with
    all metadata parsed and location information extracted.
    """
    
    # Primary identifiers
    page_id: int = Field(..., gt=0, description="Wikipedia page ID from database")
    article_id: int = Field(..., gt=0, description="Database row ID")
    embedding_id: Optional[str] = Field(
        default_factory=generate_uuid,
        description="UUID for embedding correlation"
    )
    
    # Article content
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Wikipedia URL")
    full_text: str = Field(..., description="Full article text")
    
    # Metadata
    relevance_score: float = Field(0.0, ge=0.0, description="Relevance score")
    location: LocationInfo = Field(default_factory=LocationInfo, description="Location information")
    depth: Optional[int] = Field(None, ge=0, description="Crawl depth")
    
    # Embedding data
    embedding: Optional[EmbeddingData] = Field(None, description="Vector embedding data")
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not empty."""
        if not v or not v.strip():
            raise ValueError("Article title cannot be empty")
        return v.strip()
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")
        v = v.strip()
        if not (v.startswith('http://') or v.startswith('https://')):
            # Assume it's a Wikipedia path and prepend the base URL
            v = f"https://en.wikipedia.org{v}" if v.startswith('/') else f"https://en.wikipedia.org/wiki/{v}"
        return v


class WikipediaSummary(BaseEnrichedModel):
    """
    Wikipedia article summary with extracted topics and location confidence.
    
    This model represents the processed summary from the page_summaries table
    with all JSON fields parsed and structured.
    """
    
    # Primary identifiers
    page_id: int = Field(..., gt=0, description="Wikipedia page ID")
    embedding_id: Optional[str] = Field(
        default_factory=generate_uuid,
        description="UUID for embedding correlation"
    )
    
    # Summary content
    article_title: str = Field(..., description="Article title")
    short_summary: str = Field("", description="Short summary of the article")
    long_summary: str = Field("", description="Long summary of the article")
    
    # Extracted information
    key_topics: List[str] = Field(default_factory=list, description="Parsed key topics")
    best_city: Optional[str] = Field(None, description="Best matching city")
    best_county: Optional[str] = Field(None, description="Best matching county")
    best_state: Optional[str] = Field(None, description="Best matching state")
    overall_confidence: float = Field(0.0, ge=0.0, description="Confidence score")
    
    # Embedding data
    embedding: Optional[EmbeddingData] = Field(None, description="Vector embedding data")
    
    @field_validator('article_title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not empty."""
        if not v or not v.strip():
            raise ValueError("Article title cannot be empty")
        return v.strip()
    
    @field_validator('key_topics')
    @classmethod
    def normalize_topics(cls, v: List[str]) -> List[str]:
        """Normalize and deduplicate topics."""
        if not v:
            return []
        # Remove empty strings, strip whitespace, deduplicate
        topics = [topic.strip() for topic in v if topic and topic.strip()]
        # Preserve order but remove duplicates
        seen = set()
        unique_topics = []
        for topic in topics:
            topic_lower = topic.lower()
            if topic_lower not in seen:
                seen.add(topic_lower)
                unique_topics.append(topic)
        return unique_topics
    
    @field_validator('short_summary', 'long_summary')
    @classmethod
    def clean_summary(cls, v: str) -> str:
        """Clean and normalize summary text."""
        if not v:
            return ""
        # Strip whitespace and normalize line breaks
        v = v.strip()
        # Replace multiple spaces with single space
        v = ' '.join(v.split())
        return v


class WikipediaEnrichmentMetadata(BaseModel):
    """
    Metadata for Wikipedia enrichment operations.
    
    Used to track the enrichment process and any issues encountered.
    """
    
    articles_processed: int = Field(0, ge=0, description="Number of articles processed")
    summaries_processed: int = Field(0, ge=0, description="Number of summaries processed")
    embeddings_correlated: int = Field(0, ge=0, description="Number of embeddings correlated")
    missing_embeddings: List[int] = Field(default_factory=list, description="Page IDs missing embeddings")
    orphaned_embeddings: List[str] = Field(default_factory=list, description="Embedding IDs without source data")
    processing_errors: List[Dict[str, Any]] = Field(default_factory=list, description="Errors during processing")