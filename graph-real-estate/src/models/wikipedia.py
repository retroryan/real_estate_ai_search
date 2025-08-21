"""Pydantic models for Wikipedia entities"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


class WikipediaArticle(BaseModel):
    """Wikipedia article with LLM-processed summaries"""
    page_id: int = Field(..., description="Wikipedia page ID")
    title: str = Field(..., description="Article title")
    short_summary: str = Field(default="", description="Concise summary (~350-550 chars)")
    long_summary: str = Field(default="", description="Detailed summary (~1000-1300 chars)")
    key_topics: List[str] = Field(default_factory=list, description="LLM-extracted key topics")
    
    # Geographic metadata
    best_city: Optional[str] = None
    best_county: Optional[str] = None
    best_state: Optional[str] = None
    location_type: Optional[str] = None
    
    # Quality metrics
    overall_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Additional metadata
    url: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    last_updated: Optional[datetime] = Field(default_factory=datetime.now)
    
    @validator('key_topics', pre=True)
    def parse_key_topics(cls, v):
        """Parse key topics from string if needed"""
        if isinstance(v, str):
            # Handle comma-separated string
            topics = []
            for topic in v.split(','):
                topic = topic.strip()
                if topic:
                    topics.append(topic)
            return topics
        return v or []
    
    @validator('short_summary', 'long_summary')
    def clean_summary(cls, v):
        """Clean and normalize summary text"""
        if v:
            # Remove excessive whitespace
            return ' '.join(v.split())
        return ""
    
    def has_geographic_data(self) -> bool:
        """Check if article has geographic data"""
        return any([self.best_city, self.best_county, self.best_state])
    
    def has_summaries(self) -> bool:
        """Check if article has summary content"""
        return bool(self.short_summary or self.long_summary)
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if article meets confidence threshold"""
        return self.overall_confidence >= threshold
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WikipediaRelationship(BaseModel):
    """Relationship between Wikipedia article and geographic entity"""
    page_id: int
    entity_type: str = Field(..., pattern="^(state|county|city|neighborhood)$")
    entity_id: str
    relationship_type: str = Field(default="describes")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.now)


class WikipediaStats(BaseModel):
    """Statistics about Wikipedia data"""
    total_articles: int = 0
    articles_with_summaries: int = 0
    articles_with_topics: int = 0
    articles_with_geographic_data: int = 0
    high_confidence_articles: int = 0
    
    # Geographic connections
    articles_connected_to_states: int = 0
    articles_connected_to_counties: int = 0
    articles_connected_to_cities: int = 0
    
    # Topic statistics
    unique_topics: int = 0
    avg_topics_per_article: float = 0.0
    
    # Confidence metrics
    avg_confidence: float = 0.0
    min_confidence: float = 0.0
    max_confidence: float = 0.0
    
    timestamp: datetime = Field(default_factory=datetime.now)


class WikipediaLoadResult(BaseModel):
    """Result of Wikipedia loading operation"""
    articles_loaded: int = 0
    nodes_created: int = 0
    topics_extracted: int = 0
    relationships_created: Dict[str, int] = Field(default_factory=lambda: {
        'state': 0,
        'county': 0,
        'city': 0
    })
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    success: bool = True
    
    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str):
        """Add a warning message"""
        self.warnings.append(warning)