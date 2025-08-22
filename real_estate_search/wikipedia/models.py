"""
Pydantic models for Wikipedia data integration.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum


class POICategory(str, Enum):
    """Categories for points of interest."""
    PARK = "park"
    MUSEUM = "museum"
    SCHOOL = "school"
    TRANSIT = "transit"
    SHOPPING = "shopping"
    LANDMARK = "landmark"
    RESTAURANT = "restaurant"
    ENTERTAINMENT = "entertainment"
    SPORTS = "sports"
    CULTURAL = "cultural"


class WikipediaArticle(BaseModel):
    """Wikipedia article data from database."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    page_id: int = Field(..., description="Wikipedia page ID")
    article_id: int = Field(..., description="Internal article ID")
    title: str = Field(..., min_length=1, max_length=500)
    short_summary: str = Field(..., min_length=1, max_length=5000)
    long_summary: str = Field(..., min_length=1, max_length=10000)
    key_topics: List[str] = Field(default_factory=list)
    best_city: Optional[str] = None
    best_county: Optional[str] = None
    best_state: Optional[str] = None
    overall_confidence: float = Field(ge=0, le=1)
    url: Optional[str] = None
    relevance_score: Optional[float] = Field(None, ge=0)
    
    @field_validator('key_topics', mode='before')
    @classmethod
    def parse_key_topics(cls, v):
        """Parse comma-separated key topics."""
        if isinstance(v, str):
            return [topic.strip() for topic in v.split(',') if topic.strip()]
        return v or []


class WikipediaPOI(BaseModel):
    """Point of Interest extracted from Wikipedia."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., min_length=1, max_length=200)
    wikipedia_page_id: Optional[int] = None
    category: POICategory
    significance_score: float = Field(default=0.5, ge=0, le=1)
    description: Optional[str] = Field(None, max_length=1000)
    key_topics: List[str] = Field(default_factory=list)
    distance_miles: Optional[float] = Field(None, ge=0)


class WikipediaLocation(BaseModel):
    """Location data extracted from Wikipedia."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=2)
    county: Optional[str] = Field(None, max_length=100)
    articles: List[WikipediaArticle] = Field(default_factory=list)
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Ensure state is uppercase."""
        return v.upper()


class LocationContext(BaseModel):
    """Location context from Wikipedia for enrichment."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    wikipedia_page_id: str
    wikipedia_title: str
    location_summary: str
    key_topics: List[str] = Field(default_factory=list)


class NeighborhoodContext(BaseModel):
    """Neighborhood context from Wikipedia."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    wikipedia_page_id: str
    wikipedia_title: str
    description: str
    key_topics: List[str] = Field(default_factory=list)


class LocationScores(BaseModel):
    """Location quality scores."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    cultural_richness: float = Field(default=0.0, ge=0, le=1)
    historical_importance: float = Field(default=0.0, ge=0, le=1)
    tourist_appeal: float = Field(default=0.0, ge=0, le=1)
    overall_desirability: float = Field(default=0.0, ge=0, le=1)


class WikipediaData(BaseModel):
    """Simple, flat Wikipedia data for a location."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    wikipedia_title: Optional[str] = None
    summary: Optional[str] = Field(None, max_length=500)
    key_topics: List[str] = Field(default_factory=list, max_length=10)
    nearby_pois: List[Dict[str, Any]] = Field(default_factory=list, max_length=20)  # Simple dicts, not nested objects
    cultural_score: float = Field(default=0.0, ge=0, le=1)
    historical_score: float = Field(default=0.0, ge=0, le=1)
    tourist_score: float = Field(default=0.0, ge=0, le=1)
    overall_score: float = Field(default=0.0, ge=0, le=1)