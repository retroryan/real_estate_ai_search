"""Aggregation demo queries for statistical analysis."""

from typing import Dict, Any
from elasticsearch import Elasticsearch
import logging

from .models import DemoQueryResult

logger = logging.getLogger(__name__)


def demo_neighborhood_stats(
    es_client: Elasticsearch,
    size: int = 20
) -> DemoQueryResult:
    """
    Demo 4: Neighborhood statistics aggregation.
    
    Aggregates property data by neighborhood to show average prices,
    property counts, and other statistics per neighborhood.
    
    Args:
        es_client: Elasticsearch client
        size: Number of neighborhoods to include
        
    Returns:
        DemoQueryResult with aggregated statistics
    """
    query = {
        "size": 0,  # Don't return documents, only aggregations
        "aggs": {
            "by_neighborhood": {
                "terms": {
                    "field": "neighborhood_id.keyword",
                    "size": size,
                    "order": {"property_count": "desc"}
                },
                "aggs": {
                    "property_count": {
                        "value_count": {"field": "listing_id"}
                    },
                    "avg_price": {
                        "avg": {"field": "price"}
                    },
                    "min_price": {
                        "min": {"field": "price"}
                    },
                    "max_price": {
                        "max": {"field": "price"}
                    },
                    "avg_bedrooms": {
                        "avg": {"field": "bedrooms"}
                    },
                    "avg_square_feet": {
                        "avg": {"field": "square_feet"}
                    },
                    "price_per_sqft": {
                        "avg": {"field": "price_per_sqft"}
                    },
                    "property_types": {
                        "terms": {
                            "field": "property_type.keyword",
                            "size": 10
                        }
                    }
                }
            },
            "total_properties": {
                "value_count": {"field": "listing_id"}
            },
            "overall_avg_price": {
                "avg": {"field": "price"}
            }
        }
    }
    
    try:
        response = es_client.search(index="properties", body=query)
        
        # Format aggregation results
        results = []
        if 'aggregations' in response and 'by_neighborhood' in response['aggregations']:
            for bucket in response['aggregations']['by_neighborhood']['buckets']:
                results.append({
                    'neighborhood_id': bucket['key'],
                    'property_count': bucket['property_count']['value'],
                    'avg_price': round(bucket['avg_price']['value'], 2) if bucket['avg_price']['value'] else 0,
                    'min_price': bucket['min_price']['value'],
                    'max_price': bucket['max_price']['value'],
                    'avg_bedrooms': round(bucket['avg_bedrooms']['value'], 1) if bucket['avg_bedrooms']['value'] else 0,
                    'avg_square_feet': round(bucket['avg_square_feet']['value'], 0) if bucket['avg_square_feet']['value'] else 0,
                    'price_per_sqft': round(bucket['price_per_sqft']['value'], 2) if bucket['price_per_sqft']['value'] else 0,
                    'property_types': [
                        {'type': t['key'], 'count': t['doc_count']} 
                        for t in bucket['property_types']['buckets']
                    ]
                })
        
        return DemoQueryResult(
            query_name="Neighborhood Statistics Aggregation",
            execution_time_ms=response.get('took', 0),
            total_hits=response['aggregations']['total_properties']['value'] if 'aggregations' in response else 0,
            returned_hits=len(results),
            results=results,
            aggregations=response.get('aggregations', {}),
            query_dsl=query
        )
    except Exception as e:
        logger.error(f"Error in neighborhood stats aggregation: {e}")
        return DemoQueryResult(
            query_name="Neighborhood Statistics Aggregation",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=query
        )


def demo_price_distribution(
    es_client: Elasticsearch,
    interval: int = 100000,
    min_price: float = 0,
    max_price: float = 2000000
) -> DemoQueryResult:
    """
    Demo 5: Price distribution analysis.
    
    Creates a histogram of property prices with breakdown by property type,
    useful for understanding market price distributions.
    
    Args:
        es_client: Elasticsearch client
        interval: Price bucket interval (default: $100,000)
        min_price: Minimum price for histogram
        max_price: Maximum price for histogram
        
    Returns:
        DemoQueryResult with price distribution data
    """
    query = {
        "size": 0,
        "query": {
            "range": {
                "price": {
                    "gte": min_price,
                    "lte": max_price
                }
            }
        },
        "aggs": {
            "price_histogram": {
                "histogram": {
                    "field": "price",
                    "interval": interval,
                    "min_doc_count": 1,
                    "extended_bounds": {
                        "min": min_price,
                        "max": max_price
                    }
                },
                "aggs": {
                    "by_property_type": {
                        "terms": {
                            "field": "property_type.keyword",
                            "size": 10
                        }
                    },
                    "stats": {
                        "stats": {"field": "price"}
                    }
                }
            },
            "price_percentiles": {
                "percentiles": {
                    "field": "price",
                    "percents": [25, 50, 75, 90, 95, 99]
                }
            },
            "by_property_type_stats": {
                "terms": {
                    "field": "property_type.keyword",
                    "size": 10
                },
                "aggs": {
                    "price_stats": {
                        "stats": {"field": "price"}
                    },
                    "price_percentiles": {
                        "percentiles": {
                            "field": "price",
                            "percents": [50]
                        }
                    }
                }
            }
        }
    }
    
    try:
        response = es_client.search(index="properties", body=query)
        
        # Format histogram results
        results = []
        if 'aggregations' in response and 'price_histogram' in response['aggregations']:
            for bucket in response['aggregations']['price_histogram']['buckets']:
                range_start = bucket['key']
                range_end = range_start + interval
                
                property_type_breakdown = {}
                for type_bucket in bucket['by_property_type']['buckets']:
                    property_type_breakdown[type_bucket['key']] = type_bucket['doc_count']
                
                results.append({
                    'price_range': f"${range_start:,.0f} - ${range_end:,.0f}",
                    'range_start': range_start,
                    'range_end': range_end,
                    'count': bucket['doc_count'],
                    'property_types': property_type_breakdown,
                    'avg_price': bucket['stats']['avg'] if 'stats' in bucket else None
                })
        
        # Add percentiles to aggregations
        aggregations = response.get('aggregations', {})
        
        return DemoQueryResult(
            query_name=f"Price Distribution Analysis (${min_price:,.0f} - ${max_price:,.0f}, interval: ${interval:,.0f})",
            execution_time_ms=response.get('took', 0),
            total_hits=response['hits']['total']['value'] if 'hits' in response else 0,
            returned_hits=len(results),
            results=results,
            aggregations=aggregations,
            query_dsl=query
        )
    except Exception as e:
        logger.error(f"Error in price distribution analysis: {e}")
        return DemoQueryResult(
            query_name="Price Distribution Analysis",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=query
        )