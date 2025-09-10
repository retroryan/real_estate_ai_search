"""
Hybrid search demo runner base class.

Provides common patterns for hybrid search demos combining
vector and text search with RRF (Reciprocal Rank Fusion).
"""

from typing import Dict, Any, Optional, List, Tuple
from elasticsearch import Elasticsearch

from .base_demo_runner import BaseDemoRunner
from .property.models import PropertySearchResult
from ..models import PropertyListing
from .demo_config import demo_config
from ..hybrid import HybridSearchEngine, HybridSearchParams


class HybridDemoBase(BaseDemoRunner[PropertySearchResult]):
    """
    Base class for hybrid search demos.
    
    Manages hybrid search engine initialization and provides
    RRF-specific search patterns.
    """
    
    def __init__(self, es_client: Elasticsearch):
        """
        Initialize hybrid demo runner.
        
        Args:
            es_client: Elasticsearch client
        """
        super().__init__(es_client)
        self.hybrid_engine = HybridSearchEngine(es_client)
    
    def create_error_result(
        self,
        demo_name: str,
        error_message: str,
        execution_time_ms: float,
        query_dsl: Dict[str, Any],
        **kwargs
    ) -> PropertySearchResult:
        """Create a hybrid search error result."""
        return PropertySearchResult(
            query_name=demo_name,
            query_description=f"Error occurred: {error_message}",
            execution_time_ms=int(execution_time_ms),
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=query_dsl,
            es_features=["Error occurred during hybrid search"],
            indexes_used=[demo_config.indexes.properties_index]
        )
    
    def execute_hybrid_search(
        self,
        query: str,
        size: int = 10,
        rank_constant: int = 60,
        rank_window_size: int = 100,
        **kwargs
    ) -> PropertySearchResult:
        """
        Execute a hybrid search combining vector and text search.
        
        Args:
            query: Natural language query
            size: Number of results to return
            rank_constant: RRF rank constant parameter
            rank_window_size: RRF window size parameter
            **kwargs: Additional arguments for result processing
            
        Returns:
            PropertySearchResult with hybrid search results
        """
        query_name = kwargs.get('query_name', f"Hybrid Search: '{query}'")
        query_description = kwargs.get('query_description', 
                                     f"Hybrid search combining semantic and text search for: '{query}'")
        
        # Configure search parameters
        params = HybridSearchParams(
            query_text=query,
            size=size,
            rank_constant=rank_constant,
            rank_window_size=rank_window_size
        )
        
        try:
            # Execute hybrid search
            result = self.hybrid_engine.search(params)
            
            # Extract PropertyListing objects
            property_results = [sr.property_data for sr in result.results]
            
            # Build query DSL for display
            query_dsl = {
                "retriever": {
                    "rrf": {
                        "retrievers": ["text_search", "vector_search"],
                        "rank_constant": rank_constant,
                        "rank_window_size": rank_window_size
                    }
                },
                "query": query,
                "size": size
            }
            
            # Build ES features list
            es_features = kwargs.get('es_features', [
                f"RRF (Reciprocal Rank Fusion) - rank_constant={rank_constant}",
                "Retriever Syntax - Modern Elasticsearch 8.16+ architecture",
                "Multi-Match Text Search - BM25 scoring with field boosting",
                "KNN Vector Search - 1024-dimensional semantic embeddings",
                "Hybrid Scoring - Combines text relevance with semantic similarity",
                f"Query executed in {result.execution_time_ms}ms"
            ])
            
            return PropertySearchResult(
                query_name=query_name,
                query_description=query_description,
                execution_time_ms=result.execution_time_ms,
                total_hits=result.total_hits,
                returned_hits=len(property_results),
                results=property_results,
                query_dsl=query_dsl,
                es_features=es_features,
                indexes_used=[
                    demo_config.indexes.properties_index,
                    f"Hybrid search for: '{query}'"
                ]
            )
            
        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}")
            return self.create_error_result(
                demo_name=query_name,
                error_message=f"Hybrid search failed: {str(e)}",
                execution_time_ms=0,
                query_dsl=query_dsl if 'query_dsl' in locals() else {}
            )
    
    def configure_rrf_params(
        self,
        rank_constant: Optional[int] = None,
        rank_window_size: Optional[int] = None
    ) -> Tuple[int, int]:
        """
        Configure RRF parameters with defaults.
        
        Args:
            rank_constant: RRF rank constant (uses config default if None)
            rank_window_size: RRF window size (uses config default if None)
            
        Returns:
            Tuple of (rank_constant, rank_window_size)
        """
        # Use defaults from config
        if rank_constant is None:
            rank_constant = demo_config.hybrid_defaults.rank_constant
        if rank_window_size is None:
            rank_window_size = demo_config.hybrid_defaults.rank_window_size
        
        return rank_constant, rank_window_size