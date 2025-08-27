"""Core property search demo queries using direct Elasticsearch DSL."""

from typing import Dict, Any, Optional, List
from elasticsearch import Elasticsearch
import logging

from .models import (
    DemoQueryResult,
    PropertySearchParams,
    PropertyFilterParams,
    GeoSearchParams
)

logger = logging.getLogger(__name__)


def demo_basic_property_search(
    es_client: Elasticsearch,
    query_text: str = "family home with pool",
    size: int = 10
) -> DemoQueryResult:
    """
    Demo 1: Basic property search using multi-match query.
    
    ELASTICSEARCH CONCEPTS:
    - LEAF QUERY CLAUSE: multi_match is a leaf query that searches for text
    - QUERY CONTEXT: This runs in query context, calculating relevance scores
    - FIELD BOOSTING: Using ^ operator to weight field importance
    - FUZZY MATCHING: Handles typos and variations
    
    Searches across description, features, amenities, and location fields
    with field boosting and fuzzy matching.
    
    Args:
        es_client: Elasticsearch client
        query_text: Search query text
        size: Number of results to return
        
    Returns:
        DemoQueryResult with search results
    """
    query = {
        "query": {
            # MULTI_MATCH QUERY: A leaf query clause that searches text across multiple fields
            # This is one of the most versatile full-text queries in Elasticsearch
            "multi_match": {
                "query": query_text,  # The text to search for
                
                # FIELD BOOSTING: Fields with ^ boost scores when matches are found
                # Higher boost = more important for relevance ranking
                "fields": [
                    "description^2",      # 2x boost - property descriptions are most important
                    "features^1.5",       # 1.5x boost - features are quite important
                    "amenities",          # 1x boost (default) - standard importance
                    "address.city",       # Nested field search for location
                    "address.street",     # Another nested field
                    "neighborhood_name"   # Neighborhood context
                ],
                
                # QUERY TYPE: "best_fields" finds the best matching field for each document
                # Other options: "most_fields", "cross_fields", "phrase", "phrase_prefix"
                "type": "best_fields",
                
                # FUZZINESS: Allows matching with typos/variations
                # "AUTO" adjusts fuzziness based on term length (recommended)
                # 0-2 chars: must match exactly
                # 3-5 chars: one edit allowed  
                # >5 chars: two edits allowed
                "fuzziness": "AUTO",
                
                # PREFIX_LENGTH: Number of initial characters that must match exactly
                # Prevents excessive fuzzy matches on short prefixes
                "prefix_length": 2
            }
        },
        
        # RESULT SIZE: Maximum number of documents to return
        "size": size,
        
        # SOURCE FILTERING: Specify which fields to include in results
        # Reduces network overhead by excluding unnecessary fields
        "_source": [
            "listing_id", "property_type", "price", "bedrooms", "bathrooms",
            "square_feet", "address", "description", "features"
        ],
        
        # HIGHLIGHTING: Shows matched text fragments with emphasis
        # Helps users understand why documents matched
        "highlight": {
            "fields": {
                "description": {},  # Default highlighter settings
                "features": {}      # Will wrap matches in <em> tags
            }
        }
    }
    
    try:
        response = es_client.search(index="properties", body=query)
        
        results = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            if 'highlight' in hit:
                source['_highlights'] = hit['highlight']
            results.append(source)
        
        return DemoQueryResult(
            query_name="Basic Property Search",
            execution_time_ms=response.get('took', 0),
            total_hits=response['hits']['total']['value'],
            returned_hits=len(results),
            results=results,
            query_dsl=query
        )
    except Exception as e:
        logger.error(f"Error in basic property search: {e}")
        return DemoQueryResult(
            query_name="Basic Property Search",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=query
        )


def demo_property_filter(
    es_client: Elasticsearch,
    property_type: Optional[str] = "condo",
    min_bedrooms: Optional[int] = 2,
    max_price: Optional[float] = 750000,
    cities: Optional[List[str]] = None,
    features: Optional[List[str]] = None,
    size: int = 10
) -> DemoQueryResult:
    """
    Demo 2: Property filter search with multiple criteria.
    
    Demonstrates bool query with multiple filter conditions for
    property type, bedrooms, price range, location, and features.
    
    Args:
        es_client: Elasticsearch client
        property_type: Type of property to filter
        min_bedrooms: Minimum number of bedrooms
        max_price: Maximum price
        cities: List of cities to filter
        features: Required features
        size: Number of results
        
    Returns:
        DemoQueryResult with filtered results
    """
    # Build filter conditions dynamically based on provided criteria
    filters = []
    
    if property_type:
        # TERM QUERY: Exact match on keyword field (not analyzed)
        # .keyword suffix uses the keyword analyzer for exact matching
        filters.append({"term": {"property_type.keyword": property_type}})
    
    if min_bedrooms is not None:
        # RANGE QUERY: Numeric range filter
        # gte = greater than or equal, also supports gt, lt, lte
        filters.append({"range": {"bedrooms": {"gte": min_bedrooms}}})
    
    if max_price is not None:
        # RANGE QUERY: Upper bound price filter
        # lte = less than or equal
        filters.append({"range": {"price": {"lte": max_price}}})
    
    if cities:
        # TERMS QUERY: Match any value in the list (OR operation)
        # Like SQL's IN clause
        filters.append({"terms": {"address.city.keyword": cities}})
    
    if features:
        # Multiple TERM queries create an AND condition when in same filter array
        for feature in features:
            filters.append({"term": {"features": feature.lower()}})
    
    query = {
        "query": {
            # BOOL QUERY: Compound query clause for combining multiple queries
            # The Swiss Army knife of Elasticsearch queries
            "bool": {
                # FILTER CONTEXT: Queries here don't calculate scores
                # - Faster than query context (cacheable)
                # - Used for yes/no questions
                # - All conditions must match (AND logic)
                "filter": filters
                
                # Other bool query clauses (not used here):
                # "must": [] - Query context, affects score, AND logic
                # "should": [] - Query context, affects score, OR logic
                # "must_not": [] - Filter context, excludes documents
            }
        } if filters else {"match_all": {}},  # Fallback if no filters
        
        "size": size,
        
        "_source": [
            "listing_id", "property_type", "price", "bedrooms", "bathrooms",
            "square_feet", "address", "features", "amenities"
        ],
        
        # SORTING: Define sort order for results
        "sort": [
            {"price": {"order": "asc"}},  # Primary sort: lowest price first
            "_score"  # Secondary sort: relevance (though filters don't generate scores)
        ]
    }
    
    try:
        response = es_client.search(index="properties", body=query)
        
        results = []
        for hit in response['hits']['hits']:
            results.append(hit['_source'])
        
        return DemoQueryResult(
            query_name=f"Property Filter (type={property_type}, beds>={min_bedrooms}, price<=${max_price})",
            execution_time_ms=response.get('took', 0),
            total_hits=response['hits']['total']['value'],
            returned_hits=len(results),
            results=results,
            query_dsl=query
        )
    except Exception as e:
        logger.error(f"Error in property filter search: {e}")
        return DemoQueryResult(
            query_name="Property Filter",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=query
        )


def demo_geo_search(
    es_client: Elasticsearch,
    latitude: float = 37.7749,
    longitude: float = -122.4194,
    distance: str = "5km",
    size: int = 10
) -> DemoQueryResult:
    """
    Demo 3: Geographic distance search.
    
    Finds properties within a specified distance from a geographic point,
    sorted by distance from the center point.
    
    Args:
        es_client: Elasticsearch client
        latitude: Center point latitude (default: San Francisco)
        longitude: Center point longitude
        distance: Search radius (e.g., '5km', '10mi')
        size: Number of results
        
    Returns:
        DemoQueryResult with geo-filtered results
    """
    query = {
        "query": {
            # COMPOUND QUERY: Bool query wraps our geo filter
            "bool": {
                # FILTER CONTEXT: Geo queries often run in filter context
                # No scoring needed - either within distance or not
                "filter": {
                    # GEO_DISTANCE QUERY: Special query type for geographic data
                    # Requires geo_point field mapping
                    "geo_distance": {
                        # DISTANCE: Can use various units (km, mi, m, yd, ft)
                        "distance": distance,
                        
                        # GEO_POINT FIELD: Must be mapped as geo_point type
                        "address.location": {
                            "lat": latitude,
                            "lon": longitude
                        }
                        # Alternative formats:
                        # "address.location": "40.715,-74.011"  # String
                        # "address.location": [lon, lat]        # Array (note: lon first!)
                        # "address.location": {"lat": 40.715, "lon": -74.011}  # Object
                    }
                }
            }
        },
        
        # GEO SORTING: Sort by distance from a point
        "sort": [
            {
                "_geo_distance": {
                    # Reference point for distance calculation
                    "address.location": {
                        "lat": latitude,
                        "lon": longitude
                    },
                    "unit": "km",  # Unit for sort values
                    "order": "asc"  # Nearest first
                    
                    # Other options:
                    # "mode": "min" - For fields with multiple geo points
                    # "distance_type": "arc" (default) or "plane" (faster, less accurate)
                }
            }
        ],
        
        "size": size,
        
        "_source": [
            "listing_id", "property_type", "price", "bedrooms", "bathrooms",
            "address", "description"
        ],
        
        # SCRIPT FIELDS: Computed fields using Painless scripting language
        # Calculate values at query time without storing them
        "script_fields": {
            "distance_km": {
                "script": {
                    # SCRIPT PARAMETERS: Pass values safely to scripts
                    "params": {
                        "lat": latitude,
                        "lon": longitude
                    },
                    # PAINLESS SCRIPT: Elasticsearch's scripting language
                    # arcDistance returns distance in meters
                    "source": """
                        if (doc['address.location'].size() == 0) return null;
                        return doc['address.location'].arcDistance(params.lat, params.lon) / 1000.0;
                    """
                }
            }
        }
    }
    
    try:
        response = es_client.search(index="properties", body=query)
        
        results = []
        for hit in response['hits']['hits']:
            result = hit['_source']
            if 'fields' in hit and 'distance_km' in hit['fields']:
                result['_distance_km'] = hit['fields']['distance_km'][0] if hit['fields']['distance_km'] else None
            if 'sort' in hit:
                result['_sort_distance'] = hit['sort'][0]
            results.append(result)
        
        return DemoQueryResult(
            query_name=f"Geo-Distance Search (within {distance} of {latitude:.4f},{longitude:.4f})",
            execution_time_ms=response.get('took', 0),
            total_hits=response['hits']['total']['value'],
            returned_hits=len(results),
            results=results,
            query_dsl=query
        )
    except Exception as e:
        logger.error(f"Error in geo-distance search: {e}")
        return DemoQueryResult(
            query_name="Geo-Distance Search",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=query
        )