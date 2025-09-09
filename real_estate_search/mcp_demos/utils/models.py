"""Pydantic models for MCP demo clients."""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from ...models import WikipediaArticle


class SearchType(str, Enum):
    """Search type enumeration."""
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    TEXT = "text"


class PropertyType(str, Enum):
    """Property type enumeration."""
    HOUSE = "House"
    CONDO = "Condo"
    TOWNHOUSE = "Townhouse"
    APARTMENT = "Apartment"
    SINGLE_FAMILY = "Single Family"
    MULTI_FAMILY = "Multi Family"


class PropertySearchRequest(BaseModel):
    """Property search request model."""
    model_config = ConfigDict(extra='forbid')
    
    query: str = Field(description="Natural language search query")
    property_type: Optional[PropertyType] = Field(default=None, description="Property type filter")
    min_price: Optional[float] = Field(default=None, ge=0, description="Minimum price")
    max_price: Optional[float] = Field(default=None, ge=0, description="Maximum price")
    min_bedrooms: Optional[int] = Field(default=None, ge=0, description="Minimum bedrooms")
    max_bedrooms: Optional[int] = Field(default=None, ge=0, description="Maximum bedrooms")
    city: Optional[str] = Field(default=None, description="City filter")
    state: Optional[str] = Field(default=None, max_length=2, description="State code")
    size: int = Field(default=20, ge=1, le=100, description="Number of results")
    search_type: SearchType = Field(default=SearchType.HYBRID, description="Search type")


class Address(BaseModel):
    """Address model."""
    model_config = ConfigDict(extra='forbid')
    
    street: str
    city: str
    state: str
    zip_code: str


class Property(BaseModel):
    """Property listing model - matches server response exactly."""
    model_config = ConfigDict(extra='forbid')
    
    listing_id: str
    property_type: str
    price: float
    bedrooms: int
    bathrooms: float
    square_feet: Optional[int] = None
    description: str
    address: Address
    features: List[str]
    score: float


class PropertySearchResponse(BaseModel):
    """Property search response - matches server response exactly."""
    model_config = ConfigDict(extra='allow')
    
    properties: List[Property]
    total_results: int
    returned_results: int
    execution_time_ms: int
    query: str
    location_extracted: Optional[Dict[str, Any]] = None


class WikipediaSearchRequest(BaseModel):
    """Wikipedia search request model."""
    model_config = ConfigDict(extra='forbid')
    
    query: str = Field(description="Search query")
    search_in: str = Field(default="full", pattern="^(full|summaries|chunks)$")
    city: Optional[str] = Field(default=None)
    state: Optional[str] = Field(default=None, max_length=2)
    categories: Optional[List[str]] = Field(default=None)
    size: int = Field(default=10, ge=1, le=50)
    search_type: SearchType = Field(default=SearchType.HYBRID)


class WikipediaSearchResponse(BaseModel):
    """Wikipedia search response model."""
    model_config = ConfigDict(extra='allow')
    
    # Server returns these field names
    total_results: int
    returned_results: int
    articles: List[WikipediaArticle]
    execution_time_ms: int
    query: Optional[str] = None
    search_in: Optional[str] = None
    search_type: Optional[str] = None
    
    # Aliases for backward compatibility with demos
    @property
    def total(self) -> int:
        return self.total_results
    
    @property
    def returned(self) -> int:
        return self.returned_results
    
    @property
    def search_time_ms(self) -> int:
        return self.execution_time_ms


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth(BaseModel):
    """Service health model."""
    model_config = ConfigDict(extra='allow')
    
    status: str  # Changed from HealthStatus enum to str for flexibility
    message: Optional[str] = None
    # Additional fields from server
    reachable: Optional[bool] = None
    cluster_status: Optional[str] = None
    nodes: Optional[int] = None
    indices: Optional[Dict[str, Any]] = None


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    model_config = ConfigDict(extra='allow')
    
    status: str  # Changed from HealthStatus enum to str for flexibility
    timestamp: str  # Server returns string, not datetime
    services: Union[Dict[str, ServiceHealth], List[ServiceHealth]]  # Can be dict or list
    version: str


class MCPError(BaseModel):
    """MCP error response model."""
    model_config = ConfigDict(extra='forbid')
    
    error: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class DemoResult(BaseModel):
    """Demo execution result model."""
    model_config = ConfigDict(extra='forbid')
    
    demo_name: str
    success: bool
    execution_time_ms: int
    total_results: int
    returned_results: int
    sample_results: List[Dict[str, Any]]
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)