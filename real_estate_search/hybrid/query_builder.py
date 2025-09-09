"""
Query builder module for constructing Elasticsearch queries.

Responsible for building complex Elasticsearch queries including RRF,
text search, vector search, and filter construction.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .models import HybridSearchParams, LocationIntent
from .location import LocationFilterBuilder

logger = logging.getLogger(__name__)


class QueryComponents(BaseModel):
    """Components that make up an Elasticsearch query."""
    text_query: Dict[str, Any] = Field(..., description="Text search query component")
    vector_config: Dict[str, Any] = Field(..., description="Vector search configuration")
    filters: List[Dict[str, Any]] = Field(default_factory=list, description="Filter clauses")
    size: int = Field(..., description="Number of results to return")


class RRFQueryBuilder:
    """
    Builds Elasticsearch queries using Reciprocal Rank Fusion (RRF).
    
    This builder constructs optimized queries that:
    - Apply filters during search (not post-filtering) for performance
    - Use native Elasticsearch RRF for result fusion
    - Support both text and vector search strategies
    """
    
    def __init__(self):
        """Initialize the RRF query builder."""
        self.filter_builder = LocationFilterBuilder()
        logger.debug("Initialized RRFQueryBuilder")
    
    def build_query(
        self,
        params: HybridSearchParams,
        query_vector: List[float],
        query_text: str
    ) -> Dict[str, Any]:
        """
        Build complete RRF query for Elasticsearch.
        
        Args:
            params: Search parameters including optional location intent
            query_vector: Generated query embedding vector
            query_text: Text to use for search (cleaned if location extracted)
            
        Returns:
            Complete Elasticsearch query dictionary
        """
        # Build query components
        components = self._build_components(params, query_vector, query_text)
        
        # Construct final RRF query
        query = self._construct_rrf_query(params, components)
        
        logger.debug(f"Built RRF query with {len(components.filters)} filters")
        return query
    
    def _build_components(
        self,
        params: HybridSearchParams,
        query_vector: List[float],
        query_text: str
    ) -> QueryComponents:
        """
        Build individual query components.
        
        Args:
            params: Search parameters
            query_vector: Query embedding vector
            query_text: Search text
            
        Returns:
            QueryComponents with all necessary parts
        """
        # Build location filters
        filters = self._build_filters(params.location_intent)
        
        # Build text query
        text_query = self._build_text_query(query_text, params.text_boost, filters)
        
        # Build vector configuration
        vector_config = self._build_vector_config(
            query_vector,
            params.size,
            filters
        )
        
        return QueryComponents(
            text_query=text_query,
            vector_config=vector_config,
            filters=filters,
            size=params.size
        )
    
    def _build_filters(self, location_intent: Optional[LocationIntent]) -> List[Dict[str, Any]]:
        """
        Build filter clauses from location intent.
        
        Args:
            location_intent: Extracted location information
            
        Returns:
            List of Elasticsearch filter clauses
        """
        if not location_intent or not location_intent.has_location:
            return []
        
        filters = self.filter_builder.build_filters(location_intent)
        logger.info(f"Built {len(filters)} location filters")
        return filters
    
    def _build_text_query(
        self,
        query_text: str,
        text_boost: float,
        filters: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build text search query with optional filters.
        
        Args:
            query_text: Search text
            text_boost: Boost factor for text fields
            filters: Filter clauses to apply
            
        Returns:
            Text query dictionary
        """
        # Base multi-match query
        base_query = {
            "multi_match": {
                "query": query_text,
                "fields": [
                    f"description^{2.0 * text_boost}",
                    f"features^{1.5 * text_boost}",
                    f"amenities^{1.5 * text_boost}",
                    "address.street",
                    "address.city",
                    "neighborhood.name"
                ],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        }
        
        # Wrap with filters if present
        if filters:
            return {
                "bool": {
                    "must": base_query,
                    "filter": filters
                }
            }
        
        return base_query
    
    def _build_vector_config(
        self,
        query_vector: List[float],
        size: int,
        filters: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build vector search configuration.
        
        Args:
            query_vector: Query embedding vector
            size: Number of results
            filters: Filter clauses to apply
            
        Returns:
            Vector search configuration dictionary
        """
        config = {
            "field": "embedding",
            "query_vector": query_vector,
            "k": min(size * 5, 100),
            "num_candidates": min(size * 10, 200)
        }
        
        # Add filters for efficient filtering during kNN search
        if filters:
            config["filter"] = filters
        
        return config
    
    def _construct_rrf_query(
        self,
        params: HybridSearchParams,
        components: QueryComponents
    ) -> Dict[str, Any]:
        """
        Construct final RRF query from components.
        
        Args:
            params: Search parameters
            components: Query components
            
        Returns:
            Complete Elasticsearch query
        """
        return {
            "retriever": {
                "rrf": {
                    "retrievers": [
                        {
                            "standard": {
                                "query": components.text_query
                            }
                        },
                        {
                            "knn": components.vector_config
                        }
                    ],
                    "rank_constant": params.rank_constant,
                    "rank_window_size": params.rank_window_size
                }
            },
            "size": components.size,
            "_source": self._get_source_fields()
        }
    
    def _get_source_fields(self) -> List[str]:
        """
        Get fields to include in search results.
        
        Returns:
            List of field names to retrieve
        """
        return [
            "listing_id",
            "property_type",
            "price",
            "bedrooms",
            "bathrooms",
            "square_feet",
            "address",
            "description",
            "features",
            "neighborhood"
        ]