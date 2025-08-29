"""Location and neighborhood data models using Pydantic V2."""

from datetime import datetime
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
    """Demographic information for a neighborhood matching Elasticsearch template."""
    
    model_config = ConfigDict(strict=True)
    
    # Core demographic fields for Elasticsearch
    population: Optional[int] = Field(default=None, gt=0)
    median_income: Optional[int] = Field(default=None, ge=0)  # Changed from median_household_income
    median_age: Optional[float] = Field(default=None, ge=0)
    
    # Array fields for Elasticsearch template
    age_distribution: List[str] = Field(default_factory=list)
    education_level: List[str] = Field(default_factory=list)
    income_brackets: List[str] = Field(default_factory=list)
    
    # Legacy fields (optional)
    primary_age_group: Optional[str] = None
    vibe: Optional[str] = None


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


class WikipediaCorrelations(BaseModel):
    """Wikipedia correlation metadata."""
    
    model_config = ConfigDict(strict=True)
    
    primary_wiki_article: WikiArticle
    related_wiki_articles: List[WikiArticle] = Field(default_factory=list)
    parent_geography: ParentGeography
    generated_by: str
    generated_at: str
    source: str
    updated_by: Optional[str] = None


class Neighborhood(BaseModel):
    """Neighborhood information model matching Elasticsearch template."""
    
    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    # Core fields matching Elasticsearch template
    neighborhood_id: str
    name: str
    city: str
    state: str
    
    # Location fields
    county: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None  # Will be transformed to location array
    location: Optional[List[float]] = None  # [longitude, latitude] for geo_point
    
    # Description and metrics
    description: Optional[str] = None
    population: Optional[int] = None
    median_income: Optional[int] = None
    walkability_score: Optional[int] = Field(default=None, ge=0, le=100)
    school_rating: Optional[float] = Field(default=None, ge=0, le=10)
    
    # Arrays
    amenities: List[str] = Field(default_factory=list)
    
    # Optional nested objects
    demographics: Optional[Demographics] = None
    wikipedia_correlations: Optional[WikipediaCorrelations] = None
    
    # Legacy fields (optional)
    characteristics: Optional[NeighborhoodCharacteristics] = None
    lifestyle_tags: List[str] = Field(default_factory=list)
    median_home_price: Optional[float] = Field(default=None, gt=0)
    price_trend: Optional[str] = None
    
    # Embedding fields for vector search
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    embedding_dimension: Optional[int] = None
    embedded_at: Optional[datetime] = None