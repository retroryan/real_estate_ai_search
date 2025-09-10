"""
Query construction logic for neighborhood searches.

This module contains pure query building functions that construct Elasticsearch
queries for neighborhood search scenarios. No side effects, no display logic,
no Elasticsearch client dependencies.
"""

from typing import Dict, Any, Optional, List
import logging

from ..demo_config import demo_config
from ...indexer.enums import FieldName, IndexName

logger = logging.getLogger(__name__)


class NeighborhoodQueryBuilder:
    """
    Builder class for constructing neighborhood search queries.
    
    This class encapsulates the logic for building various types of
    Elasticsearch queries for neighborhood searches and analytics.
    """
    
    @staticmethod
    def basic_search(
        query_text: str,
        size: int = 10
    ) -> Dict[str, Any]:
        """
        Build a basic neighborhood search query.
        
        Args:
            query_text: Text to search for
            size: Maximum results to return
            
        Returns:
            Elasticsearch query dictionary
        """
        return {
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": [
                        "name^2",           # Primary field
                        "description^1.5",  # Description content
                        "area_type",        # Area classification
                        "city",            # City context
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                    "operator": "OR"
                }
            },
            "size": size,
            "_source": [
                "neighborhood_id", "name", "description", 
                "walkability_score", "school_rating", "crime_rating",
                "city", "state", "area_type"
            ]
        }
    
    @staticmethod
    def filtered_search(
        min_walkability: Optional[int] = None,
        min_school_rating: Optional[float] = None,
        max_crime_rating: Optional[float] = None,
        city: Optional[str] = None,
        area_type: Optional[str] = None,
        size: int = 10
    ) -> Dict[str, Any]:
        """
        Build a filtered neighborhood search query.
        
        Args:
            min_walkability: Minimum walkability score
            min_school_rating: Minimum school rating
            max_crime_rating: Maximum crime rating (lower is better)
            city: Filter by city
            area_type: Filter by area type
            size: Maximum results
            
        Returns:
            Elasticsearch query dictionary with filters
        """
        filters: List[Dict[str, Any]] = []
        
        if min_walkability is not None:
            filters.append({"range": {"walkability_score": {"gte": min_walkability}}})
        
        if min_school_rating is not None:
            filters.append({"range": {"school_rating": {"gte": min_school_rating}}})
        
        if max_crime_rating is not None:
            filters.append({"range": {"crime_rating": {"lte": max_crime_rating}}})
        
        if city:
            filters.append({"term": {"city.keyword": city}})
        
        if area_type:
            filters.append({"term": {"area_type": area_type.lower()}})
        
        # Use match_all if no filters
        if filters:
            query = {
                "bool": {
                    "filter": filters
                }
            }
        else:
            query = {"match_all": {}}
        
        return {
            "query": query,
            "size": size,
            "sort": [
                {"walkability_score": {"order": "desc"}},
                {"school_rating": {"order": "desc"}}
            ]
        }
    
    @staticmethod
    def stats_aggregation() -> Dict[str, Any]:
        """
        Build neighborhood statistics aggregation query.
        
        Returns:
            Elasticsearch query dictionary with neighborhood statistics
        """
        return {
            "size": 0,  # Only aggregations
            "aggs": {
                "by_city": {
                    "terms": {
                        "field": "city.keyword",
                        "size": 20
                    },
                    "aggs": {
                        "avg_walkability": {
                            "avg": {"field": "walkability_score"}
                        },
                        "avg_school_rating": {
                            "avg": {"field": "school_rating"}
                        },
                        "avg_crime_rating": {
                            "avg": {"field": "crime_rating"}
                        },
                        "area_types": {
                            "terms": {
                                "field": "area_type",
                                "size": 10
                            }
                        }
                    }
                },
                "walkability_stats": {
                    "stats": {"field": "walkability_score"}
                },
                "school_rating_stats": {
                    "stats": {"field": "school_rating"}
                },
                "crime_rating_stats": {
                    "stats": {"field": "crime_rating"}
                }
            }
        }