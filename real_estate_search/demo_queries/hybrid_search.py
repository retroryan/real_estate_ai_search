"""
Demo for hybrid search functionality.
"""

import logging
from typing import Dict, Any
from elasticsearch import Elasticsearch

from ..models.results.hybrid import HybridSearchResult
from ..hybrid import HybridSearchEngine, HybridSearchParams

logger = logging.getLogger(__name__)


def demo_hybrid_search(
    es_client: Elasticsearch,
    query: str = "modern kitchen with stainless steel appliances",
    size: int = 10
) -> HybridSearchResult:
    """
    Demo: Hybrid search combining vector and text search with RRF.
    
    Demonstrates Elasticsearch's native RRF to combine semantic understanding
    with keyword precision for superior search results.
    
    Args:
        es_client: Elasticsearch client
        query: Natural language search query
        size: Number of results to return
        
    Returns:
        HybridSearchResult with hybrid search results
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
        
        # Convert to BaseQueryResult format
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
        
        return HybridSearchResult(
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
            ]
        )
        
    except Exception as e:
        logger.error(f"Hybrid search demo failed: {e}")
        raise