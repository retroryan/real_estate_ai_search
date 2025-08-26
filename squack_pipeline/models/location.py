"""Location and neighborhood data models using Pydantic V2."""

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Location(BaseModel):
    """Geographic location model."""
    
    model_config = ConfigDict(strict=True)
    
    city: str
    county: str
    state: str
    zip_code: str


class NeighborhoodCharacteristics(BaseModel):
    """Neighborhood characteristic scores."""
    
    model_config = ConfigDict(strict=True)
    
    walkability_score: int = Field(ge=0, le=10)
    transit_score: int = Field(ge=0, le=10)
    school_rating: int = Field(ge=0, le=10)
    safety_rating: int = Field(ge=0, le=10)
    nightlife_score: int = Field(ge=0, le=10)
    family_friendly_score: int = Field(ge=0, le=10)


class Demographics(BaseModel):
    """Demographic information for a neighborhood."""
    
    model_config = ConfigDict(strict=True)
    
    primary_age_group: str
    vibe: str
    population: int = Field(gt=0)
    median_household_income: float = Field(ge=0)


class WikiArticle(BaseModel):
    """Wikipedia article reference."""
    
    model_config = ConfigDict(strict=True)
    
    page_id: int
    title: str
    url: str
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    relationship: Optional[str] = None


class ParentGeography(BaseModel):
    """Parent geographic entities."""
    
    model_config = ConfigDict(strict=True)
    
    city_wiki: Dict[str, object]
    state_wiki: Dict[str, object]


class GraphMetadata(BaseModel):
    """Graph relationship metadata."""
    
    model_config = ConfigDict(strict=True)
    
    primary_wiki_article: WikiArticle
    related_wiki_articles: List[WikiArticle] = Field(default_factory=list)
    parent_geography: ParentGeography
    generated_by: str
    generated_at: str
    source: str
    updated_by: Optional[str] = None


class Neighborhood(BaseModel):
    """Neighborhood information model."""
    
    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    neighborhood_id: str
    name: str
    city: str
    county: str
    state: str
    coordinates: Dict[str, float]
    description: str
    characteristics: NeighborhoodCharacteristics
    amenities: List[str] = Field(default_factory=list)
    lifestyle_tags: List[str] = Field(default_factory=list)
    median_home_price: float = Field(gt=0)
    price_trend: str
    demographics: Demographics
    graph_metadata: Optional[GraphMetadata] = None