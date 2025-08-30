"""
Aggregation demo queries for statistical analysis.

ELASTICSEARCH AGGREGATIONS OVERVIEW:
- Aggregations provide analytics and statistics on your data
- They operate alongside search requests (or independently with size:0)
- Three main types: Metric (math), Bucket (grouping), Pipeline (post-processing)
- Can be nested for complex multi-dimensional analysis
"""

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
        # SIZE: 0 means don't return documents, only aggregations
        # This improves performance when you only need statistics
        "size": 0,
        
        # AGGREGATIONS: The analytics framework of Elasticsearch
        "aggs": {
            # BUCKET AGGREGATION: Groups documents into buckets
            "by_neighborhood": {
                # TERMS AGGREGATION: Creates a bucket for each unique value
                # Similar to SQL's GROUP BY
                "terms": {
                    "field": "neighborhood_id.keyword",  # Must use keyword field for exact matching
                    "size": size,  # Maximum number of buckets to return
                    
                    # ORDER: Sort buckets by a metric (can reference sub-aggregations)
                    "order": {"property_count": "desc"}  # Most properties first
                    # Other options: {"_count": "desc"}, {"_key": "asc"}, {"avg_price": "desc"}
                },
                
                # SUB-AGGREGATIONS: Calculate metrics for each bucket
                # These run in the context of their parent bucket
                "aggs": {
                    # METRIC AGGREGATION: Single-value numeric metric
                    "property_count": {
                        "value_count": {"field": "listing_id"}  # Count unique values
                    },
                    
                    # AVG AGGREGATION: Calculate average value
                    "avg_price": {
                        "avg": {"field": "price"}
                    },
                    
                    # MIN/MAX AGGREGATIONS: Find extremes
                    "min_price": {
                        "min": {"field": "price"}
                    },
                    "max_price": {
                        "max": {"field": "price"}
                    },
                    
                    # Multiple metrics on different fields
                    "avg_bedrooms": {
                        "avg": {"field": "bedrooms"}
                    },
                    "avg_square_feet": {
                        "avg": {"field": "square_feet"}
                    },
                    "price_per_sqft": {
                        "avg": {"field": "price_per_sqft"}
                    },
                    
                    # NESTED BUCKET AGGREGATION: Create sub-buckets within each neighborhood
                    "property_types": {
                        "terms": {
                            "field": "property_type",
                            "size": 10  # Top 10 property types per neighborhood
                        }
                    }
                }
            },
            
            # GLOBAL METRICS: Calculate across all documents (not per bucket)
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
            query_name="Demo 4: Neighborhood Statistics Aggregation",
            query_description=f"Aggregates property data by neighborhood showing average prices, counts, and breakdowns for top {size} neighborhoods",
            execution_time_ms=response.get('took', 0),
            total_hits=response['aggregations']['total_properties']['value'] if 'aggregations' in response else 0,
            returned_hits=len(results),
            results=results,
            aggregations=response.get('aggregations', {}),
            query_dsl=query,
            es_features=[
                "Terms Aggregation - Groups properties by neighborhood_id (like SQL GROUP BY)",
                "Metric Aggregations - Calculates avg, min, max prices and other statistics",
                "Nested Aggregations - Property type breakdown within each neighborhood",
                "Sub-aggregations - Multiple metrics calculated per bucket",
                "Ordering - Sorts neighborhoods by property count",
                "Global Aggregations - Overall statistics across all properties"
            ],
            indexes_used=[
                "properties index - Real estate property listings",
                f"Returns statistics for top {size} neighborhoods by property count"
            ]
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
        "size": 0,  # Only aggregations, no documents
        
        # QUERY WITH AGGREGATIONS: Filter documents before aggregating
        # Aggregations only operate on documents matching the query
        "query": {
            # RANGE QUERY in QUERY CONTEXT: Although it doesn't need scoring,
            # it's used here to limit the aggregation scope
            "range": {
                "price": {
                    "gte": min_price,  # Greater than or equal
                    "lte": max_price   # Less than or equal
                }
            }
        },
        
        "aggs": {
            # HISTOGRAM AGGREGATION: Fixed-size interval buckets
            # Like terms but for numeric ranges
            "price_histogram": {
                "histogram": {
                    "field": "price",
                    "interval": interval,  # Bucket width (e.g., $100,000)
                    
                    # MIN_DOC_COUNT: Omit empty buckets (0 = show all)
                    "min_doc_count": 1,
                    
                    # EXTENDED_BOUNDS: Force histogram range even if no data
                    # Useful for consistent visualizations
                    "extended_bounds": {
                        "min": min_price,
                        "max": max_price
                    }
                    # Other options:
                    # "offset": 50000 - Shift bucket boundaries
                    # "keyed": true - Return as object instead of array
                },
                
                # SUB-AGGREGATIONS per price bucket
                "aggs": {
                    # Break down each price range by property type
                    "by_property_type": {
                        "terms": {
                            "field": "property_type",
                            "size": 10
                        }
                    },
                    
                    # STATS AGGREGATION: Multiple metrics in one
                    # Returns: min, max, avg, sum, count
                    "stats": {
                        "stats": {"field": "price"}
                    }
                }
            },
            
            # PERCENTILES AGGREGATION: Statistical distribution
            # Find values at specific percentile ranks
            "price_percentiles": {
                "percentiles": {
                    "field": "price",
                    "percents": [25, 50, 75, 90, 95, 99]  # Quartiles + high percentiles
                    # 50th percentile = median
                    # 25th-75th = interquartile range
                }
            },
            
            # COMPLEX NESTED AGGREGATION: Stats per property type
            "by_property_type_stats": {
                "terms": {
                    "field": "property_type",
                    "size": 10
                },
                "aggs": {
                    # Multiple metric aggregations per bucket
                    "price_stats": {
                        "stats": {"field": "price"}
                    },
                    "price_percentiles": {
                        "percentiles": {
                            "field": "price",
                            "percents": [50]  # Just the median
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
            query_name=f"Demo 5: Price Distribution Analysis",
            query_description=f"Creates histogram of property prices from ${min_price:,.0f} to ${max_price:,.0f} with ${interval:,.0f} intervals, including property type breakdowns",
            execution_time_ms=response.get('took', 0),
            total_hits=response['hits']['total']['value'] if 'hits' in response else 0,
            returned_hits=len(results),
            results=results,
            aggregations=aggregations,
            query_dsl=query,
            es_features=[
                "Histogram Aggregation - Creates fixed-size price range buckets",
                "Range Query - Filters properties within price boundaries",
                "Percentiles Aggregation - Calculates price distribution percentiles",
                "Stats Aggregation - Multiple metrics (min/max/avg/sum) in one aggregation",
                "Nested Terms Aggregation - Property type breakdown per price bucket",
                "Extended Bounds - Forces consistent histogram range",
                "Min Doc Count - Omits empty buckets for cleaner results"
            ],
            indexes_used=[
                "properties index - Real estate property listings",
                f"Analyzes price distribution across {(max_price - min_price) / interval:.0f} price ranges"
            ]
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