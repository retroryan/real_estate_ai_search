"""
Pydantic models for advanced search modules.

This module contains strongly-typed models used across the advanced search functionality.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    """Model for a search request."""
    query: Dict[str, Any] = Field(description="Elasticsearch query DSL")
    size: int = Field(default=10, ge=1, le=100, description="Number of results")
    source_fields: List[str] = Field(default_factory=list, description="Fields to return")
    index: str = Field(default="properties", description="Index to search")


class MultiIndexSearchRequest(BaseModel):
    """Model for a multi-index search request."""
    query: Dict[str, Any] = Field(description="Elasticsearch query DSL")
    indices: List[str] = Field(description="Indices to search")
    size: int = Field(default=15, ge=1, le=100, description="Number of results")
    aggregations: Optional[Dict[str, Any]] = Field(default=None, description="Aggregations")
    highlight: Optional[Dict[str, Any]] = Field(default=None, description="Highlight config")
    
    @field_validator('indices')
    @classmethod
    def validate_indices(cls, v: List[str]) -> List[str]:
        """Ensure indices list is not empty."""
        if not v:
            raise ValueError("Indices list cannot be empty")
        return v


class WikipediaSearchRequest(BaseModel):
    """Model for a Wikipedia search request."""
    query: Dict[str, Any] = Field(description="Elasticsearch query DSL")
    size: int = Field(default=10, ge=1, le=50, description="Number of results")
    source_fields: List[str] = Field(default_factory=list, description="Fields to return")
    highlight: Optional[Dict[str, Any]] = Field(default=None, description="Highlight config")
    sort: Optional[List[Any]] = Field(default=None, description="Sort configuration")
    index: str = Field(default="wikipedia", description="Index to search")


class LocationFilter(BaseModel):
    """Model for location-based filtering."""
    city: Optional[str] = Field(default=None, description="City to filter by")
    state: Optional[str] = Field(default=None, description="State to filter by")
    require_location: bool = Field(default=True, description="Require location fields")
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        """Ensure state is uppercase if provided."""
        return v.upper() if v else v


class EntityDiscriminationResult(BaseModel):
    """Model for entity type discrimination."""
    entity_type: str = Field(description="Type of entity")
    index_name: str = Field(description="Source index name")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    
    @field_validator('entity_type')
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Validate entity type is recognized."""
        valid_types = {'property', 'neighborhood', 'wikipedia', 'unknown'}
        if v not in valid_types:
            raise ValueError(f"Entity type must be one of {valid_types}")
        return v