"""Pydantic models for demo query inputs and outputs."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class PropertySearchParams(BaseModel):
    """Parameters for property search queries."""
    query_text: str = Field(..., description="Search query text")
    size: int = Field(10, description="Number of results to return")
    from_: int = Field(0, description="Offset for pagination", alias="from")
    
    class Config:
        populate_by_name = True


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
        
        if self.results:
            output.append(f"\n{'-'*40}")
            output.append("Results:")
            output.append(f"{'-'*40}")
            
            # Show all results for aggregation queries, limited results for others
            is_aggregation = 'aggregation' in str(self.query_name).lower() or 'statistics' in str(self.query_name).lower() or 'distribution' in str(self.query_name).lower()
            results_to_show = self.results if is_aggregation else self.results[:10]
            
            for i, result in enumerate(results_to_show, 1):
                # Check if this is an aggregation result (has specific aggregation fields)
                if 'property_count' in result and 'neighborhood_id' in result:
                    # Neighborhood aggregation result
                    output.append(
                        f"{i}. Neighborhood: {result.get('neighborhood_id', 'N/A')}"
                    )
                    output.append(f"   Properties: {result.get('property_count', 0)}")
                    output.append(f"   Avg Price: ${result.get('avg_price', 0):,.0f}")
                    output.append(f"   Price Range: ${result.get('min_price', 0):,.0f} - ${result.get('max_price', 0):,.0f}")
                    output.append(f"   Avg Bedrooms: {result.get('avg_bedrooms', 0):.1f}")
                    output.append(f"   Avg Sq Ft: {result.get('avg_square_feet', 0):,.0f}")
                    output.append(f"   Price/SqFt: ${result.get('price_per_sqft', 0):,.0f}")
                    if 'property_types' in result and result['property_types']:
                        types_str = ", ".join([f"{t['type']} ({t['count']})" for t in result['property_types']])
                        output.append(f"   Types: {types_str}")
                    output.append("")  # Blank line between neighborhoods
                elif 'price_range' in result:
                    # Price distribution result
                    output.append(f"{i}. {result.get('price_range', 'N/A')}: {result.get('count', 0)} properties")
                    if result.get('property_types'):
                        for prop_type, count in result['property_types'].items():
                            output.append(f"   - {prop_type}: {count}")
                    if result.get('avg_price'):
                        output.append(f"   Avg: ${result.get('avg_price', 0):,.0f}")
                elif 'property_type' in result:
                    # Property result
                    output.append(
                        f"{i}. {result.get('address', {}).get('street', 'N/A')}, "
                        f"{result.get('address', {}).get('city', 'N/A')}, "
                        f"{result.get('address', {}).get('state', 'N/A')}"
                    )
                    # Check if features is a dict with property details
                    features = result.get('features', {})
                    if isinstance(features, dict):
                        bedrooms = features.get('bedrooms', result.get('bedrooms', 0))
                        bathrooms = features.get('bathrooms', result.get('bathrooms', 0))
                        square_feet = features.get('square_feet', result.get('square_feet', 0))
                    else:
                        bedrooms = result.get('bedrooms', 0)
                        bathrooms = result.get('bathrooms', 0)
                        square_feet = result.get('square_feet', 0)
                    
                    output.append(
                        f"   ${result.get('price', 0):,.0f} | "
                        f"{bedrooms}bd/{bathrooms}ba | "
                        f"{square_feet:,} sqft | "
                        f"{result.get('property_type', 'N/A')}"
                    )
                    if '_score' in result:
                        output.append(f"   Score: {result['_score']:.3f}")
                    if '_entity_type' in result:
                        output.append(f"   Source: {result['_entity_type']}")
                    output.append("")  # Add spacing
                elif 'neighborhood_id' in result and 'name' not in result:
                    # Basic neighborhood result
                    output.append(
                        f"{i}. Neighborhood: {result.get('neighborhood_id', 'N/A')}"
                    )
                    if 'description' in result:
                        output.append(f"   {result['description'][:200]}...")
                    if '_entity_type' in result:
                        output.append(f"   Source: {result['_entity_type']}")
                    output.append("")  # Add spacing
                elif 'name' in result and 'neighborhood_id' in result:
                    # Full neighborhood result
                    output.append(
                        f"{i}. {result.get('name', 'N/A')} ({result.get('neighborhood_id', 'N/A')})"
                    )
                    output.append(
                        f"   Location: {result.get('city', 'N/A')}, {result.get('state', 'N/A')}"
                    )
                    if 'description' in result:
                        output.append(f"   {result['description'][:200]}...")
                    if '_score' in result:
                        output.append(f"   Score: {result['_score']:.3f}")
                    if '_entity_type' in result:
                        output.append(f"   Source: {result['_entity_type']}")
                    output.append("")  # Add spacing
                elif 'page_id' in result:
                    # Wikipedia result
                    output.append(
                        f"{i}. {result.get('title', 'N/A')}"
                    )
                    if result.get('city') or result.get('state'):
                        output.append(
                            f"   Location: {result.get('city', '')}{', ' if result.get('city') and result.get('state') else ''}{result.get('state', '')}"
                        )
                    output.append(
                        f"   {result.get('summary', 'N/A')[:300]}..."
                    )
                    if '_score' in result:
                        output.append(f"   Score: {result['_score']:.3f}")
                    if '_entity_type' in result:
                        output.append(f"   Source: {result['_entity_type']}")
                    output.append("")  # Add spacing
                else:
                    # Generic result - show full content
                    output.append(f"{i}. {json.dumps(result, indent=2)}")
        
        if self.aggregations:
            output.append(f"\n{'-'*40}")
            output.append("Aggregations:")
            output.append(f"{'-'*40}")
            # Format aggregations as pretty JSON without truncation
            output.append(json.dumps(self.aggregations, indent=2))
        
        if verbose:
            output.append(f"\n{'-'*40}")
            output.append("Query DSL:")
            output.append(f"{'-'*40}")
            # Show full query DSL without truncation
            output.append(json.dumps(self.query_dsl, indent=2))
        
        return '\n'.join(output)