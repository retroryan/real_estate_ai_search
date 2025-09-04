"""
Standardized response models for all MCP tools.

Single source of truth for response formats.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class PropertyAddress(BaseModel):
    """Property address."""
    model_config = ConfigDict(extra='forbid')
    
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


class Property(BaseModel):
    """Property information."""
    model_config = ConfigDict(extra='forbid')
    
    listing_id: str
    property_type: Optional[str] = None
    price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    address: PropertyAddress
    description: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    score: Optional[float] = None


class PropertySearchResponse(BaseModel):
    """Property search response."""
    model_config = ConfigDict(extra='forbid')
    
    properties: List[Property]
    total_results: int
    returned_results: int
    execution_time_ms: int
    query: str
    location_extracted: Optional[Dict[str, Any]] = None


class WikipediaArticle(BaseModel):
    """Wikipedia article."""
    model_config = ConfigDict(extra='forbid')
    
    article_id: str
    title: str
    url: Optional[str] = None
    summary: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    city: Optional[str] = None
    state: Optional[str] = None
    score: Optional[float] = None


class WikipediaSearchResponse(BaseModel):
    """Wikipedia search response."""
    model_config = ConfigDict(extra='forbid')
    
    articles: List[WikipediaArticle]
    total_results: int
    returned_results: int
    execution_time_ms: int
    query: str


class PropertyDetailsResponse(BaseModel):
    """Property details response."""
    model_config = ConfigDict(extra='forbid')
    
    property: Property
    neighborhood: Optional[Dict[str, Any]] = None
    related_articles: List[WikipediaArticle] = Field(default_factory=list)
    execution_time_ms: int


class ServiceHealth(BaseModel):
    """Service health status."""
    model_config = ConfigDict(extra='forbid')
    
    name: str
    status: str
    response_time_ms: Optional[int] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""
    model_config = ConfigDict(extra='forbid')
    
    status: str
    services: List[ServiceHealth]
    execution_time_ms: int