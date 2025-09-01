"""
Hybrid search implementation combining vector and text search with RRF.

This module provides location-aware hybrid search capabilities using Elasticsearch's
native Reciprocal Rank Fusion (RRF) to combine semantic vector search with traditional
text search for superior relevance.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from elasticsearch import Elasticsearch
from pydantic import BaseModel, Field

from .models import DemoQueryResult
from .location_understanding import LocationIntent, LocationUnderstandingModule, LocationFilterBuilder
from ..embeddings import QueryEmbeddingService
from ..config import AppConfig

logger = logging.getLogger(__name__)


class HybridSearchParams(BaseModel):
    """Parameters for hybrid search queries."""
    query_text: str = Field(..., description="Natural language search query")
    size: int = Field(10, description="Number of results to return")
    rank_constant: int = Field(60, description="RRF rank constant (k parameter)")
    rank_window_size: int = Field(100, description="RRF window size for ranking")
    text_boost: float = Field(1.0, description="Boost factor for text search")
    vector_boost: float = Field(1.0, description="Boost factor for vector search")
    location_intent: Optional[LocationIntent] = Field(None, description="Extracted location information")




class SearchResult(BaseModel):
    """Individual search result with hybrid scoring."""
    listing_id: str = Field(..., description="Property listing ID")
    hybrid_score: float = Field(..., description="Combined RRF score")
    text_score: Optional[float] = Field(None, description="Text search score")
    vector_score: Optional[float] = Field(None, description="Vector search score")
    property_data: Dict[str, Any] = Field(..., description="Property information")


class HybridSearchResult(BaseModel):
    """Complete hybrid search result."""
    query: str = Field(..., description="Original query text")
    total_hits: int = Field(..., description="Total matching documents")
    execution_time_ms: int = Field(..., description="Query execution time")
    results: List[SearchResult] = Field(..., description="Search results")
    search_metadata: Dict[str, Any] = Field(..., description="Search execution metadata")


class HybridSearchEngine:
    """
    Hybrid search engine combining vector and text search with RRF.
    
    Uses Elasticsearch's native RRF implementation following 2024 best practices
    with retriever syntax for optimal performance and accuracy. Integrates location
    understanding for geographic filtering.
    """
    
    def __init__(self, es_client: Elasticsearch, config: Optional[AppConfig] = None):
        """
        Initialize the hybrid search engine.
        
        Args:
            es_client: Elasticsearch client instance
            config: Application configuration (loads default if None)
        """
        self.es_client = es_client
        self.config = config or AppConfig.load()
        self.embedding_service = QueryEmbeddingService(config=self.config.embedding)
        self.location_module = LocationUnderstandingModule()
        self.filter_builder = LocationFilterBuilder()
        logger.info("Initialized HybridSearchEngine with RRF and location support")
    
    def search(self, params: HybridSearchParams) -> HybridSearchResult:
        """
        Execute hybrid search with RRF fusion and optional location filtering.
        
        Args:
            params: Search parameters with optional location intent
            
        Returns:
            HybridSearchResult with ranked results
        """
        start_time = time.time()
        logger.info(f"Starting hybrid search for query: '{params.query_text}'")
        
        # Use cleaned query if location intent is provided, otherwise use original
        query_for_search = params.query_text
        if params.location_intent and params.location_intent.has_location:
            query_for_search = params.location_intent.cleaned_query
            logger.info(f"Using cleaned query: '{query_for_search}' with location filters")
        
        # Generate query embedding
        self.embedding_service.initialize()
        try:
            query_vector = self.embedding_service.embed_query(query_for_search)
            logger.debug(f"Generated embedding vector of dimension {len(query_vector)}")
        finally:
            self.embedding_service.close()
        
        # Build RRF query using native Elasticsearch syntax
        query_body = self._build_rrf_query(params, query_vector, query_for_search)
        
        # Execute search
        try:
            response = self.es_client.search(
                index="properties",
                body=query_body
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            logger.info(f"Hybrid search completed in {execution_time}ms")
            
            # Process results
            return self._process_results(params.query_text, response, execution_time)
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise
    
    def search_with_location(self, query: str, size: int = 10) -> HybridSearchResult:
        """
        Execute location-aware hybrid search.
        
        Extracts location from the query and applies geographic filters
        along with hybrid text and vector search.
        
        Args:
            query: Natural language search query
            size: Number of results to return
            
        Returns:
            HybridSearchResult with location-filtered results
        """
        logger.info(f"Starting location-aware search for: '{query}'")
        
        # Extract location intent
        location_intent = self.location_module(query)
        
        # Log extracted location information
        if location_intent.has_location:
            logger.info(f"Location extracted - City: {location_intent.city}, "
                       f"State: {location_intent.state}, Confidence: {location_intent.confidence}")
        else:
            logger.info("No location detected in query")
        
        # Create search parameters with location intent
        params = HybridSearchParams(
            query_text=query,
            size=size,
            location_intent=location_intent
        )
        
        # Execute search with location filters
        return self.search(params)
    
    def _build_rrf_query(self, params: HybridSearchParams, query_vector: List[float], query_text: str) -> Dict[str, Any]:
        """
        Build RRF query using Elasticsearch retriever syntax with location filters.
        
        Args:
            params: Search parameters including optional location intent
            query_vector: Generated query embedding
            query_text: Text to use for search (cleaned if location was extracted)
            
        Returns:
            Elasticsearch query dictionary ready for execution
        """
        # Build location filters if location intent exists
        location_filters = []
        if params.location_intent and params.location_intent.has_location:
            location_filters = self.filter_builder.build_filters(params.location_intent)
            logger.debug(f"Applied {len(location_filters)} location filters")
        
        # Build text search query directly
        text_query = {
            "multi_match": {
                "query": query_text,
                "fields": [
                    f"description^{2.0 * params.text_boost}",
                    f"features^{1.5 * params.text_boost}",
                    f"amenities^{1.5 * params.text_boost}",
                    "address.street",
                    "address.city",
                    "neighborhood.name"
                ],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        }
        
        # Wrap with filters if they exist
        if location_filters:
            text_query = {
                "bool": {
                    "must": text_query,
                    "filter": location_filters
                }
            }
        
        # Build vector search configuration directly
        vector_config = {
            "field": "embedding",
            "query_vector": query_vector,
            "k": min(params.size * 5, 100),
            "num_candidates": min(params.size * 10, 200)
        }
        
        # Add filters to vector search if they exist
        if location_filters:
            vector_config["filter"] = location_filters
        
        # Build complete Elasticsearch query with native RRF
        return {
            "retriever": {
                "rrf": {
                    "retrievers": [
                        {
                            "standard": {
                                "query": text_query
                            }
                        },
                        {
                            "knn": vector_config
                        }
                    ],
                    "rank_constant": params.rank_constant,
                    "rank_window_size": params.rank_window_size
                }
            },
            "size": params.size,
            "_source": [
                "listing_id", "property_type", "price", "bedrooms", "bathrooms",
                "square_feet", "address", "description", "features", "amenities",
                "neighborhood"
            ]
        }
    
    def _process_results(
        self, 
        query: str, 
        response: Dict[str, Any], 
        execution_time: int
    ) -> HybridSearchResult:
        """
        Process Elasticsearch response into structured results.
        
        Args:
            query: Original query text
            response: Elasticsearch response
            execution_time: Query execution time in ms
            
        Returns:
            Processed hybrid search results
        """
        results = []
        
        for hit in response['hits']['hits']:
            result = SearchResult(
                listing_id=hit['_source']['listing_id'],
                hybrid_score=hit['_score'],
                text_score=None,  # RRF combines scores automatically
                vector_score=None,  # Individual scores not available in RRF
                property_data=hit['_source']
            )
            results.append(result)
        
        search_metadata = {
            "rrf_used": True,
            "rank_constant": 60,  # Default from query
            "total_retrievers": 2,
            "elasticsearch_took": response.get('took', 0)
        }
        
        return HybridSearchResult(
            query=query,
            total_hits=response['hits']['total']['value'],
            execution_time_ms=execution_time,
            results=results,
            search_metadata=search_metadata
        )


def demo_hybrid_search(
    es_client: Elasticsearch,
    query: str = "modern kitchen with stainless steel appliances",
    size: int = 10
) -> DemoQueryResult:
    """
    Demo: Hybrid search combining vector and text search with RRF.
    
    Demonstrates Elasticsearch's native RRF to combine semantic understanding
    with keyword precision for superior search results.
    
    Args:
        es_client: Elasticsearch client
        query: Natural language search query
        size: Number of results to return
        
    Returns:
        DemoQueryResult with hybrid search results
    """
    logger.info(f"Running hybrid search demo for query: '{query}'")
    
    # Initialize hybrid search engine
    engine = HybridSearchEngine(es_client)
    
    # Configure search parameters
    params = HybridSearchParams(
        query_text=query,
        size=size,
        rank_constant=60,
        rank_window_size=100
    )
    
    # Execute search
    try:
        result = engine.search(params)
        
        # Convert to DemoQueryResult format
        demo_results = []
        for search_result in result.results:
            demo_result = search_result.property_data.copy()
            demo_result['_hybrid_score'] = search_result.hybrid_score
            demo_results.append(demo_result)
        
        # Build query DSL for display
        query_dsl = {
            "retriever": {
                "rrf": {
                    "retrievers": ["text_search", "vector_search"],
                    "rank_constant": params.rank_constant,
                    "rank_window_size": params.rank_window_size
                }
            }
        }
        
        return DemoQueryResult(
            query_name=f"Hybrid Search: '{query}'",
            query_description=f"Combines semantic vector search with text search using RRF for query: '{query}'",
            execution_time_ms=result.execution_time_ms,
            total_hits=result.total_hits,
            returned_hits=len(demo_results),
            results=demo_results,
            query_dsl=query_dsl,
            es_features=[
                "RRF (Reciprocal Rank Fusion) - Native Elasticsearch fusion algorithm",
                "Retriever Syntax - Modern Elasticsearch 8.16+ retriever architecture",
                "Multi-Match Text Search - BM25 scoring with field boosting",
                "KNN Vector Search - 1024-dimensional semantic embeddings",
                "Hybrid Scoring - Combines text relevance with semantic similarity",
                f"Query executed in {result.execution_time_ms}ms with RRF rank_constant=60"
            ],
            indexes_used=[
                "properties index - Real estate listings with embeddings and text fields",
                f"RRF fusion of 2 retrievers for comprehensive search coverage"
            ]
        )
        
    except Exception as e:
        logger.error(f"Hybrid search demo failed: {e}")
        raise