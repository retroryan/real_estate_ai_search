"""Pydantic models for Neighborhood entities"""
from typing import Optional, List, Dict, Any, Set
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class PriceTrend(str, Enum):
    """Price trend categories"""
    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


class NeighborhoodCharacteristics(BaseModel):
    """Neighborhood characteristic scores"""
    walkability_score: Optional[int] = Field(None, ge=0, le=10)
    transit_score: Optional[int] = Field(None, ge=0, le=10)
    school_rating: Optional[int] = Field(None, ge=0, le=10)
    safety_rating: Optional[int] = Field(None, ge=0, le=10)
    nightlife_score: Optional[int] = Field(None, ge=0, le=10)
    family_friendly_score: Optional[int] = Field(None, ge=0, le=10)
    
    def average_score(self) -> float:
        """Calculate average of all non-null scores"""
        scores = [
            self.walkability_score, self.transit_score, self.school_rating,
            self.safety_rating, self.nightlife_score, self.family_friendly_score
        ]
        valid_scores = [s for s in scores if s is not None]
        return sum(valid_scores) / len(valid_scores) if valid_scores else 0.0


class NeighborhoodDemographics(BaseModel):
    """Demographic information for a neighborhood"""
    primary_age_group: Optional[str] = None
    vibe: Optional[str] = None
    population: Optional[int] = Field(None, ge=0)
    median_household_income: Optional[float] = Field(None, ge=0)


class WikipediaMetadata(BaseModel):
    """Wikipedia article metadata for neighborhoods"""
    page_id: int
    title: str
    url: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    relationship: Optional[str] = Field(default="primary")
    
    @validator('relationship')
    def validate_relationship(cls, v):
        valid_types = ['primary', 'neighborhood', 'park', 'landmark', 'reference', 'related']
        if v and v not in valid_types:
            return 'related'
        return v


class GraphMetadata(BaseModel):
    """Graph-related metadata for neighborhoods"""
    primary_wiki_article: Optional[WikipediaMetadata] = None
    related_wiki_articles: List[WikipediaMetadata] = Field(default_factory=list)
    parent_geography: Optional[Dict[str, Any]] = None
    generated_by: Optional[str] = None
    generated_at: Optional[datetime] = None
    source: Optional[str] = None
    updated_by: Optional[str] = None
    
    def get_all_wiki_page_ids(self) -> Set[int]:
        """Get all Wikipedia page IDs from metadata"""
        page_ids = set()
        if self.primary_wiki_article:
            page_ids.add(self.primary_wiki_article.page_id)
        for article in self.related_wiki_articles:
            page_ids.add(article.page_id)
        return page_ids


class Neighborhood(BaseModel):
    """Complete neighborhood model"""
    neighborhood_id: str = Field(..., description="Unique neighborhood identifier")
    name: str = Field(..., description="Neighborhood name")
    city: str = Field(..., description="City name")
    county: str = Field(..., description="County name")
    state: str = Field(..., description="State abbreviation or full name")
    
    # Geographic information
    coordinates: Optional[Dict[str, float]] = None
    
    # Description and characteristics
    description: Optional[str] = None
    characteristics: Optional[NeighborhoodCharacteristics] = None
    amenities: List[str] = Field(default_factory=list)
    lifestyle_tags: List[str] = Field(default_factory=list)
    
    # Market data
    median_home_price: Optional[float] = Field(None, ge=0)
    price_trend: Optional[str] = None
    
    # Demographics
    demographics: Optional[NeighborhoodDemographics] = None
    
    # Graph metadata
    graph_metadata: Optional[GraphMetadata] = None
    
    # Derived fields for graph
    knowledge_score: float = Field(default=0.0, ge=0.0, le=1.0)
    aggregated_topics: Set[str] = Field(default_factory=set)
    wikipedia_count: int = Field(default=0)
    
    @validator('price_trend')
    def validate_price_trend(cls, v):
        if v:
            try:
                return PriceTrend(v.lower()).value
            except:
                return PriceTrend.UNKNOWN.value
        return None
    
    @validator('state')
    def normalize_state(cls, v):
        """Ensure state is consistent"""
        # Map common abbreviations
        state_map = {'CA': 'California', 'UT': 'Utah', 'NV': 'Nevada'}
        if v in state_map:
            return state_map[v]
        return v
    
    def calculate_knowledge_score(self) -> float:
        """Calculate knowledge score based on Wikipedia coverage"""
        score = 0.0
        
        if self.graph_metadata:
            # Primary article contributes 0.5
            if self.graph_metadata.primary_wiki_article:
                score += 0.5 * self.graph_metadata.primary_wiki_article.confidence
            
            # Related articles contribute up to 0.5
            if self.graph_metadata.related_wiki_articles:
                related_score = sum(
                    a.confidence for a in self.graph_metadata.related_wiki_articles[:5]
                ) / 5.0  # Average of up to 5 articles
                score += 0.5 * min(related_score, 1.0)
        
        self.knowledge_score = min(score, 1.0)
        return self.knowledge_score
    
    def has_wikipedia_data(self) -> bool:
        """Check if neighborhood has Wikipedia data"""
        if not self.graph_metadata:
            return False
        return bool(
            self.graph_metadata.primary_wiki_article or 
            self.graph_metadata.related_wiki_articles
        )
    
    class Config:
        arbitrary_types_allowed = True


class NeighborhoodCorrelation(BaseModel):
    """Correlation between neighborhood and Wikipedia article"""
    neighborhood_id: str
    page_id: int
    correlation_method: str = Field(..., pattern="^(direct|geographic|name_match|proximity)$")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    relationship_type: str = Field(default="describes")
    created_at: datetime = Field(default_factory=datetime.now)


class NeighborhoodLoadResult(BaseModel):
    """Result of neighborhood loading operation"""
    neighborhoods_loaded: int = 0
    nodes_created: int = 0
    
    # Relationship counts
    city_relationships: int = 0
    county_relationships: int = 0
    wikipedia_correlations: int = 0
    wikipedia_property_relationships: int = 0
    
    # Correlation breakdown
    direct_correlations: int = 0
    geographic_correlations: int = 0
    name_match_correlations: int = 0
    
    # Enrichment stats
    neighborhoods_enriched: int = 0
    total_topics_extracted: int = 0
    avg_knowledge_score: float = 0.0
    
    # Errors and warnings
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


class NeighborhoodStats(BaseModel):
    """Statistics about neighborhood data"""
    total_neighborhoods: int = 0
    neighborhoods_with_wikipedia: int = 0
    neighborhoods_with_characteristics: int = 0
    neighborhoods_with_demographics: int = 0
    
    # Geographic distribution
    cities_represented: int = 0
    counties_represented: int = 0
    
    # Wikipedia coverage
    avg_wikipedia_articles_per_neighborhood: float = 0.0
    total_wikipedia_correlations: int = 0
    
    # Knowledge metrics
    avg_knowledge_score: float = 0.0
    high_knowledge_neighborhoods: int = 0  # Score > 0.7
    
    # Topic statistics
    unique_topics: int = 0
    avg_topics_per_neighborhood: float = 0.0
    
    timestamp: datetime = Field(default_factory=datetime.now)