"""
Business entity models for Property Finder.

Provides models for properties, neighborhoods, and Wikipedia articles.
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

from .core import BaseEnrichedModel, generate_uuid
from .enums import PropertyType, PropertyStatus
from .geographic import EnrichedAddress, GeoPolygon, GeoLocation, LocationInfo


class EmbeddingData(BaseModel):
    """
    Minimal model for embedding data from ChromaDB.
    
    Represents a single embedding with its metadata, designed for
    efficient correlation between source data and vector embeddings.
    """
    
    embedding_id: str = Field(..., description="Unique identifier for the embedding")
    vector: Optional[List[float]] = Field(None, description="Embedding vector (optional for performance)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata from ChromaDB")
    chunk_index: Optional[int] = Field(None, description="Chunk index for multi-chunk documents")


class EnrichedProperty(BaseEnrichedModel):
    """
    Enriched property with all normalization and validation applied.
    
    This model represents a fully enriched property ready for consumption
    by downstream modules. All addresses are normalized, features are
    deduplicated, and optional embeddings can be attached.
    """
    
    # Primary identifiers
    listing_id: str = Field(..., description="Primary property identifier")
    embedding_id: Optional[str] = Field(
        default_factory=generate_uuid,
        description="UUID for embedding correlation"
    )
    
    # Core property details
    property_type: PropertyType = Field(..., description="Type of property")
    price: Decimal = Field(..., gt=0, description="Property price")
    bedrooms: int = Field(..., ge=0, description="Number of bedrooms")
    bathrooms: float = Field(..., ge=0, description="Number of bathrooms")
    square_feet: Optional[int] = Field(None, gt=0, description="Property size in square feet")
    year_built: Optional[int] = Field(None, gt=1800, le=2100, description="Year property was built")
    lot_size: Optional[float] = Field(None, gt=0, description="Lot size in square feet")
    
    # Location
    address: EnrichedAddress = Field(..., description="Normalized and validated address")
    
    # Features and amenities (normalized and deduplicated)
    features: List[str] = Field(default_factory=list, description="Normalized, deduplicated features")
    amenities: List[str] = Field(default_factory=list, description="Property amenities")
    
    # Additional details
    description: Optional[str] = Field(None, description="Property description")
    status: PropertyStatus = Field(PropertyStatus.ACTIVE, description="Listing status")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    virtual_tour_url: Optional[str] = Field(None, description="Virtual tour URL")
    mls_number: Optional[str] = Field(None, description="MLS listing number")
    hoa_fee: Optional[Decimal] = Field(None, ge=0, description="HOA monthly fee")
    
    # Embedding fields for ChromaDB correlation
    embeddings: Optional[List[EmbeddingData]] = Field(None, description="Correlated embeddings from ChromaDB")
    embedding_count: int = Field(0, description="Number of embeddings")
    has_embeddings: bool = Field(False, description="Whether embeddings are available")
    correlation_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence in embedding correlation")
    
    @field_validator('features', 'amenities')
    @classmethod
    def normalize_string_list(cls, v: List[str]) -> List[str]:
        """Normalize and deduplicate string lists."""
        if not v:
            return []
        # Convert to lowercase, strip whitespace, remove duplicates, sort
        normalized = sorted(list(set(item.lower().strip() for item in v if item and item.strip())))
        return normalized
    
    @field_validator('listing_id')
    @classmethod
    def validate_listing_id(cls, v: str) -> str:
        """Ensure listing_id is not empty."""
        if not v or not v.strip():
            raise ValueError("listing_id cannot be empty")
        return v.strip()


class EnrichedNeighborhood(BaseEnrichedModel):
    """
    Enriched neighborhood data with normalized location information.
    """
    
    # Primary identifiers
    neighborhood_id: str = Field(
        default_factory=generate_uuid,
        description="Primary neighborhood identifier"
    )
    embedding_id: Optional[str] = Field(
        default_factory=generate_uuid,
        description="UUID for embedding correlation"
    )
    
    # Core neighborhood details
    name: str = Field(..., description="Neighborhood name")
    city: str = Field(..., description="Normalized city name")
    state: str = Field(..., description="Full state name")
    
    # Geographic data
    boundaries: Optional[GeoPolygon] = Field(None, description="Neighborhood boundaries")
    center_point: Optional[GeoLocation] = Field(None, description="Center point of neighborhood")
    
    # Demographic and statistical data
    demographics: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Demographic information"
    )
    poi_count: int = Field(0, ge=0, description="Number of points of interest")
    
    # Additional metadata
    description: Optional[str] = Field(None, description="Neighborhood description")
    characteristics: List[str] = Field(default_factory=list, description="Neighborhood characteristics")
    
    # Embedding fields for ChromaDB correlation
    embeddings: Optional[List[EmbeddingData]] = Field(None, description="Correlated embeddings from ChromaDB")
    embedding_count: int = Field(0, description="Number of embeddings")
    has_embeddings: bool = Field(False, description="Whether embeddings are available")
    correlation_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence in embedding correlation")


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