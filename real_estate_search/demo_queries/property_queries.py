"""
Refactored property search demo queries with Pydantic models and comprehensive documentation.

This module demonstrates fundamental Elasticsearch property search patterns:
1. Full-text search with multi-match queries
2. Filtered searches combining text and criteria
3. Range queries for numeric fields
4. Geo-distance searches for location-based queries
5. Complex boolean queries with multiple conditions

ELASTICSEARCH CONCEPTS DEMONSTRATED:
- Query vs Filter context (scoring vs non-scoring)
- Field boosting for relevance tuning
- Fuzzy matching for typo tolerance
- Aggregations for faceted search
- Geo queries for location-based search
- Highlighting for search result context
- Source filtering for performance optimization
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from elasticsearch import Elasticsearch
import logging

from .base_models import (
    PropertyListing,
    SearchRequest,
    SearchResponse,
    BoolQuery,
    QueryClause,
    QueryType,
    PropertyType,
    Address,
    GeoPoint,
    TypedDemoResult,
    AggregationType,
    AggregationResult,
    BucketAggregation,
    StatsAggregation
)
from .models import DemoQueryResult

logger = logging.getLogger(__name__)


class PropertyQueryBuilder:
    """
    Builder class for constructing property search queries.
    
    This class encapsulates the logic for building various types of
    Elasticsearch queries for property searches, from simple text searches
    to complex geo-spatial and filtered queries.
    """
    
    @staticmethod
    def basic_search(
        query_text: str,
        size: int = 10,
        highlight: bool = True
    ) -> SearchRequest:
        """
        Build a basic property search query using multi-match.
        
        ELASTICSEARCH CONCEPTS:
        1. MULTI-MATCH QUERY:
           - Searches text across multiple fields simultaneously
           - More flexible than single-field match queries
           - Supports different matching strategies
        
        2. FIELD BOOSTING:
           - description^2 gives 2x weight to description matches
           - Influences relevance scoring, not filtering
           - Critical for tuning search result quality
        
        3. FUZZINESS:
           - AUTO adapts based on term length
           - Handles typos and variations
           - Essential for user-friendly search
        
        Args:
            query_text: Text to search for
            size: Maximum results to return
            highlight: Whether to include highlighting
            
        Returns:
            SearchRequest configured for basic text search
        """
        query: Dict[str, Any] = {
            "multi_match": {
                "query": query_text,
                "fields": [
                    "description^2",      # Primary content field
                    "amenities^1.5",      # Important features
                    "address.street",     # Location context
                    "address.city",       # City search
                    "neighborhood_id"     # Neighborhood association
                ],
                "type": "best_fields",   # Use best matching field's score
                "fuzziness": "AUTO",      # Adaptive fuzzy matching
                "prefix_length": 2,       # Minimum exact prefix
                "operator": "OR"          # Match ANY term (vs AND for ALL)
            }
        }
        
        request = SearchRequest(
            index="properties",
            query=query,
            size=size,
            source=[  # Only return needed fields
                "listing_id", "property_type", "price", 
                "bedrooms", "bathrooms", "square_feet",
                "address", "description", "amenities"
            ]
        )
        
        if highlight:
            request.highlight = {
                "fields": {
                    "description": {"fragment_size": 150},
                    "amenities": {"fragment_size": 100}
                },
                "pre_tags": ["<em>"],
                "post_tags": ["</em>"]
            }
        
        return request
    
    @staticmethod
    def filtered_search(
        property_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_bedrooms: Optional[int] = None,
        min_bathrooms: Optional[float] = None,
        amenities: Optional[List[str]] = None,
        size: int = 10
    ) -> SearchRequest:
        """
        Build a filtered property search query.
        
        ELASTICSEARCH CONCEPTS:
        1. BOOL QUERY:
           - Combines multiple query clauses with boolean logic
           - filter: Must match but doesn't affect score (cached)
           - must: Must match and affects score
           - should: Optional matches that boost score
        
        2. FILTER CONTEXT:
           - Used for yes/no questions (has 3 bedrooms?)
           - Results are cached for performance
           - No relevance scores calculated
        
        3. RANGE QUERIES:
           - gte/lte for inclusive bounds
           - gt/lt for exclusive bounds
           - Works with numbers, dates, strings
        
        Args:
            property_type: Filter by property type
            min_price: Minimum price filter
            max_price: Maximum price filter
            min_bedrooms: Minimum bedrooms
            min_bathrooms: Minimum bathrooms
            amenities: Required amenities
            size: Maximum results
            
        Returns:
            SearchRequest with filter criteria
        """
        bool_query = BoolQuery()
        
        # Build filter clauses (non-scoring, cached)
        filters: List[Dict[str, Any]] = []
        
        if property_type:
            # Normalize property type to match data format
            pt_normalized = property_type.lower().replace(' ', '-')
            filters.append({"term": {"property_type": pt_normalized}})
        
        if min_price is not None or max_price is not None:
            range_clause: Dict[str, Any] = {}
            if min_price is not None:
                range_clause["gte"] = min_price
            if max_price is not None:
                range_clause["lte"] = max_price
            filters.append({"range": {"price": range_clause}})
        
        if min_bedrooms is not None:
            filters.append({"range": {"bedrooms": {"gte": min_bedrooms}}})
        
        if min_bathrooms is not None:
            filters.append({"range": {"bathrooms": {"gte": min_bathrooms}}})
        
        if amenities:
            # Each amenity must exist
            for amenity in amenities:
                filters.append({"match": {"amenities": amenity}})
        
        # Use match_all if no filters (returns everything)
        if filters:
            query = {
                "bool": {
                    "filter": filters
                }
            }
        else:
            query = {"match_all": {}}
        
        return SearchRequest(
            index="properties",
            query=query,
            size=size,
            sort=[{"price": {"order": "asc"}}],  # Sort by price when filtering
            source=True  # Return all fields
        )
    
    @staticmethod
    def geo_search(
        center_lat: float,
        center_lon: float,
        radius_km: float = 5.0,
        property_type: Optional[str] = None,
        max_price: Optional[float] = None,
        size: int = 10
    ) -> SearchRequest:
        """
        Build a geo-distance property search query.
        
        ELASTICSEARCH CONCEPTS:
        1. GEO_DISTANCE QUERY:
           - Filters documents within radius of a point
           - Requires geo_point field mapping
           - Supports various distance units (km, mi, m)
        
        2. DISTANCE CALCULATION:
           - arc: Most accurate, slowest (default)
           - plane: Faster, less accurate for large distances
           - Distance returned in sort for display
        
        3. COMBINED FILTERING:
           - Geo filter reduces search space first
           - Additional filters apply within radius
           - Order matters for performance
        
        Args:
            center_lat: Center point latitude
            center_lon: Center point longitude
            radius_km: Search radius in kilometers
            property_type: Optional property type filter
            max_price: Optional maximum price
            size: Maximum results
            
        Returns:
            SearchRequest for geo-distance search
        """
        filters = [
            {
                "geo_distance": {
                    "distance": f"{radius_km}km",
                    "address.location": {
                        "lat": center_lat,
                        "lon": center_lon
                    }
                }
            }
        ]
        
        if property_type:
            # Normalize property type to match data format
            pt_normalized = property_type.lower().replace(' ', '-')
            filters.append({"term": {"property_type": pt_normalized}})
        
        if max_price is not None:
            filters.append({"range": {"price": {"lte": max_price}}})
        
        query = {
            "bool": {
                "filter": filters
            }
        }
        
        # Sort by distance from center point
        sort = [
            {
                "_geo_distance": {
                    "address.location": {
                        "lat": center_lat,
                        "lon": center_lon
                    },
                    "order": "asc",
                    "unit": "km",
                    "distance_type": "arc"
                }
            }
        ]
        
        return SearchRequest(
            index="properties",
            query=query,
            size=size,
            sort=sort,
            source=True
        )
    
    @staticmethod
    def price_range_with_stats(
        min_price: float,
        max_price: float,
        include_stats: bool = True
    ) -> SearchRequest:
        """
        Build a price range query with statistical aggregations.
        
        ELASTICSEARCH CONCEPTS:
        1. AGGREGATIONS:
           - Calculate metrics across matching documents
           - Don't affect search results, add metadata
           - Can be nested for complex analytics
        
        2. STATS AGGREGATION:
           - Returns min, max, avg, sum, count
           - Single pass calculation for efficiency
           - Useful for result set context
        
        3. HISTOGRAM AGGREGATION:
           - Buckets data into intervals
           - Fixed or automatic interval sizing
           - Great for price distribution visualization
        
        Args:
            min_price: Minimum price
            max_price: Maximum price
            include_stats: Whether to include aggregations
            
        Returns:
            SearchRequest with price range and optional stats
        """
        query = {
            "range": {
                "price": {
                    "gte": min_price,
                    "lte": max_price
                }
            }
        }
        
        aggs = None
        if include_stats:
            aggs = {
                "price_stats": {
                    "stats": {
                        "field": "price"
                    }
                },
                "price_histogram": {
                    "histogram": {
                        "field": "price",
                        "interval": 100000,  # $100k buckets
                        "min_doc_count": 1  # Only return non-empty buckets
                    }
                },
                "property_types": {
                    "terms": {
                        "field": "property_type.keyword",
                        "size": 10
                    }
                },
                "bedroom_stats": {
                    "stats": {
                        "field": "bedrooms"
                    }
                }
            }
        
        return SearchRequest(
            index="properties",
            query=query,
            size=20,
            aggs=aggs,
            sort=[{"price": {"order": "asc"}}],
            source=True
        )


class PropertySearchDemo:
    """
    Demo class for property searches using Pydantic models.
    
    This class demonstrates best practices for:
    - Executing Elasticsearch queries with proper error handling
    - Converting responses to strongly-typed entities
    - Building complex search workflows
    - Providing useful search metadata
    """
    
    def __init__(self, es_client: Elasticsearch):
        """Initialize with Elasticsearch client."""
        self.es_client = es_client
        self.query_builder = PropertyQueryBuilder()
    
    def execute_search(self, request: SearchRequest) -> Tuple[Optional[SearchResponse], int]:
        """
        Execute a search request and measure timing.
        
        Args:
            request: SearchRequest to execute
            
        Returns:
            Tuple of (SearchResponse or None, execution time in ms)
        """
        import time
        start_time = time.time()
        
        try:
            response = self.es_client.search(
                index=request.index,
                body=request.to_dict()
            )
            execution_time = int((time.time() - start_time) * 1000)
            return SearchResponse.from_elasticsearch(response), execution_time
            
        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            return None, execution_time
    
    def demo_basic_search(
        self,
        query_text: str = "modern home with pool"
    ) -> DemoQueryResult:
        """
        Execute basic property search demo.
        
        This demonstrates:
        - Full-text search across multiple fields
        - Field boosting for relevance
        - Fuzzy matching for user-friendly search
        - Result highlighting
        
        Args:
            query_text: Search query
            
        Returns:
            DemoQueryResult with typed property entities
        """
        request = self.query_builder.basic_search(query_text)
        response, exec_time = self.execute_search(request)
        
        if not response:
            return DemoQueryResult(
                query_name="Basic Property Search",
                execution_time_ms=exec_time,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=request.to_dict()
            )
        
        # Convert to typed entities
        properties = response.to_entities()
        
        # Convert to legacy format for compatibility
        results = []
        for prop in properties:
            if isinstance(prop, PropertyListing):
                result = prop.model_dump(exclude_none=True)
                # Add highlights if available
                for hit in response.hits:
                    if hit.source.get('listing_id') == prop.listing_id:
                        if hit.highlight:
                            result['_highlights'] = hit.highlight
                        break
                results.append(result)
        
        return DemoQueryResult(
            query_name=f"Basic Property Search: '{query_text}'",
            query_description=f"Full-text search for '{query_text}' across property descriptions, amenities, and addresses with fuzzy matching to handle typos",
            execution_time_ms=exec_time,
            total_hits=response.total_hits,
            returned_hits=len(results),
            results=results,
            query_dsl=request.to_dict(),
            es_features=[
                "Multi-Match Query: Searches across multiple fields simultaneously",
                "Field Boosting: Weights description 2x, amenities 1.5x for relevance",
                "Fuzzy Matching: AUTO fuzziness handles typos and variations",
                "Highlighting: Shows matched text fragments in results",
                "Query Context: Calculates relevance scores for ranking"
            ],
            indexes_used=[
                "properties index: 420 real estate listings",
                "Fields searched: description, amenities, address.street, address.city, neighborhood_id"
            ],
            explanation=f"Searched for '{query_text}' across description, amenities, and address fields with fuzzy matching"
        )
    
    def demo_filtered_search(
        self,
        property_type: str = "Single Family",
        min_price: float = 300000,
        max_price: float = 800000,
        min_bedrooms: int = 3,
        min_bathrooms: float = 2.0
    ) -> DemoQueryResult:
        """
        Execute filtered property search demo.
        
        This demonstrates:
        - Filter context for non-scoring criteria
        - Range queries for numeric fields
        - Combining multiple filter conditions
        - Efficient caching of filter results
        
        Args:
            property_type: Type of property
            min_price: Minimum price
            max_price: Maximum price  
            min_bedrooms: Minimum bedrooms
            min_bathrooms: Minimum bathrooms
            
        Returns:
            DemoQueryResult with filtered properties
        """
        request = self.query_builder.filtered_search(
            property_type=property_type,
            min_price=min_price,
            max_price=max_price,
            min_bedrooms=min_bedrooms,
            min_bathrooms=min_bathrooms
        )
        
        response, exec_time = self.execute_search(request)
        
        if not response:
            return DemoQueryResult(
                query_name="Filtered Property Search",
                execution_time_ms=exec_time,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=request.to_dict()
            )
        
        # Convert to typed entities
        properties = response.to_entities()
        results = [prop.model_dump(exclude_none=True) for prop in properties 
                  if isinstance(prop, PropertyListing)]
        
        return DemoQueryResult(
            query_name="Filtered Property Search",
            query_description=f"Filter properties by: {property_type} type, ${min_price:,.0f}-${max_price:,.0f} price range, {min_bedrooms}+ bedrooms, {min_bathrooms}+ bathrooms",
            execution_time_ms=exec_time,
            total_hits=response.total_hits,
            returned_hits=len(results),
            results=results,
            query_dsl=request.to_dict(),
            es_features=[
                "Bool Query with Filters: Combines multiple criteria using filter context",
                "Filter Context: Non-scoring queries cached for performance",
                "Range Queries: Numeric filtering for price, bedrooms, bathrooms",
                "Term Query: Exact matching on property type",
                "Sort by Price: Results ordered by price ascending"
            ],
            indexes_used=[
                "properties index: 420 real estate listings",
                "Filtered fields: property_type, price, bedrooms, bathrooms"
            ],
            explanation=f"Properties: {property_type}, ${min_price:,.0f}-${max_price:,.0f}, {min_bedrooms}+ beds, {min_bathrooms}+ baths"
        )
    
    def demo_geo_search(
        self,
        center_lat: float = 37.7749,  # San Francisco
        center_lon: float = -122.4194,
        radius_km: float = 5.0,
        max_price: Optional[float] = 1000000
    ) -> DemoQueryResult:
        """
        Execute geo-distance search demo.
        
        This demonstrates:
        - Geo-distance filtering
        - Sorting by distance
        - Combining geo and other filters
        - Distance calculation in results
        
        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            radius_km: Search radius in km
            max_price: Optional price limit
            
        Returns:
            DemoQueryResult with nearby properties
        """
        request = self.query_builder.geo_search(
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km,
            max_price=max_price
        )
        
        response, exec_time = self.execute_search(request)
        
        if not response:
            return DemoQueryResult(
                query_name="Geo-Distance Property Search",
                execution_time_ms=exec_time,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=request.to_dict()
            )
        
        # Convert to typed entities with distance
        properties = response.to_entities()
        results = []
        for i, prop in enumerate(properties):
            if isinstance(prop, PropertyListing):
                result = prop.model_dump(exclude_none=True)
                # Add distance from sort values
                if i < len(response.hits) and hasattr(response.hits[i], 'sort'):
                    result['_distance_km'] = response.hits[i].sort[0] if response.hits[i].sort else None
                results.append(result)
        
        return DemoQueryResult(
            query_name="Geo-Distance Property Search",
            query_description=f"Find properties within {radius_km}km radius of coordinates ({center_lat:.4f}, {center_lon:.4f}) with optional price filtering",
            execution_time_ms=exec_time,
            total_hits=response.total_hits,
            returned_hits=len(results),
            results=results,
            query_dsl=request.to_dict(),
            es_features=[
                "Geo-Distance Query: Filters documents within radius of a point",
                "Geo-Point Field: Uses address.location field for coordinates",
                "Distance Sorting: Results ordered by distance from center",
                "Distance Calculation: Arc method for accurate distances",
                "Combined Filters: Geo filter with optional price constraints"
            ],
            indexes_used=[
                "properties index: 420 real estate listings with geo-coordinates",
                "Geo field: address.location (lat/lon pairs)",
                f"Search area: {radius_km}km radius in San Francisco area"
            ],
            explanation=f"Properties within {radius_km}km of ({center_lat}, {center_lon})"
        )
    
    def demo_price_range_with_analytics(
        self,
        min_price: float = 400000,
        max_price: float = 800000
    ) -> DemoQueryResult:
        """
        Execute price range search with analytics.
        
        This demonstrates:
        - Range queries for price filtering
        - Statistical aggregations
        - Histogram aggregations for distribution
        - Terms aggregations for categories
        
        Args:
            min_price: Minimum price
            max_price: Maximum price
            
        Returns:
            DemoQueryResult with properties and statistics
        """
        request = self.query_builder.price_range_with_stats(
            min_price=min_price,
            max_price=max_price,
            include_stats=True
        )
        
        response, exec_time = self.execute_search(request)
        
        if not response:
            return DemoQueryResult(
                query_name="Price Range Search with Analytics",
                execution_time_ms=exec_time,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=request.to_dict()
            )
        
        # Convert properties
        properties = response.to_entities()
        results = [prop.model_dump(exclude_none=True) for prop in properties 
                  if isinstance(prop, PropertyListing)]
        
        # Process aggregations - keep as dict for compatibility
        aggregations = None
        if response.aggregations:
            aggregations = {}
            
            # Price statistics
            if 'price_stats' in response.aggregations:
                stats = response.aggregations['price_stats']
                aggregations['price_stats'] = {
                    "min": stats.get('min', 0),
                    "max": stats.get('max', 0),
                    "avg": stats.get('avg', 0),
                    "sum": stats.get('sum', 0),
                    "count": stats.get('count', 0)
                }
            
            # Property type distribution
            if 'property_types' in response.aggregations:
                aggregations['property_types'] = response.aggregations['property_types']
            
            # Price histogram
            if 'price_histogram' in response.aggregations:
                aggregations['price_histogram'] = response.aggregations['price_histogram']
            
            # Bedroom stats
            if 'bedroom_stats' in response.aggregations:
                aggregations['bedroom_stats'] = response.aggregations['bedroom_stats']
        
        return DemoQueryResult(
            query_name="Price Range Search with Analytics",
            query_description=f"Search properties in ${min_price:,.0f}-${max_price:,.0f} range with statistical aggregations for market analysis",
            execution_time_ms=exec_time,
            total_hits=response.total_hits,
            returned_hits=len(results),
            results=results,
            query_dsl=request.to_dict(),
            aggregations=aggregations,
            es_features=[
                "Range Query: Filter properties by price range",
                "Stats Aggregation: Calculate min, max, avg, sum statistics",
                "Histogram Aggregation: Price distribution in $100k buckets",
                "Terms Aggregation: Group by property types",
                "Multi-Aggregation: Multiple analytics in single query"
            ],
            indexes_used=[
                "properties index: 420 real estate listings",
                "Aggregation fields: price, property_type, bedrooms",
                "Statistical analysis across matching properties"
            ],
            explanation=f"Properties ${min_price:,.0f}-${max_price:,.0f} with statistical analysis"
        )


# Public API functions for backward compatibility
def demo_basic_property_search(
    es_client: Elasticsearch,
    query_text: str = "family home with pool",
    size: int = 10
) -> DemoQueryResult:
    """
    Demo 1: Basic property search using multi-match query.
    
    Refactored to use Pydantic models for type safety.
    See PropertySearchDemo.demo_basic_search for implementation.
    """
    demo = PropertySearchDemo(es_client)
    return demo.demo_basic_search(query_text)


def demo_filtered_property_search(
    es_client: Elasticsearch,
    property_type: str = "Single Family",
    min_price: float = 300000,
    max_price: float = 800000,
    min_bedrooms: int = 3,
    min_bathrooms: float = 2.0,
    amenities: Optional[List[str]] = None
) -> DemoQueryResult:
    """
    Demo 2: Filtered property search with multiple criteria.
    
    Refactored to use Pydantic models for type safety.
    See PropertySearchDemo.demo_filtered_search for implementation.
    """
    demo = PropertySearchDemo(es_client)
    return demo.demo_filtered_search(
        property_type=property_type,
        min_price=min_price,
        max_price=max_price,
        min_bedrooms=min_bedrooms,
        min_bathrooms=min_bathrooms
    )


def demo_geo_distance_search(
    es_client: Elasticsearch,
    center_lat: float = 37.7749,
    center_lon: float = -122.4194,
    radius_km: float = 5.0,
    property_type: Optional[str] = None,
    max_price: Optional[float] = None
) -> DemoQueryResult:
    """
    Demo 3: Geo-distance search for properties near a location.
    
    Refactored to use Pydantic models for type safety.
    See PropertySearchDemo.demo_geo_search for implementation.
    """
    demo = PropertySearchDemo(es_client)
    return demo.demo_geo_search(
        center_lat=center_lat,
        center_lon=center_lon,
        radius_km=radius_km,
        max_price=max_price
    )


def demo_price_range_search(
    es_client: Elasticsearch,
    min_price: float = 400000,
    max_price: float = 800000
) -> DemoQueryResult:
    """
    Demo 4: Price range search with aggregation statistics.
    
    Refactored to use Pydantic models for type safety.
    See PropertySearchDemo.demo_price_range_with_analytics for implementation.
    """
    demo = PropertySearchDemo(es_client)
    return demo.demo_price_range_with_analytics(
        min_price=min_price,
        max_price=max_price
    )


# Aliases for backward compatibility with existing imports
demo_property_filter = demo_filtered_property_search
demo_geo_search = demo_geo_distance_search