"""
Search parameter models.

Models for various search query parameters.
"""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict


class PropertySearchParams(BaseModel):
    """Parameters for property search queries."""
    query_text: str = Field(..., description="Search query text")
    size: int = Field(10, ge=1, le=100, description="Number of results to return")
    from_: int = Field(0, ge=0, description="Offset for pagination", alias="from")
    fields: Optional[List[str]] = Field(None, description="Fields to search")
    boost_fields: Optional[Dict[str, float]] = Field(None, description="Field boost values")
    
    model_config = ConfigDict(populate_by_name=True)


class PropertyFilterParams(BaseModel):
    """Parameters for property filter queries."""
    property_type: Optional[str] = Field(None, description="Property type (condo, single-family, etc)")
    min_bedrooms: Optional[int] = Field(None, ge=0, description="Minimum number of bedrooms")
    max_bedrooms: Optional[int] = Field(None, ge=0, description="Maximum number of bedrooms")
    min_bathrooms: Optional[float] = Field(None, ge=0, description="Minimum number of bathrooms")
    max_bathrooms: Optional[float] = Field(None, ge=0, description="Maximum number of bathrooms")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price")
    min_square_feet: Optional[int] = Field(None, ge=0, description="Minimum square feet")
    max_square_feet: Optional[int] = Field(None, ge=0, description="Maximum square feet")
    min_year_built: Optional[int] = Field(None, ge=1600, description="Minimum year built")
    max_year_built: Optional[int] = Field(None, le=2100, description="Maximum year built")
    cities: Optional[List[str]] = Field(None, description="List of cities to filter")
    states: Optional[List[str]] = Field(None, description="List of states to filter")
    features: Optional[List[str]] = Field(None, description="Required features")
    amenities: Optional[List[str]] = Field(None, description="Required amenities")
    parking_type: Optional[str] = Field(None, description="Parking type")
    size: int = Field(10, ge=1, le=100, description="Number of results")
    
    model_config = ConfigDict(extra="ignore")


class NeighborhoodSearchParams(BaseModel):
    """Parameters for neighborhood search."""
    query_text: Optional[str] = Field(None, description="Search query text")
    city: Optional[str] = Field(None, description="City to filter")
    state: Optional[str] = Field(None, description="State to filter")
    min_walkability: Optional[int] = Field(None, ge=0, le=100, description="Minimum walkability score")
    min_school_rating: Optional[float] = Field(None, ge=0, le=10, description="Minimum school rating")
    min_population: Optional[int] = Field(None, ge=0, description="Minimum population")
    max_population: Optional[int] = Field(None, ge=0, description="Maximum population")
    amenities: Optional[List[str]] = Field(None, description="Required amenities")
    size: int = Field(10, ge=1, le=100, description="Number of results")
    
    model_config = ConfigDict(extra="ignore")


class WikipediaSearchParams(BaseModel):
    """Parameters for Wikipedia search."""
    query_text: str = Field(..., description="Search query text")
    categories: Optional[List[str]] = Field(None, description="Wikipedia categories to filter")
    min_relevance: Optional[float] = Field(None, ge=0, le=1, description="Minimum relevance score")
    include_summary: bool = Field(True, description="Include article summary")
    include_sections: bool = Field(False, description="Include article sections")
    size: int = Field(10, ge=1, le=100, description="Number of results")
    
    model_config = ConfigDict(extra="ignore")


class SemanticSearchParams(BaseModel):
    """Parameters for semantic similarity search using embeddings."""
    embedding_vector: Optional[List[float]] = Field(None, description="Embedding vector for similarity")
    query_text: Optional[str] = Field(None, description="Text to generate embedding from")
    field: str = Field("embedding", description="Field containing embeddings")
    min_score: float = Field(0.7, ge=0, le=1, description="Minimum similarity score")
    k: int = Field(10, ge=1, le=100, description="Number of nearest neighbors")
    num_candidates: int = Field(100, ge=10, le=10000, description="Number of candidates to consider")
    
    model_config = ConfigDict(extra="ignore")


class HybridSearchParams(BaseModel):
    """Parameters for hybrid search combining text and vector search."""
    query_text: str = Field(..., description="Search query text")
    embedding_vector: Optional[List[float]] = Field(None, description="Embedding vector")
    text_weight: float = Field(0.5, ge=0, le=1, description="Weight for text search (0-1)")
    vector_weight: float = Field(0.5, ge=0, le=1, description="Weight for vector search (0-1)")
    rrf_window_size: int = Field(100, ge=10, le=1000, description="RRF window size")
    rrf_rank_constant: int = Field(60, ge=1, description="RRF rank constant")
    size: int = Field(10, ge=1, le=100, description="Number of results")
    
    model_config = ConfigDict(extra="ignore")


class AggregationParams(BaseModel):
    """Parameters for aggregation queries."""
    field: str = Field(..., description="Field to aggregate on")
    agg_type: str = Field("terms", description="Type of aggregation")
    size: int = Field(20, ge=1, le=1000, description="Number of buckets to return")
    include_stats: bool = Field(False, description="Include statistical aggregations")
    include_missing: bool = Field(False, description="Include missing values")
    order_by: Optional[str] = Field(None, description="Order aggregation results by")
    
    model_config = ConfigDict(extra="ignore")


class MultiEntitySearchParams(BaseModel):
    """Parameters for searching across multiple entity types."""
    query_text: str = Field(..., description="Search query text")
    include_properties: bool = Field(True, description="Include property results")
    include_neighborhoods: bool = Field(True, description="Include neighborhood results")
    include_wikipedia: bool = Field(True, description="Include Wikipedia results")
    size_per_index: int = Field(5, ge=1, le=50, description="Results per index")
    min_score: Optional[float] = Field(None, ge=0, description="Minimum relevance score")
    
    model_config = ConfigDict(extra="ignore")