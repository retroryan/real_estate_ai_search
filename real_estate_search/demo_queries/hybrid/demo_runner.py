"""
Demo runner for hybrid search functionality.

Orchestrates hybrid search demonstrations combining vector and text search
with RRF (Reciprocal Rank Fusion).
"""

from typing import Optional
from elasticsearch import Elasticsearch

from ..hybrid_demo_base import HybridDemoBase
from ..property.models import PropertySearchResult
from ..demo_config import demo_config
from .query_builder import HybridQueryBuilder


class HybridDemoRunner(HybridDemoBase):
    """
    Orchestrates hybrid search demos using base class patterns.
    """
    
    def __init__(self, es_client: Elasticsearch):
        """Initialize hybrid demo runner."""
        super().__init__(es_client)
        self.query_builder = HybridQueryBuilder()
    
    def run_hybrid_search(
        self,
        query: Optional[str] = None,
        size: Optional[int] = None,
        rank_constant: Optional[int] = None,
        rank_window_size: Optional[int] = None
    ) -> PropertySearchResult:
        """
        Run hybrid search combining vector and text search with RRF.
        
        Args:
            query: Natural language search query (uses default if None)
            size: Number of results (uses default if None)
            rank_constant: RRF rank constant (uses default if None)
            rank_window_size: RRF window size (uses default if None)
            
        Returns:
            PropertySearchResult with hybrid search results
        """
        # Use defaults from config
        query = query or demo_config.hybrid_defaults.default_query
        size = size or demo_config.hybrid_defaults.default_size
        
        # Configure RRF parameters
        rank_constant, rank_window_size = self.configure_rrf_params(
            rank_constant, rank_window_size
        )
        
        # Execute using base class pattern
        return self.execute_hybrid_search(
            query=query,
            size=size,
            rank_constant=rank_constant,
            rank_window_size=rank_window_size,
            query_name=f"Hybrid Search: '{query}'",
            query_description=self._build_query_description(query),
            es_features=self._get_es_features(rank_constant)
        )
    
    def _build_query_description(self, query: str) -> str:
        """Build query description for display."""
        return (
            f"Combines semantic vector search with text search using RRF "
            f"for query: '{query}'"
        )
    
    def _get_es_features(self, rank_constant: int) -> list:
        """Get Elasticsearch features list for display."""
        return [
            "RRF (Reciprocal Rank Fusion) - Native Elasticsearch fusion algorithm",
            "Retriever Syntax - Modern Elasticsearch 8.16+ retriever architecture",
            "Multi-Match Text Search - BM25 scoring with field boosting",
            "KNN Vector Search - 1024-dimensional semantic embeddings",
            "Hybrid Scoring - Combines text relevance with semantic similarity",
            f"RRF Configuration - rank_constant={rank_constant}"
        ]