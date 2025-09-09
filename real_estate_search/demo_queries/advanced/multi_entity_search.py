"""
Multi-entity cross-index search module.

This module provides search capabilities across multiple indices
(properties, neighborhoods, Wikipedia) with unified ranking and
entity type discrimination.
"""

from typing import Dict, Any, List
import logging

from .models import MultiIndexSearchRequest, EntityDiscriminationResult

logger = logging.getLogger(__name__)


class MultiEntitySearchBuilder:
    """Builds multi-index search queries across different entity types."""
    
    def build_multi_index_search(
        self,
        query_text: str,
        size_per_type: int = 5
    ) -> MultiIndexSearchRequest:
        """
        Build a multi-index search query.
        
        Args:
            query_text: The search query text
            size_per_type: Number of results per entity type
            
        Returns:
            MultiIndexSearchRequest for cross-index search
        """
        query = {
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": [
                        # Property fields
                        "description^2",
                        "features^1.5",
                        "amenities",
                        "address.city",
                        "neighborhood_name",
                        
                        # Neighborhood fields
                        "name^3",
                        "demographics.description",
                        
                        # Wikipedia fields
                        "title^3",
                        "summary^2",
                        "content",
                        "categories"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "size": size_per_type * 3,  # Get more since we're searching multiple indices
            "_source": {
                "includes": ["*"]
            },
            "highlight": {
                "fields": {
                    "*": {}
                },
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"]
            }
        }
        
        aggregations = {
            "by_index": {
                "terms": {
                    "field": "_index",
                    "size": 10
                }
            }
        }
        
        return MultiIndexSearchRequest(
            query=query,
            indices=["properties", "neighborhoods", "wikipedia"],
            size=size_per_type * 3,
            aggregations=aggregations,
            highlight={
                "fields": {"*": {}},
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"]
            }
        )
    
    def build_entity_aggregation(self) -> Dict[str, Any]:
        """
        Build aggregation for entity type counting.
        
        Returns:
            Aggregation configuration for index counting
        """
        return {
            "by_index": {
                "terms": {
                    "field": "_index",
                    "size": 10
                }
            }
        }
    
    def get_field_boost_config(self) -> Dict[str, float]:
        """
        Get field boost configuration for multi-index search.
        
        Returns:
            Dictionary of field patterns and their boost values
        """
        return {
            # Property fields
            "description": 2.0,
            "features": 1.5,
            "amenities": 1.0,
            "address.city": 1.0,
            "neighborhood_name": 1.0,
            
            # Neighborhood fields
            "name": 3.0,
            "demographics.description": 1.0,
            
            # Wikipedia fields
            "title": 3.0,
            "summary": 2.0,
            "content": 1.0,
            "categories": 1.0
        }