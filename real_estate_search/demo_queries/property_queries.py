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
            "multi_match": {
                "query": query_text,
                "fields": [
                    "description^2",
                    "features^1.5",
                    "amenities",
                    "address.city",
                    "address.street",
                    "neighborhood_name"
                ],
                "type": "best_fields",
                "fuzziness": "AUTO",
                "prefix_length": 2
            }
        },
        "size": size,
        "_source": [
            "listing_id", "property_type", "price", "bedrooms", "bathrooms",
            "square_feet", "address", "description", "features"
        ],
        "highlight": {
            "fields": {
                "description": {},
                "features": {}
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
    # Build filter conditions
    filters = []
    
    if property_type:
        filters.append({"term": {"property_type.keyword": property_type}})
    
    if min_bedrooms is not None:
        filters.append({"range": {"bedrooms": {"gte": min_bedrooms}}})
    
    if max_price is not None:
        filters.append({"range": {"price": {"lte": max_price}}})
    
    if cities:
        filters.append({"terms": {"address.city.keyword": cities}})
    
    if features:
        for feature in features:
            filters.append({"term": {"features": feature.lower()}})
    
    query = {
        "query": {
            "bool": {
                "filter": filters
            }
        } if filters else {"match_all": {}},
        "size": size,
        "_source": [
            "listing_id", "property_type", "price", "bedrooms", "bathrooms",
            "square_feet", "address", "features", "amenities"
        ],
        "sort": [
            {"price": {"order": "asc"}},
            "_score"
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
            "bool": {
                "filter": {
                    "geo_distance": {
                        "distance": distance,
                        "address.location": {
                            "lat": latitude,
                            "lon": longitude
                        }
                    }
                }
            }
        },
        "sort": [
            {
                "_geo_distance": {
                    "address.location": {
                        "lat": latitude,
                        "lon": longitude
                    },
                    "unit": "km",
                    "order": "asc"
                }
            }
        ],
        "size": size,
        "_source": [
            "listing_id", "property_type", "price", "bedrooms", "bathrooms",
            "address", "description"
        ],
        "script_fields": {
            "distance_km": {
                "script": {
                    "params": {
                        "lat": latitude,
                        "lon": longitude
                    },
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