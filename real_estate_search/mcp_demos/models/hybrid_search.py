"""Pydantic models for hybrid search demos following MCP best practices."""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime


class HybridSearchRequest(BaseModel):
    """Request model for hybrid search with validation."""
    
    model_config = ConfigDict(
        extra='forbid',
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=500, 
        description="Natural language property search query"
    )
    size: int = Field(
        default=10, 
        ge=1, 
        le=50, 
        description="Number of results to return"
    )
    include_location_extraction: bool = Field(
        default=False, 
        description="Include location extraction details in response"
    )
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate query is not empty after stripping."""
        if not v.strip():
            raise ValueError("Query cannot be empty or only whitespace")
        return v.strip()


class LocationExtractionMetadata(BaseModel):
    """Metadata about location extraction from DSPy."""
    
    model_config = ConfigDict(extra='forbid')
    
    city: Optional[str] = Field(None, description="Extracted city name")
    state: Optional[str] = Field(None, description="Extracted state name")
    has_location: bool = Field(..., description="Whether location information was found")
    cleaned_query: str = Field(..., description="Query text with location terms removed")


class PropertyAddress(BaseModel):
    """Property address information with validation."""
    
    model_config = ConfigDict(extra='forbid')
    
    street: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State abbreviation")
    zip_code: Optional[str] = Field(None, description="ZIP code")


class HybridSearchProperty(BaseModel):
    """Individual property result from hybrid search."""
    
    model_config = ConfigDict(
        extra='forbid',
        str_strip_whitespace=True
    )
    
    listing_id: Optional[str] = Field(None, description="Unique listing identifier")
    property_type: Optional[str] = Field(None, description="Type of property")
    address: PropertyAddress = Field(..., description="Property address information")
    price: Optional[float] = Field(None, ge=0, description="Property price in USD")
    bedrooms: Optional[int] = Field(None, ge=0, le=20, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, ge=0, le=20, description="Number of bathrooms")
    square_feet: Optional[int] = Field(None, ge=0, le=50000, description="Property square footage")
    description: Optional[str] = Field(None, max_length=1000, description="Property description")
    features: List[str] = Field(default_factory=list, description="Property features and amenities")
    hybrid_score: Optional[float] = Field(None, ge=0, description="Hybrid search relevance score")
    
    @field_validator('features')
    @classmethod
    def validate_features(cls, v: List[str]) -> List[str]:
        """Validate and clean features list."""
        if not isinstance(v, list):
            return []
        return [str(feature).strip() for feature in v if feature and str(feature).strip()]


class HybridSearchMetadata(BaseModel):
    """Search execution metadata with performance tracking."""
    
    model_config = ConfigDict(extra='forbid')
    
    query: str = Field(..., description="Original search query")
    total_hits: int = Field(..., ge=0, description="Total number of matching properties")
    returned_hits: int = Field(..., ge=0, description="Number of results returned")
    execution_time_ms: int = Field(..., ge=0, description="Total execution time in milliseconds")
    location_extracted: Optional[LocationExtractionMetadata] = Field(
        None, 
        description="Location extraction details"
    )
    timestamp: datetime = Field(default_factory=datetime.now, description="Search timestamp")


class HybridSearchResponse(BaseModel):
    """Complete hybrid search response with validation."""
    
    model_config = ConfigDict(extra='forbid')
    
    results: List[HybridSearchProperty] = Field(
        default_factory=list, 
        description="Property search results"
    )
    metadata: HybridSearchMetadata = Field(..., description="Search execution metadata")
    
    @field_validator('results')
    @classmethod
    def validate_results(cls, v: List[HybridSearchProperty]) -> List[HybridSearchProperty]:
        """Ensure results list is valid."""
        return v if isinstance(v, list) else []


class DemoExecutionResult(BaseModel):
    """Result of a demo execution with metrics."""
    
    model_config = ConfigDict(extra='forbid')
    
    demo_name: str = Field(..., description="Name of the demo executed")
    demo_number: int = Field(..., ge=15, le=19, description="Demo number (15-19)")
    success: bool = Field(..., description="Whether the demo completed successfully")
    queries_executed: int = Field(..., ge=0, description="Number of queries executed")
    queries_successful: int = Field(..., ge=0, description="Number of successful queries")
    total_execution_time_ms: float = Field(..., ge=0, description="Total demo execution time")
    error_message: Optional[str] = Field(None, description="Error message if demo failed")
    timestamp: datetime = Field(default_factory=datetime.now, description="Demo execution timestamp")
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.queries_executed == 0:
            return 0.0
        return (self.queries_successful / self.queries_executed) * 100.0


class ValidationTestCase(BaseModel):
    """Model for parameter validation test cases."""
    
    model_config = ConfigDict(extra='forbid')
    
    name: str = Field(..., description="Test case name")
    params: Dict[str, Any] = Field(..., description="Parameters to test")
    should_fail: bool = Field(..., description="Whether the test should fail")
    expected_error: Optional[str] = Field(None, description="Expected error type")
    description: Optional[str] = Field(None, description="Test case description")


class EdgeCaseTest(BaseModel):
    """Model for edge case testing scenarios."""
    
    model_config = ConfigDict(extra='forbid')
    
    name: str = Field(..., description="Edge case name")
    query: str = Field(..., description="Query to test")
    description: str = Field(..., description="What this edge case tests")
    expected_behavior: Optional[str] = Field(None, description="Expected behavior description")


class PerformanceMetrics(BaseModel):
    """Performance metrics collection model."""
    
    model_config = ConfigDict(extra='forbid')
    
    query_length: int = Field(..., ge=0, description="Length of query in characters")
    execution_time_ms: float = Field(..., ge=0, description="Client-side execution time")
    server_time_ms: int = Field(..., ge=0, description="Server-side execution time")
    total_hits: int = Field(..., ge=0, description="Total search results found")
    returned_hits: int = Field(..., ge=0, description="Number of results returned")
    network_overhead_ms: float = Field(default=0.0, ge=0, description="Network overhead time")
    
    @property
    def efficiency_ratio(self) -> float:
        """Calculate server efficiency ratio."""
        if self.execution_time_ms == 0:
            return 0.0
        return self.server_time_ms / self.execution_time_ms