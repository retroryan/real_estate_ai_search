"""Enriched Wikipedia article model with computed fields and relationships."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, computed_field, ConfigDict


class EnrichedWikipediaArticle(BaseModel):
    """Enriched Wikipedia article with all computed fields and relationships."""
    
    model_config = ConfigDict(frozen=True)
    
    # Core identifiers
    page_id: str = Field(description="Wikipedia page ID")
    title: str = Field(description="Article title")
    
    # Content
    summary: str = Field(description="Article summary")
    content: str = Field(description="Full content")
    content_chunks: list[str] = Field(description="Content chunks for processing")
    
    # Metadata
    categories: list[str] = Field(description="Categories")
    url: str = Field(description="Wikipedia URL")
    word_count: int = Field(description="Word count")
    sentence_count: int = Field(description="Sentence count")
    readability_score: float = Field(description="Readability score")
    
    # Geographic relevance
    is_location: bool = Field(description="Is location article")
    latitude: Optional[float] = Field(default=None, description="Latitude")
    longitude: Optional[float] = Field(default=None, description="Longitude")
    
    # Enhanced geographic data
    location_type: Optional[str] = Field(default=None, description="Type of location")
    location_importance: float = Field(default=0, ge=0, le=10, description="Location importance")
    coverage_radius_miles: Optional[float] = Field(default=None, description="Geographic coverage radius")
    
    # Real estate relevance
    real_estate_relevance_score: float = Field(ge=0, le=1, description="RE relevance")
    property_mentions: int = Field(default=0, description="Property-related mentions")
    neighborhood_mentions: int = Field(default=0, description="Neighborhood mentions")
    housing_content_ratio: float = Field(default=0, ge=0, le=1, description="Housing content ratio")
    
    # Topic analysis
    primary_topics: list[str] = Field(default_factory=list, description="Primary topics")
    secondary_topics: list[str] = Field(default_factory=list, description="Secondary topics")
    entities_mentioned: list[str] = Field(default_factory=list, description="Named entities")
    
    # Sentiment and tone
    sentiment_score: float = Field(default=0, ge=-1, le=1, description="Sentiment -1 to 1")
    objectivity_score: float = Field(default=0.5, ge=0, le=1, description="Objectivity 0 to 1")
    
    # Quality and credibility
    content_quality_score: float = Field(ge=0, le=1, description="Content quality")
    source_credibility: float = Field(default=0.8, ge=0, le=1, description="Source credibility")
    citation_count: int = Field(default=0, description="Number of citations")
    
    # Relationships
    related_neighborhoods: list[str] = Field(default_factory=list, description="Related neighborhoods")
    related_properties: list[str] = Field(default_factory=list, description="Related properties")
    related_pages: list[str] = Field(default_factory=list, description="Related Wikipedia pages")
    
    # Search and embeddings
    embedding_text: str = Field(description="Text for embeddings")
    search_keywords: list[str] = Field(description="Search keywords")
    semantic_tags: list[str] = Field(default_factory=list, description="Semantic tags")
    
    # Temporal relevance
    historical_importance: float = Field(default=0, ge=0, le=10, description="Historical importance")
    contemporary_relevance: float = Field(default=5, ge=0, le=10, description="Current relevance")
    last_modified: Optional[datetime] = Field(default=None, description="Last modified")
    
    # Metadata
    enrichment_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Enrichment time")
    processing_version: str = Field(default="2.0", description="Processing version")
    
    @computed_field
    @property
    def content_density(self) -> float:
        """Calculate content density (words per sentence)."""
        if self.sentence_count > 0:
            return self.word_count / self.sentence_count
        return 0
    
    @computed_field
    @property
    def geographic_specificity(self) -> str:
        """Determine geographic specificity level."""
        if self.is_location and self.latitude and self.longitude:
            if self.coverage_radius_miles and self.coverage_radius_miles < 1:
                return "point"
            elif self.coverage_radius_miles and self.coverage_radius_miles < 10:
                return "neighborhood"
            elif self.coverage_radius_miles and self.coverage_radius_miles < 50:
                return "city"
            return "region"
        return "non_geographic"
    
    @computed_field
    @property
    def information_richness(self) -> float:
        """Calculate information richness score."""
        factors = [
            min(self.word_count / 1000, 10) / 10,  # Length factor
            self.readability_score / 100,  # Readability
            len(self.categories) / 10,  # Category breadth
            self.citation_count / 50,  # Citation depth
            self.content_quality_score,  # Quality
        ]
        return sum(factors) / len(factors)
    
    @computed_field
    @property
    def real_estate_classification(self) -> str:
        """Classify article's real estate relevance."""
        if self.real_estate_relevance_score > 0.8:
            return "highly_relevant"
        elif self.real_estate_relevance_score > 0.5:
            return "relevant"
        elif self.real_estate_relevance_score > 0.2:
            return "somewhat_relevant"
        return "not_relevant"