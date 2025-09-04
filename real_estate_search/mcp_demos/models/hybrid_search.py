"""Models for hybrid search - matches server response exactly."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class HybridPropertyAddress(BaseModel):
    """Property address."""
    model_config = ConfigDict(extra='forbid')
    
    street: str
    city: str
    state: str
    zip_code: str


class HybridProperty(BaseModel):
    """Property in hybrid search result."""
    model_config = ConfigDict(extra='forbid')
    
    listing_id: str
    property_type: str
    price: float
    bedrooms: int
    bathrooms: float
    square_feet: Optional[int] = None
    address: HybridPropertyAddress
    description: str
    features: List[str]
    score: float


class HybridSearchResponse(BaseModel):
    """Hybrid search response - matches server response exactly."""
    model_config = ConfigDict(extra='forbid')
    
    properties: List[HybridProperty]
    total_results: int
    returned_results: int
    execution_time_ms: int
    query: str
    location_extracted: Optional[Dict[str, Any]] = None


class HybridSearchRequest(BaseModel):
    """Request for hybrid property search."""
    model_config = ConfigDict(extra='forbid')
    
    query: str = Field(min_length=1, max_length=500, description="Natural language search query")
    size: int = Field(default=10, ge=1, le=50, description="Number of results")
    include_location_extraction: bool = Field(default=False, description="Include location extraction details")


class DemoExecutionResult(BaseModel):
    """Result of a demo execution."""
    model_config = ConfigDict(extra='forbid')
    
    demo_name: str
    demo_number: int
    success: bool
    queries_executed: int
    queries_successful: int
    total_execution_time_ms: float
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.queries_executed == 0:
            return 0.0
        return (self.queries_successful / self.queries_executed) * 100.0


class PerformanceMetrics(BaseModel):
    """Performance metrics for tracking."""
    model_config = ConfigDict(extra='forbid')
    
    query_length: int = Field(ge=0)
    execution_time_ms: float = Field(ge=0)
    server_time_ms: int = Field(ge=0)
    total_hits: int = Field(ge=0)
    returned_hits: int = Field(ge=0)
    network_overhead_ms: float = Field(default=0.0, ge=0)
    
    @property
    def efficiency_ratio(self) -> float:
        """Calculate server efficiency ratio."""
        if self.execution_time_ms == 0:
            return 0.0
        return self.server_time_ms / self.execution_time_ms


class ValidationTestCase(BaseModel):
    """Test case for parameter validation."""
    model_config = ConfigDict(extra='forbid')
    
    name: str = Field(description="Test case name")
    params: Dict[str, Any] = Field(description="Parameters to test")
    should_fail: bool = Field(description="Whether test should fail")
    expected_error: Optional[str] = Field(default=None, description="Expected error message pattern")
    description: str = Field(description="Test case description")


class EdgeCaseTest(BaseModel):
    """Edge case test scenario."""
    model_config = ConfigDict(extra='forbid')
    
    name: str = Field(description="Test case name")
    query: str = Field(description="Search query to test")
    expected_location: Optional[str] = Field(default=None, description="Expected location extraction")
    expected_behavior: str = Field(description="Expected behavior description")