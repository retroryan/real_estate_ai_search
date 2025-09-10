"""
Semantic-specific demo runner base class.

Provides common patterns for semantic search demos including
embedding service management and semantic-specific error handling.
"""

from typing import Dict, Any, Optional, List, Tuple
from elasticsearch import Elasticsearch
import time

from .base_demo_runner import BaseDemoRunner
from .property.models import PropertySearchResult
from ..models import PropertyListing
from .demo_config import demo_config
from ..config import AppConfig
from ..embeddings.exceptions import (
    EmbeddingServiceError,
    EmbeddingGenerationError,
    ConfigurationError
)
from .semantic.embedding_service import get_embedding_service


class SemanticDemoBase(BaseDemoRunner[PropertySearchResult]):
    """
    Base class for semantic search demos.
    
    Handles embedding service lifecycle management and provides
    semantic-specific search patterns.
    """
    
    def __init__(self, es_client: Elasticsearch, config: Optional[AppConfig] = None):
        """
        Initialize semantic demo runner.
        
        Args:
            es_client: Elasticsearch client
            config: Application configuration for embedding service
        """
        super().__init__(es_client)
        self.config = config
    
    def create_error_result(
        self,
        demo_name: str,
        error_message: str,
        execution_time_ms: float,
        query_dsl: Dict[str, Any],
        **kwargs
    ) -> PropertySearchResult:
        """Create a semantic search error result."""
        return PropertySearchResult(
            query_name=demo_name,
            query_description=f"Error occurred: {error_message}",
            execution_time_ms=int(execution_time_ms),
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=query_dsl,
            es_features=["Error occurred during semantic search"],
            indexes_used=[demo_config.indexes.properties_index]
        )
    
    def generate_embedding(self, query: str) -> Tuple[List[float], float]:
        """
        Generate embedding for a query.
        
        Args:
            query: Natural language query text
            
        Returns:
            Tuple of (embedding vector, generation time in ms)
            
        Raises:
            EmbeddingServiceError: If embedding generation fails
        """
        try:
            with get_embedding_service(self.config) as embedding_service:
                return embedding_service.generate_query_embedding(query)
        except (ConfigurationError, EmbeddingServiceError, EmbeddingGenerationError) as e:
            self.logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingServiceError(f"Embedding generation failed: {str(e)}")
    
    def execute_semantic_search(
        self,
        query: str,
        query_builder_func,
        size: int = 10,
        **kwargs
    ) -> PropertySearchResult:
        """
        Execute a semantic search with embedding generation.
        
        Args:
            query: Natural language query
            query_builder_func: Function that builds ES query from embedding
            size: Number of results to return
            **kwargs: Additional arguments for result processing
            
        Returns:
            PropertySearchResult with semantic search results
        """
        query_name = kwargs.pop('query_name', f"Semantic Search: '{query}'")
        query_description = kwargs.pop('query_description', f"Semantic search for: '{query}'")
        
        try:
            # Generate embedding and build query
            query_embedding, embedding_time_ms = self.generate_embedding(query)
            query_dsl = query_builder_func(query_embedding, size)
            
            # Process the search with embedding timing
            return self._process_semantic_response(
                query_dsl=query_dsl,
                query_name=query_name,
                query_description=query_description,
                query=query,
                embedding_time_ms=embedding_time_ms,
                **kwargs
            )
            
        except EmbeddingServiceError as e:
            return self.create_error_result(
                demo_name=query_name,
                error_message=str(e),
                execution_time_ms=0,
                query_dsl={}
            )
    
    def _process_semantic_response(
        self,
        query_dsl: Dict[str, Any],
        query_name: str,
        query_description: str,
        query: str,
        embedding_time_ms: float,
        **kwargs
    ) -> PropertySearchResult:
        """Process semantic search response."""
        start_time = time.time()
        
        try:
            # Execute search
            response = self.es_client.search(
                index=demo_config.indexes.properties_index,
                body=query_dsl
            )
            
            # Process response
            search_time_ms = self.safe_get_execution_time(response)
            total_time_ms = embedding_time_ms + search_time_ms
            hits, total_count = self.safe_extract_hits(response)
            
            # Convert to property listings
            property_results = self._convert_hits_to_properties(hits)
            
            # Build result with timing breakdown
            return self._build_semantic_result(
                query_name=query_name,
                query_description=query_description,
                total_time_ms=total_time_ms,
                total_count=total_count,
                property_results=property_results,
                query_dsl=query_dsl,
                query=query,
                embedding_time_ms=embedding_time_ms,
                search_time_ms=search_time_ms,
                **kwargs
            )
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Semantic search failed: {e}")
            return self.create_error_result(
                demo_name=query_name,
                error_message=f"Search failed: {str(e)}",
                execution_time_ms=execution_time_ms,
                query_dsl=query_dsl
            )
    
    def _convert_hits_to_properties(self, hits: List[Dict[str, Any]]) -> List[PropertyListing]:
        """Convert Elasticsearch hits to PropertyListing objects."""
        property_results = []
        for hit in hits:
            try:
                prop = PropertyListing.from_elasticsearch(hit['_source'])
                property_results.append(prop)
            except Exception as e:
                self.logger.warning(f"Failed to convert property: {e}")
        return property_results
    
    def _build_semantic_result(
        self,
        query_name: str,
        query_description: str,
        total_time_ms: float,
        total_count: int,
        property_results: List[PropertyListing],
        query_dsl: Dict[str, Any],
        query: str,
        embedding_time_ms: float,
        search_time_ms: float,
        **kwargs
    ) -> PropertySearchResult:
        """Build semantic search result."""
        return PropertySearchResult(
            query_name=query_name,
            query_description=query_description,
            execution_time_ms=int(total_time_ms),
            total_hits=total_count,
            returned_hits=len(property_results),
            results=property_results,
            query_dsl=query_dsl,
            es_features=kwargs.get('es_features', [
                f"Query Embedding Generation - {embedding_time_ms:.1f}ms",
                f"KNN Search - {search_time_ms:.1f}ms",
                "Dense Vectors - 1024-dimensional embeddings",
                "Cosine Similarity - Vector distance metric"
            ]),
            indexes_used=[
                demo_config.indexes.properties_index,
                f"Semantic search for: '{query}'"
            ],
            aggregations=kwargs.get('aggregations', {
                "timing_breakdown": {
                    "embedding_generation_ms": embedding_time_ms,
                    "elasticsearch_search_ms": search_time_ms,
                    "total_ms": total_time_ms
                }
            })
        )
