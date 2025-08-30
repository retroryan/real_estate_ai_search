"""Natural language semantic search service for MCP server."""

import time
import logging
from typing import Dict, Any, List, Optional

from ..models.search import (
    NaturalLanguageSearchRequest,
    NaturalLanguageSearchResponse,
    SemanticComparisonResponse
)
from ..settings import MCPServerConfig
from .elasticsearch_client import ElasticsearchClient
from ...embeddings import QueryEmbeddingService
from ..utils.logging import get_logger

logger = get_logger(__name__)


class NaturalLanguageSearchService:
    """Service for natural language semantic search operations."""

    def __init__(
        self,
        config: MCPServerConfig,
        es_client: ElasticsearchClient,
        embedding_service: QueryEmbeddingService
    ):
        """Initialize natural language search service.
        
        Args:
            config: Server configuration
            es_client: Elasticsearch client
            embedding_service: Query embedding service
        """
        self.config = config
        self.es_client = es_client
        self.embedding_service = embedding_service
        self.index_name = config.elasticsearch.property_index

    async def semantic_search(
        self, 
        query: str, 
        size: int = 10
    ) -> NaturalLanguageSearchResponse:
        """Perform pure semantic search using embeddings.
        
        Args:
            query: Natural language query
            size: Number of results to return
            
        Returns:
            Natural language search response
        """
        start_time = time.time()
        logger.info(f"Performing semantic search: {query}")

        try:
            # Generate query embedding
            query_embedding = self.embedding_service.embed_query(query)
            embedding_time = (time.time() - start_time) * 1000

            # Build KNN query
            es_query = {
                "knn": {
                    "field": "embedding",
                    "query_vector": query_embedding,
                    "k": size,
                    "num_candidates": min(100, size * 10)
                },
                "size": size,
                "_source": [
                    "listing_id", "property_type", "price", "bedrooms", "bathrooms",
                    "square_feet", "address", "description", "features", "amenities"
                ]
            }

            # Execute search
            search_start = time.time()
            response = self.es_client.search(index=self.index_name, body=es_query)
            search_time = (time.time() - search_start) * 1000

            # Process results
            results = []
            for hit in response['hits']['hits']:
                result = hit['_source']
                result['_score'] = hit['_score']
                result['_similarity_score'] = hit['_score']
                results.append(result)

            total_time = embedding_time + search_time

            return NaturalLanguageSearchResponse(
                query_name=f"Semantic Search: '{query[:50]}...'",
                query_description=f"Pure semantic search using AI embeddings for: '{query}'",
                execution_time_ms=int(total_time),
                total_hits=response['hits']['total']['value'],
                returned_hits=len(results),
                results=results,
                search_features=[
                    f"Query Embedding Generation: {embedding_time:.1f}ms",
                    f"Vector Similarity Search: {search_time:.1f}ms",
                    f"Using {len(query_embedding)}-dimensional embeddings",
                    "Cosine similarity ranking for semantic understanding",
                    "Pure AI-based semantic matching (no keyword matching)"
                ],
                original_query=query
            )

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return NaturalLanguageSearchResponse(
                query_name=f"Semantic Search Failed: '{query[:50]}...'",
                query_description="Semantic search encountered an error",
                execution_time_ms=int((time.time() - start_time) * 1000),
                total_hits=0,
                returned_hits=0,
                results=[],
                search_features=[f"Error: {str(e)}"],
                original_query=query
            )

    async def natural_language_examples(self) -> NaturalLanguageSearchResponse:
        """Run multiple natural language search examples.
        
        Returns:
            Aggregated results from multiple example queries
        """
        example_queries = [
            "cozy family home near good schools and parks",
            "modern downtown condo with city views", 
            "spacious property with home office and fast internet",
            "eco-friendly house with solar panels and energy efficiency",
            "luxury estate with pool and entertainment areas"
        ]

        all_results = []
        total_time = 0
        total_hits_all = 0
        start_time = time.time()

        try:
            for i, query in enumerate(example_queries, 1):
                query_start = time.time()
                
                # Generate embedding
                query_embedding = self.embedding_service.embed_query(query)
                
                # Build and execute query
                es_query = {
                    "knn": {
                        "field": "embedding",
                        "query_vector": query_embedding,
                        "k": 3,
                        "num_candidates": 30
                    },
                    "size": 3,
                    "_source": ["listing_id", "property_type", "price", "address", "description"]
                }
                
                response = self.es_client.search(index=self.index_name, body=es_query)
                query_time = (time.time() - query_start) * 1000
                total_time += query_time
                
                # Collect top result from each query
                if response['hits']['hits']:
                    hit = response['hits']['hits'][0]
                    result = {
                        'example_number': i,
                        'query': query,
                        'top_match': hit['_source'],
                        'score': hit['_score'],
                        'total_hits': response['hits']['total']['value'],
                        'query_time_ms': query_time
                    }
                    all_results.append(result)
                    total_hits_all += response['hits']['total']['value']

            total_time = (time.time() - start_time) * 1000

            return NaturalLanguageSearchResponse(
                query_name="Natural Language Search Examples",
                query_description=f"Demonstrates semantic understanding across {len(example_queries)} diverse queries",
                execution_time_ms=int(total_time),
                total_hits=total_hits_all,
                returned_hits=len(all_results),
                results=all_results,
                search_features=[
                    f"Tested {len(example_queries)} diverse natural language queries",
                    f"Average query time: {total_time/len(example_queries):.1f}ms",
                    "Query types: family homes, condos, work-from-home, eco-friendly, luxury",
                    "Each query generates unique embedding for semantic matching",
                    "Demonstrates AI understanding beyond keyword matching"
                ],
                original_query=f"Multiple examples: {', '.join(example_queries[:2])}..."
            )

        except Exception as e:
            logger.error(f"Natural language examples failed: {e}")
            return NaturalLanguageSearchResponse(
                query_name="Natural Language Examples Failed",
                query_description="Multiple example queries encountered an error",
                execution_time_ms=int((time.time() - start_time) * 1000),
                total_hits=0,
                returned_hits=0,
                results=[],
                search_features=[f"Error: {str(e)}"],
                original_query="Multiple examples"
            )

    async def semantic_vs_keyword_comparison(
        self,
        query: str = "stunning views from modern kitchen",
        size: int = 5
    ) -> SemanticComparisonResponse:
        """Compare semantic search with keyword search.
        
        Args:
            query: Natural language query
            size: Number of results to return
            
        Returns:
            Comparison response with both search results
        """
        start_time = time.time()
        logger.info(f"Comparing semantic vs keyword search: {query}")

        # Run semantic search
        semantic_start = time.time()
        semantic_results = []
        semantic_hits = 0
        
        try:
            query_embedding = self.embedding_service.embed_query(query)
            semantic_query = {
                "knn": {
                    "field": "embedding", 
                    "query_vector": query_embedding,
                    "k": size,
                    "num_candidates": size * 10
                },
                "size": size,
                "_source": ["listing_id", "property_type", "price", "address", "description"]
            }
            
            response = self.es_client.search(index=self.index_name, body=semantic_query)
            semantic_hits = response['hits']['total']['value']
            for hit in response['hits']['hits']:
                result = hit['_source']
                result['_score'] = hit['_score']
                semantic_results.append(result)
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")

        semantic_time = (time.time() - semantic_start) * 1000

        # Run keyword search
        keyword_start = time.time()
        keyword_query = {
            "query": {
                "multi_match": {
                    "query": query,
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
            "_source": ["listing_id", "property_type", "price", "address", "description"]
        }

        keyword_results = []
        keyword_hits = 0

        try:
            response = self.es_client.search(index=self.index_name, body=keyword_query)
            keyword_hits = response['hits']['total']['value']
            for hit in response['hits']['hits']:
                result = hit['_source']
                result['_score'] = hit['_score']
                keyword_results.append(result)
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")

        keyword_time = (time.time() - keyword_start) * 1000

        # Compare results
        semantic_ids = {r.get('listing_id') for r in semantic_results if 'listing_id' in r}
        keyword_ids = {r.get('listing_id') for r in keyword_results if 'listing_id' in r}
        overlap = semantic_ids & keyword_ids

        total_time = (time.time() - start_time) * 1000

        return SemanticComparisonResponse(
            query=query,
            semantic={
                'total_hits': semantic_hits,
                'top_results': semantic_results[:3],
                'execution_time_ms': semantic_time,
                'search_type': 'AI embedding-based semantic search',
                'top_score': semantic_results[0].get('_score', 0) if semantic_results else 0
            },
            keyword={
                'total_hits': keyword_hits,
                'top_results': keyword_results[:3],
                'execution_time_ms': keyword_time,
                'search_type': 'Traditional BM25 keyword search',
                'top_score': keyword_results[0].get('_score', 0) if keyword_results else 0
            },
            comparison={
                'overlap_count': len(overlap),
                'unique_to_semantic': len(semantic_ids - keyword_ids),
                'unique_to_keyword': len(keyword_ids - semantic_ids),
                'semantic_advantage': 'Better at understanding intent and context',
                'keyword_advantage': 'Better at exact term matching',
                'recommendation': 'Hybrid search combines both approaches for best results'
            },
            execution_time_ms=int(total_time)
        )

    async def search(self, request: NaturalLanguageSearchRequest) -> Dict[str, Any]:
        """Execute natural language search based on request type.
        
        Args:
            request: Natural language search request
            
        Returns:
            Search results based on request type
        """
        if request.search_type == "semantic":
            response = await self.semantic_search(request.query, request.size)
            return response.model_dump()
        elif request.search_type == "examples":
            response = await self.natural_language_examples()
            return response.model_dump()
        elif request.search_type == "comparison":
            response = await self.semantic_vs_keyword_comparison(request.query, request.size)
            return response.model_dump()
        else:
            raise ValueError(f"Unknown search type: {request.search_type}")