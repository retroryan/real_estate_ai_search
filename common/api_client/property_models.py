"""Property API Client Models."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from property_finder_models import EnrichedProperty, EnrichedNeighborhood

from .models import PaginatedRequest, PaginatedResponse


class PropertyListRequest(PaginatedRequest):
    """Request model for property list endpoint."""
    
    city: Optional[str] = Field(None, description="Filter by city name")
    include_embeddings: bool = Field(False, description="Include embedding data")
    collection_name: Optional[str] = Field(None, description="ChromaDB collection name")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class PropertyResponse(BaseModel):
    """Single property response."""
    
    data: EnrichedProperty = Field(..., description="Enriched property data")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class ResponseMetadata(BaseModel):
    """API response metadata."""
    
    total_count: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total pages")
    has_next: bool = Field(..., description="Has next page")
    has_previous: bool = Field(..., description="Has previous page")
    timestamp: Optional[float] = Field(None, description="Response timestamp")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class ResponseLinks(BaseModel):
    """Pagination links."""
    
    self: str = Field(..., description="Current page URL")
    first: str = Field(..., description="First page URL") 
    last: str = Field(..., description="Last page URL")
    next: Optional[str] = Field(None, description="Next page URL")
    previous: Optional[str] = Field(None, description="Previous page URL")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class PropertyListResponse(BaseModel):
    """Property list response with pagination."""
    
    data: List[EnrichedProperty] = Field(..., description="List of properties")
    metadata: ResponseMetadata = Field(..., description="Response metadata")
    links: Optional[ResponseLinks] = Field(None, description="Pagination links")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class NeighborhoodListRequest(PaginatedRequest):
    """Request model for neighborhood list endpoint."""
    
    city: Optional[str] = Field(None, description="Filter by city name")
    include_embeddings: bool = Field(False, description="Include embedding data")
    collection_name: Optional[str] = Field(None, description="ChromaDB collection name")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class NeighborhoodResponse(BaseModel):
    """Single neighborhood response."""
    
    data: EnrichedNeighborhood = Field(..., description="Enriched neighborhood data")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class NeighborhoodListResponse(BaseModel):
    """Neighborhood list response with pagination."""
    
    data: List[EnrichedNeighborhood] = Field(..., description="List of neighborhoods")
    metadata: ResponseMetadata = Field(..., description="Response metadata")
    links: Optional[ResponseLinks] = Field(None, description="Pagination links")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")