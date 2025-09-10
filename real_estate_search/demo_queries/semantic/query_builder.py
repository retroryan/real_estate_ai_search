"""
Query construction for semantic and keyword search.

Builds Elasticsearch queries for KNN and keyword-based searches.
"""

from typing import Dict, Any, List, Optional
import logging

from .constants import (
    DEFAULT_SIZE,
    KNN_NUM_CANDIDATES_MULTIPLIER,
    PROPERTY_FIELDS
)


logger = logging.getLogger(__name__)


class SemanticQueryBuilder:
    """Builder for semantic search queries."""
    
    @staticmethod
    def build_knn_query(
        query_vector: List[float], 
        size: int = DEFAULT_SIZE,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Build a KNN query for semantic search.
        
        Args:
            query_vector: The embedding vector for the query
            size: Number of results to return
            fields: Fields to retrieve (defaults to PROPERTY_FIELDS)
            
        Returns:
            Elasticsearch query dictionary
        """
        if fields is None:
            fields = PROPERTY_FIELDS
            
        query = {
            "knn": {
                "field": "embedding",
                "query_vector": query_vector,
                "k": size,
                "num_candidates": min(100, size * KNN_NUM_CANDIDATES_MULTIPLIER)
            },
            "size": size,
            "_source": fields
        }
        
        logger.debug(f"Built KNN query for {size} results with {len(query_vector)}-dim vector")
        return query
    
    @staticmethod
    def build_keyword_query(
        query_text: str,
        size: int = DEFAULT_SIZE,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Build a keyword-based multi-match query.
        
        Args:
            query_text: The text query
            size: Number of results to return
            fields: Fields to retrieve (defaults to PROPERTY_FIELDS)
            
        Returns:
            Elasticsearch query dictionary
        """
        if fields is None:
            fields = PROPERTY_FIELDS
            
        query = {
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": [
                        "description^2",
                        "features^1.5",
                        "amenities^1.5",
                        "address.city",
                        "address.neighborhood"
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