"""
Aggregation query construction for Elasticsearch.

This module handles the construction of various aggregation queries including
terms aggregations, histograms, percentiles, and nested aggregations.
"""

from typing import Dict, Any, Optional
import logging

from .constants import (
    DEFAULT_NEIGHBORHOOD_SIZE,
    DEFAULT_PRICE_INTERVAL,
    DEFAULT_MIN_PRICE,
    DEFAULT_MAX_PRICE,
    FIELD_LISTING_ID,
    FIELD_NEIGHBORHOOD_ID,
    FIELD_PRICE,
    FIELD_BEDROOMS,
    FIELD_SQUARE_FEET,
    FIELD_PRICE_PER_SQFT,
    FIELD_PROPERTY_TYPE,
    MAX_PROPERTY_TYPES_PER_BUCKET,
    PRICE_PERCENTILES,
    MEDIAN_PERCENTILE,
    TOP_PROPERTIES_TO_SHOW
)

logger = logging.getLogger(__name__)


class AggregationQueryBuilder:
    """Builder for Elasticsearch aggregation queries."""
    
    @staticmethod
    def build_neighborhood_stats_query(size: int = DEFAULT_NEIGHBORHOOD_SIZE) -> Dict[str, Any]:
        """
        Build neighborhood statistics aggregation query.
        
        Creates a terms aggregation grouped by neighborhood with multiple
        metric sub-aggregations for each bucket.
        
        Args:
            size: Maximum number of neighborhoods to return
            
        Returns:
            Elasticsearch query dictionary with aggregations
        """
        return {
            "size": 0,  # Don't return documents, only aggregations
            
            "aggs": {
                # Bucket aggregation: Groups documents by neighborhood
                "by_neighborhood": {
                    "terms": {
                        "field": FIELD_NEIGHBORHOOD_ID,
                        "size": size,
                        "order": {"property_count": "desc"}  # Most properties first
                    },
                    
                    # Sub-aggregations for each neighborhood bucket
                    "aggs": {
                        "property_count": {
                            "value_count": {"field": FIELD_LISTING_ID}
                        },
                        "avg_price": {
                            "avg": {"field": FIELD_PRICE}
                        },
                        "min_price": {
                            "min": {"field": FIELD_PRICE}
                        },
                        "max_price": {
                            "max": {"field": FIELD_PRICE}
                        },
                        "avg_bedrooms": {
                            "avg": {"field": FIELD_BEDROOMS}
                        },
                        "avg_square_feet": {
                            "avg": {"field": FIELD_SQUARE_FEET}
                        },
                        "price_per_sqft": {
                            "avg": {"field": FIELD_PRICE_PER_SQFT}
                        },
                        # Nested bucket aggregation for property types
                        "property_types": {
                            "terms": {
                                "field": FIELD_PROPERTY_TYPE,
                                "size": MAX_PROPERTY_TYPES_PER_BUCKET
                            }
                        }
                    }
                },
                
                # Global metrics across all documents
                "total_properties": {
                    "value_count": {"field": FIELD_LISTING_ID}
                },
                "overall_avg_price": {
                    "avg": {"field": FIELD_PRICE}
                }
            }
        }
    
    @staticmethod
    def build_price_distribution_query(
        interval: int = DEFAULT_PRICE_INTERVAL,
        min_price: float = DEFAULT_MIN_PRICE,
        max_price: float = DEFAULT_MAX_PRICE
    ) -> Dict[str, Any]:
        """
        Build price distribution histogram query.
        
        Creates a histogram aggregation for price ranges with percentiles
        and property type breakdowns.
        
        Args:
            interval: Bucket width for histogram
            min_price: Minimum price for range filter
            max_price: Maximum price for range filter
            
        Returns:
            Elasticsearch query dictionary with histogram aggregations
        """
        return {
            "size": TOP_PROPERTIES_TO_SHOW,  # Return top 5 most expensive properties
            
            # Sort by price descending to show most expensive
            "sort": [
                {"price": {"order": "desc"}}
            ],
            
            # Filter documents before aggregating
            "query": {
                "range": {
                    "price": {
                        "gte": min_price,
                        "lte": max_price
                    }
                }
            },
            
            "aggs": {
                # Histogram aggregation for price ranges
                "price_histogram": {
                    "histogram": {
                        "field": FIELD_PRICE,
                        "interval": interval,
                        "min_doc_count": 1,  # Omit empty buckets
                        "extended_bounds": {
                            "min": min_price,
                            "max": max_price
                        }
                    },
                    
                    # Sub-aggregations per price bucket
                    "aggs": {
                        "by_property_type": {
                            "terms": {
                                "field": FIELD_PROPERTY_TYPE,
                                "size": MAX_PROPERTY_TYPES_PER_BUCKET
                            }
                        },
                        "stats": {
                            "stats": {"field": FIELD_PRICE}
                        }
                    }
                },
                
                # Percentiles for statistical distribution
                "price_percentiles": {
                    "percentiles": {
                        "field": FIELD_PRICE,
                        "percents": PRICE_PERCENTILES
                    }
                },
                
                # Statistics per property type
                "by_property_type_stats": {
                    "terms": {
                        "field": FIELD_PROPERTY_TYPE,
                        "size": MAX_PROPERTY_TYPES_PER_BUCKET
                    },
                    "aggs": {
                        "price_stats": {
                            "stats": {"field": FIELD_PRICE}
                        },
                        "price_percentiles": {
                            "percentiles": {
                                "field": FIELD_PRICE,
                                "percents": MEDIAN_PERCENTILE
                            }
                        }
                    }
                }
            }
        }