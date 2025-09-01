"""
Pydantic models for hybrid search functionality.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class LocationIntent(BaseModel):
    """Extracted location intent from natural language query."""
    city: Optional[str] = Field(None, description="Extracted city name")
    state: Optional[str] = Field(None, description="Extracted state name")
    neighborhood: Optional[str] = Field(None, description="Extracted neighborhood name")
    zip_code: Optional[str] = Field(None, description="Extracted ZIP code")
    has_location: bool = Field(False, description="Whether location was found in query")
    cleaned_query: str = Field(..., description="Query with location terms removed")
    confidence: float = Field(0.0, description="Confidence score for extraction")


class HybridSearchParams(BaseModel):
    """Parameters for hybrid search queries."""
    query_text: str = Field(..., description="Natural language search query")
    size: int = Field(10, description="Number of results to return")
    rank_constant: int = Field(60, description="RRF rank constant (k parameter)")
    rank_window_size: int = Field(100, description="RRF window size for ranking")
    text_boost: float = Field(1.0, description="Boost factor for text search")
    vector_boost: float = Field(1.0, description="Boost factor for vector search")
    location_intent: Optional[LocationIntent] = Field(None, description="Extracted location information")


class SearchResult(BaseModel):
    """Individual search result with hybrid scoring."""
    listing_id: str = Field(..., description="Property listing ID")
    hybrid_score: float = Field(..., description="Combined RRF score")
    text_score: Optional[float] = Field(None, description="Text search score")
    vector_score: Optional[float] = Field(None, description="Vector search score")
    property_data: Dict[str, Any] = Field(..., description="Property information")


class HybridSearchResult(BaseModel):
    """Complete hybrid search result."""
    query: str = Field(..., description="Original query text")
    total_hits: int = Field(..., description="Total matching documents")
    execution_time_ms: int = Field(..., description="Query execution time")
    results: List[SearchResult] = Field(..., description="Search results")
    search_metadata: Dict[str, Any] = Field(..., description="Search execution metadata")