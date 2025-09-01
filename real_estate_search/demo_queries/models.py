"""Pydantic models for demo query inputs and outputs."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


class PropertySearchParams(BaseModel):
    """Parameters for property search queries."""
    model_config = ConfigDict(populate_by_name=True)
    
    query_text: str = Field(..., description="Search query text")
    size: int = Field(10, description="Number of results to return")
    from_: int = Field(0, description="Offset for pagination", alias="from")


class PropertyFilterParams(BaseModel):
    """Parameters for property filter queries."""
    property_type: Optional[str] = Field(None, description="Property type (condo, single-family, etc)")
    min_bedrooms: Optional[int] = Field(None, description="Minimum number of bedrooms")
    max_bedrooms: Optional[int] = Field(None, description="Maximum number of bedrooms")
    min_bathrooms: Optional[float] = Field(None, description="Minimum number of bathrooms")
    min_price: Optional[float] = Field(None, description="Minimum price")
    max_price: Optional[float] = Field(None, description="Maximum price")
    min_square_feet: Optional[int] = Field(None, description="Minimum square feet")
    max_square_feet: Optional[int] = Field(None, description="Maximum square feet")
    cities: Optional[List[str]] = Field(None, description="List of cities to filter")
    features: Optional[List[str]] = Field(None, description="Required features")
    size: int = Field(10, description="Number of results")
    

class GeoSearchParams(BaseModel):
    """Parameters for geographic search."""
    latitude: float = Field(..., description="Center latitude")
    longitude: float = Field(..., description="Center longitude")
    distance: str = Field("5km", description="Search radius (e.g., '5km', '10mi')")
    size: int = Field(10, description="Number of results")


class AggregationParams(BaseModel):
    """Parameters for aggregation queries."""
    field: str = Field(..., description="Field to aggregate on")
    size: int = Field(20, description="Number of buckets to return")
    include_stats: bool = Field(True, description="Include statistical aggregations")


class SemanticSearchParams(BaseModel):
    """Parameters for semantic similarity search."""
    embedding_vector: Optional[List[float]] = Field(None, description="Embedding vector for similarity")
    query_text: Optional[str] = Field(None, description="Text to generate embedding from")
    min_score: float = Field(0.7, description="Minimum similarity score")
    size: int = Field(10, description="Number of results")


class MultiEntitySearchParams(BaseModel):
    """Parameters for multi-entity search."""
    query_text: str = Field(..., description="Search query text")
    include_properties: bool = Field(True, description="Include property results")
    include_neighborhoods: bool = Field(True, description="Include neighborhood results")
    include_wikipedia: bool = Field(True, description="Include Wikipedia results")
    size_per_index: int = Field(5, description="Results per index")


class PropertyFeatures(BaseModel):
    """Model for property features to ensure consistent structure."""
    bedrooms: Optional[int] = Field(0, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(0, description="Number of bathrooms")
    square_feet: Optional[int] = Field(0, description="Square footage")
    
    @classmethod
    def from_result(cls, result: Dict[str, Any]) -> 'PropertyFeatures':
        """Create PropertyFeatures from a result dict."""
        features = result.get('features', {})
        
        # Try to extract from features dict or fall back to top-level
        try:
            # Try to use features as a dict
            if features:
                bedrooms = features.get('bedrooms', result.get('bedrooms', 0))
                bathrooms = features.get('bathrooms', result.get('bathrooms', 0))
                square_feet = features.get('square_feet', result.get('square_feet', 0))
                return cls(
                    bedrooms=bedrooms,
                    bathrooms=bathrooms,
                    square_feet=square_feet
                )
        except (AttributeError, TypeError):
            # features is not dict-like, fall through to top-level
            pass
        
        # Fall back to top-level fields
        return cls(
            bedrooms=result.get('bedrooms', 0),
            bathrooms=result.get('bathrooms', 0),
            square_feet=result.get('square_feet', 0)
        )


class DemoQueryResult(BaseModel):
    """Standard result format for demo queries."""
    query_name: str = Field(..., description="Name of the demo query")
    query_description: Optional[str] = Field(None, description="Description of what the query searches for")
    execution_time_ms: int = Field(..., description="Query execution time in milliseconds")
    total_hits: int = Field(..., description="Total number of matching documents")
    returned_hits: int = Field(..., description="Number of documents returned")
    results: List[Dict[str, Any]] = Field(..., description="Query results")
    aggregations: Optional[Dict[str, Any]] = Field(None, description="Aggregation results if applicable")
    query_dsl: Dict[str, Any] = Field(..., description="The actual Elasticsearch query used")
    es_features: Optional[List[str]] = Field(None, description="Elasticsearch features demonstrated")
    indexes_used: Optional[List[str]] = Field(None, description="Indexes queried")
    
    def display(self, verbose: bool = False) -> str:
        """Format results for display."""
        import json
        
        output = []
        output.append(f"\n{'='*80}")
        output.append(f"🔍 Demo Query: {self.query_name}")
        output.append(f"{'='*80}")
        
        # Add search description if provided
        if self.query_description:
            output.append(f"\n📝 SEARCH DESCRIPTION:")
            output.append(f"   {self.query_description}")
        
        # Add Elasticsearch features if provided
        if self.es_features:
            output.append(f"\n📊 ELASTICSEARCH FEATURES:")
            for feature in self.es_features:
                output.append(f"   • {feature}")
        
        # Add indexes used if provided
        if self.indexes_used:
            output.append(f"\n📁 INDEXES & DOCUMENTS:")
            for index_info in self.indexes_used:
                output.append(f"   • {index_info}")
        
        output.append(f"\n{'─'*80}")
        output.append(f"⏱️  Execution Time: {self.execution_time_ms}ms")
        output.append(f"📊 Total Hits: {self.total_hits}")
        output.append(f"📄 Returned: {self.returned_hits}")
        
        # Remove raw results and aggregations display - rich formatting is handled by demo modules
        
        if verbose:
            output.append(f"\n{'-'*40}")
            output.append("Query DSL:")
            output.append(f"{'-'*40}")
            # Show full query DSL without truncation
            output.append(json.dumps(self.query_dsl, indent=2))
        
        return '\n'.join(output)