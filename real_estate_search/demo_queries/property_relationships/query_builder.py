"""
Query builder for property relationships searches.

This module constructs Elasticsearch queries for the property_relationships index,
which contains denormalized property data with embedded neighborhood and Wikipedia information.
"""

import logging
from typing import Dict, Any, Optional

from ..demo_config import demo_config
from ...indexer.enums import IndexName

logger = logging.getLogger(__name__)


class PropertyRelationshipsQueryBuilder:
    """
    Builds Elasticsearch queries for property relationships searches.
    
    This class constructs queries specifically for the property_relationships
    index, which contains denormalized data with embedded related information.
    """
    
    @staticmethod
    def build_listing_query(listing_id: str) -> Dict[str, Any]:
        """
        Build a term query to retrieve a specific listing by ID.
        
        Args:
            listing_id: The listing ID to search for
            
        Returns:
            Elasticsearch query DSL
        """
        if not listing_id:
            raise ValueError("listing_id is required for listing query")
        
        return {
            "query": {
                "term": {
                    "listing_id": listing_id
                }
            },
            "size": 1,
            "_source": True,  # Return all fields
            "sort": [
                {"_score": "desc"}
            ]
        }
    
    @staticmethod
    def build_search_query(
        query_text: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        property_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_bedrooms: Optional[int] = None,
        size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build a search query with optional filters.
        
        Args:
            query_text: Text to search across property fields
            city: Filter by city
            state: Filter by state
            property_type: Filter by property type
            min_price: Minimum price filter
            max_price: Maximum price filter
            min_bedrooms: Minimum bedrooms filter
            size: Number of results to return
            
        Returns:
            Elasticsearch query DSL
        """
        # Build the query
        must_clauses = []
        filter_clauses = []
        
        # Text search if provided
        if query_text:
            must_clauses.append({
                "multi_match": {
                    "query": query_text,
                    "fields": [
                        "title^3",
                        "description^2",
                        "features",
                        "neighborhood.name^2",
                        "neighborhood.description",
                        "address.street",
                        "address.city",
                        "wikipedia_articles.title",
                        "wikipedia_articles.short_summary"
                    ],
                    "type": "best_fields",
                    "operator": "or"
                }
            })
        
        # Location filters
        if city:
            filter_clauses.append({
                "term": {
                    "address.city.keyword": city
                }
            })
        
        if state:
            filter_clauses.append({
                "term": {
                    "address.state.keyword": state
                }
            })
        
        # Property type filter
        if property_type:
            filter_clauses.append({
                "term": {
                    "property_type": property_type.lower()
                }
            })
        
        # Price range filter
        if min_price is not None or max_price is not None:
            price_range = {}
            if min_price is not None:
                price_range["gte"] = min_price
            if max_price is not None:
                price_range["lte"] = max_price
            filter_clauses.append({
                "range": {
                    "price": price_range
                }
            })
        
        # Bedrooms filter
        if min_bedrooms is not None:
            filter_clauses.append({
                "range": {
                    "bedrooms": {
                        "gte": min_bedrooms
                    }
                }
            })
        
        # Construct the final query
        if must_clauses or filter_clauses:
            query = {
                "bool": {}
            }
            if must_clauses:
                query["bool"]["must"] = must_clauses
            if filter_clauses:
                query["bool"]["filter"] = filter_clauses
        else:
            # If no conditions, match all
            query = {"match_all": {}}
        
        return {
            "query": query,
            "size": size or 10,
            "_source": True,
            "sort": [
                {"_score": "desc"},
                {"price": "desc"}
            ]
        }
    
    @staticmethod
    def build_aggregation_query(
        aggregation_type: str = "data_sources"
    ) -> Dict[str, Any]:
        """
        Build an aggregation query to get statistics about the data.
        
        Args:
            aggregation_type: Type of aggregation to perform
            
        Returns:
            Elasticsearch query DSL with aggregations
        """
        aggregations = {}
        
        if aggregation_type == "data_sources":
            # Count documents with each type of embedded data
            aggregations = {
                "has_neighborhood": {
                    "filter": {
                        "exists": {
                            "field": "neighborhood.neighborhood_id"
                        }
                    }
                },
                "has_wikipedia": {
                    "filter": {
                        "exists": {
                            "field": "wikipedia_articles"
                        }
                    }
                },
                "property_types": {
                    "terms": {
                        "field": "property_type",
                        "size": 10
                    }
                },
                "cities": {
                    "terms": {
                        "field": "address.city.keyword",
                        "size": 20
                    }
                }
            }
        elif aggregation_type == "price_stats":
            aggregations = {
                "price_stats": {
                    "stats": {
                        "field": "price"
                    }
                },
                "price_by_type": {
                    "terms": {
                        "field": "property_type",
                        "size": 10
                    },
                    "aggs": {
                        "avg_price": {
                            "avg": {
                                "field": "price"
                            }
                        }
                    }
                }
            }
        elif aggregation_type == "neighborhood_stats":
            aggregations = {
                "neighborhoods": {
                    "terms": {
                        "field": "neighborhood.name.keyword",
                        "size": 50
                    },
                    "aggs": {
                        "avg_price": {
                            "avg": {
                                "field": "price"
                            }
                        },
                        "property_count": {
                            "value_count": {
                                "field": "listing_id"
                            }
                        }
                    }
                }
            }
        
        return {
            "query": {"match_all": {}},
            "size": 0,  # Don't return documents, only aggregations
            "aggs": aggregations
        }
    
    @staticmethod
    def validate_query(query_dsl: Dict[str, Any]) -> bool:
        """
        Validate that a query DSL is properly structured.
        
        Args:
            query_dsl: Query DSL to validate
            
        Returns:
            True if valid, raises ValueError if not
        """
        if not query_dsl:
            raise ValueError("Query DSL cannot be empty")
        
        if "query" not in query_dsl:
            raise ValueError("Query DSL must contain a 'query' field")
        
        # Check for valid query types
        query = query_dsl["query"]
        valid_root_keys = {
            "match_all", "term", "terms", "bool", "match", 
            "multi_match", "range", "exists", "prefix", "wildcard"
        }
        
        if not any(key in query for key in valid_root_keys):
            raise ValueError(f"Query must contain one of: {valid_root_keys}")
        
        return True
    
    @staticmethod
    def add_highlighting(query_dsl: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add highlighting configuration to a query.
        
        Args:
            query_dsl: Query DSL to enhance with highlighting
            
        Returns:
            Enhanced query DSL with highlighting
        """
        query_dsl["highlight"] = {
            "fields": {
                "title": {},
                "description": {"fragment_size": 200},
                "features": {},
                "neighborhood.description": {"fragment_size": 150},
                "wikipedia_articles.short_summary": {"fragment_size": 150}
            },
            "pre_tags": ["<mark>"],
            "post_tags": ["</mark>"]
        }
        return query_dsl
    
    @staticmethod
    def build_default_query() -> Dict[str, Any]:
        """
        Build a default query to retrieve recent listings.
        
        Returns:
            Elasticsearch query DSL
        """
        return {
            "query": {
                "match_all": {}
            },
            "size": 10,
            "_source": True,
            "sort": [
                {"listing_date": "desc"},
                {"_score": "desc"}
            ]
        }