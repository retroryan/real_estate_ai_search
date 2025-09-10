"""
Query construction logic for property searches.

This module contains pure query building functions that construct Elasticsearch
queries for various property search scenarios. No side effects, no display logic,
no Elasticsearch client dependencies.
"""

from typing import Dict, Any, Optional, List
import logging

from ..base_models import SearchRequest, SourceFilter
from ..demo_config import demo_config
from ...indexer.enums import FieldName

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
                    "features^1.5",       # Important features
                    "address.street",     # Location context
                    "address.city",       # City search
                ],
                "type": "best_fields",   # Use best matching field's score
                "fuzziness": "AUTO",      # Adaptive fuzzy matching
                "prefix_length": 2,       # Minimum exact prefix
                "operator": "OR"          # Match ANY term (vs AND for ALL)
            }
        }
        
        request = SearchRequest(
            index=["properties"],
            query=query,
            size=size,
            source=SourceFilter(includes=[  # Only return needed fields
                "listing_id", "property_type", "price", 
                "bedrooms", "bathrooms", "square_feet",
                "address", "description", "features"
            ])
        )
        
        if highlight:
            request.highlight = {
                "fields": {
                    "description": {"fragment_size": 150},
                    "features": {"fragment_size": 100}
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
                filters.append({"match": {"features": amenity}})
        
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
            index=["properties"],
            query=query,
            size=size,
            sort=[{"price": {"order": "asc"}}],  # Sort by price when filtering
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
            index=["properties"],
            query=query,
            size=size,
            sort=sort,
        )
    
    # ==================== AGGREGATION QUERIES ====================
    
    @staticmethod
    def neighborhood_stats_aggregation(size: int = None) -> Dict[str, Any]:
        """
        Build neighborhood statistics aggregation query.
        
        Creates a terms aggregation grouped by neighborhood with multiple
        metric sub-aggregations for each bucket.
        
        Args:
            size: Maximum number of neighborhoods to return (uses config default if None)
            
        Returns:
            Elasticsearch query dictionary with aggregations
        """
        if size is None:
            size = demo_config.aggregation_defaults.neighborhood_size
            
        return {
            "size": 0,  # Don't return documents, only aggregations
            
            "aggs": {
                # Bucket aggregation: Groups documents by neighborhood
                "by_neighborhood": {
                    "terms": {
                        "field": FieldName.NEIGHBORHOOD_ID,
                        "size": size,
                        "order": {"property_count": "desc"}  # Most properties first
                    },
                    
                    # Sub-aggregations for each neighborhood bucket
                    "aggs": {
                        "property_count": {
                            "value_count": {"field": FieldName.LISTING_ID}
                        },
                        "avg_price": {
                            "avg": {"field": FieldName.PRICE}
                        },
                        "min_price": {
                            "min": {"field": FieldName.PRICE}
                        },
                        "max_price": {
                            "max": {"field": FieldName.PRICE}
                        },
                        "avg_bedrooms": {
                            "avg": {"field": FieldName.BEDROOMS}
                        },
                        "avg_square_feet": {
                            "avg": {"field": FieldName.SQUARE_FEET}
                        },
                        "price_per_sqft": {
                            "avg": {"field": FieldName.PRICE_PER_SQFT}
                        },
                        # Nested bucket aggregation for property types
                        "property_types": {
                            "terms": {
                                "field": FieldName.PROPERTY_TYPE,
                                "size": demo_config.aggregation_defaults.max_buckets
                            }
                        }
                    }
                },
                
                # Global metrics across all documents
                "total_properties": {
                    "value_count": {"field": FieldName.LISTING_ID}
                },
                "overall_avg_price": {
                    "avg": {"field": FieldName.PRICE}
                }
            }
        }
    
    @staticmethod
    def price_distribution_aggregation(
        interval: int = None,
        min_price: float = None,
        max_price: float = None
    ) -> Dict[str, Any]:
        """
        Build price distribution histogram query.
        
        Creates a histogram aggregation for price ranges with percentiles
        and property type breakdowns.
        
        Args:
            interval: Bucket width for histogram (uses config default if None)
            min_price: Minimum price for range filter (uses config default if None)
            max_price: Maximum price for range filter (uses config default if None)
            
        Returns:
            Elasticsearch query dictionary with histogram aggregations
        """
        if interval is None:
            interval = demo_config.aggregation_defaults.price_interval
        if min_price is None:
            min_price = demo_config.aggregation_defaults.min_price
        if max_price is None:
            max_price = demo_config.aggregation_defaults.max_price
            
        return {
            "size": demo_config.aggregation_defaults.top_properties_count,  # Return top properties
            
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
                        "field": FieldName.PRICE,
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
                                "field": FieldName.PROPERTY_TYPE,
                                "size": demo_config.aggregation_defaults.max_buckets
                            }
                        },
                        "stats": {
                            "stats": {"field": FieldName.PRICE}
                        }
                    }
                },
                
                # Percentiles for statistical distribution
                "price_percentiles": {
                    "percentiles": {
                        "field": FieldName.PRICE,
                        "percents": demo_config.aggregation_defaults.percentiles
                    }
                },
                
                # Statistics per property type
                "by_property_type_stats": {
                    "terms": {
                        "field": FieldName.PROPERTY_TYPE,
                        "size": demo_config.aggregation_defaults.max_buckets
                    },
                    "aggs": {
                        "price_stats": {
                            "stats": {"field": FieldName.PRICE}
                        },
                        "price_percentiles": {
                            "percentiles": {
                                "field": FieldName.PRICE,
                                "percents": [50]  # Just median
                            }
                        }
                    }
                }
            }
        }
    
    # ==================== SEMANTIC QUERIES ====================
    
    @staticmethod
    def knn_semantic_search(
        query_vector: List[float], 
        size: int = None,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Build a KNN query for semantic search.
        
        Args:
            query_vector: The embedding vector for the query
            size: Number of results to return (uses config default if None)
            fields: Fields to retrieve (defaults to basic property fields)
            
        Returns:
            Elasticsearch query dictionary
        """
        if size is None:
            size = demo_config.advanced_defaults.semantic_similarity_size
            
        if fields is None:
            fields = [
                "listing_id", "property_type", "price", 
                "bedrooms", "bathrooms", "square_feet",
                "address", "description", "features"
            ]
            
        knn_num_candidates_multiplier = 10  # Default multiplier
        
        query = {
            "knn": {
                "field": "embedding",
                "query_vector": query_vector,
                "k": size,
                "num_candidates": min(100, size * knn_num_candidates_multiplier)
            },
            "size": size,
            "_source": fields
        }
        
        logger.debug(f"Built KNN query for {size} results with {len(query_vector)}-dim vector")
        return query
    
    @staticmethod
    def keyword_search(
        query_text: str,
        size: int = None,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Build a keyword-based multi-match query.
        
        Args:
            query_text: The text query
            size: Number of results to return (uses config default if None)
            fields: Fields to retrieve (defaults to basic property fields)
            
        Returns:
            Elasticsearch query dictionary
        """
        if size is None:
            size = demo_config.advanced_defaults.semantic_similarity_size
            
        if fields is None:
            fields = [
                "listing_id", "property_type", "price", 
                "bedrooms", "bathrooms", "square_feet",
                "address", "description", "features"
            ]
            
        query = {
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": [
                        "description^2",
                        "features^1.5",
                        "address.street",
                        "address.city",
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "size": size,
            "_source": fields
        }
        
        logger.debug(f"Built keyword query for '{query_text}' with size {size}")
        return query
    
    @staticmethod
    def price_range_with_stats(
        min_price: float,
        max_price: float,
        include_stats: bool = True
    ) -> SearchRequest:
        """
        Build a price range query with statistical aggregations.
        
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
                        "field": "property_type",
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
            index=["properties"],
            query=query,
            size=20,
            aggs=aggs,
            sort=[{"price": {"order": "asc"}}],
        )