"""
Natural language semantic search demo using query embeddings.

This module demonstrates semantic search using natural language queries
by generating embeddings on-the-fly and performing KNN search.
"""

from typing import Dict, Any, Optional, List
from elasticsearch import Elasticsearch
import logging
import time

from .models import DemoQueryResult
from ..embeddings import QueryEmbeddingService, EmbeddingConfig
from ..embeddings.exceptions import (
    EmbeddingServiceError, 
    EmbeddingGenerationError,
    ConfigurationError
)
from ..config import AppConfig

logger = logging.getLogger(__name__)


def demo_natural_language_search(
    es_client: Elasticsearch,
    query: str = "modern home with mountain views and open floor plan",
    size: int = 10,
    config: Optional[AppConfig] = None
) -> DemoQueryResult:
    """
    Demo: Natural language semantic search using query embeddings.
    
    This demo shows how to:
    1. Take a natural language query
    2. Generate an embedding using the same model as property embeddings
    3. Use KNN search to find semantically similar properties
    4. Return results ranked by semantic similarity
    
    Args:
        es_client: Elasticsearch client
        query: Natural language search query
        size: Number of results to return
        config: Application configuration (for embedding service)
        
    Returns:
        DemoQueryResult with semantically similar properties
    """
    
    # Load config if not provided
    if config is None:
        config = AppConfig.load()
    
    # Initialize embedding service
    try:
        embedding_service = QueryEmbeddingService(config=config.embedding)
        embedding_service.initialize()
    except (ConfigurationError, EmbeddingServiceError) as e:
        logger.error(f"Failed to initialize embedding service: {e}")
        return DemoQueryResult(
            query_name=f"Natural Language Search: '{query[:50]}...'",
            query_description="Natural language semantic search using query embeddings",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl={"error": f"Embedding service initialization failed: {str(e)}"},
            es_features=["Failed to generate query embedding"]
        )
    
    # Generate query embedding
    start_time = time.time()
    try:
        logger.info(f"Generating embedding for query: '{query}'")
        query_embedding = embedding_service.embed_query(query)
        embedding_time_ms = (time.time() - start_time) * 1000
        logger.info(f"Generated query embedding in {embedding_time_ms:.1f}ms")
    except EmbeddingGenerationError as e:
        logger.error(f"Failed to generate query embedding: {e}")
        return DemoQueryResult(
            query_name=f"Natural Language Search: '{query[:50]}...'",
            query_description="Natural language semantic search using query embeddings",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl={"error": f"Embedding generation failed: {str(e)}"},
            es_features=["Failed to generate query embedding"]
        )
    finally:
        # Clean up embedding service
        embedding_service.close()
    
    # Build KNN query with generated embedding
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
    try:
        search_start = time.time()
        response = es_client.search(index="properties", body=es_query)
        search_time_ms = (time.time() - search_start) * 1000
        
        # Process results
        results = []
        for hit in response['hits']['hits']:
            result = hit['_source']
            result['_score'] = hit['_score']
            result['_similarity_score'] = hit['_score']
            results.append(result)
        
        total_time_ms = embedding_time_ms + search_time_ms
        
        return DemoQueryResult(
            query_name=f"Natural Language Search: '{query[:50]}...'",
            query_description=f"Semantic search using natural language query: '{query}'",
            execution_time_ms=int(total_time_ms),
            total_hits=response['hits']['total']['value'],
            returned_hits=len(results),
            results=results,
            query_dsl=es_query,
            es_features=[
                f"Query Embedding Generation - {embedding_time_ms:.1f}ms using Voyage-3 model",
                f"KNN Search - {search_time_ms:.1f}ms for vector similarity search",
                "Dense Vectors - 1024-dimensional embeddings for semantic understanding",
                "Natural Language Understanding - Convert text queries to semantic vectors",
                "Cosine Similarity - Vector distance metric for relevance ranking"
            ],
            indexes_used=[
                "properties index - Real estate listings with AI embeddings",
                f"Searching for {size} properties semantically similar to query"
            ],
            aggregations={
                "timing_breakdown": {
                    "embedding_generation_ms": embedding_time_ms,
                    "elasticsearch_search_ms": search_time_ms,
                    "total_ms": total_time_ms
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error in natural language search: {e}")
        return DemoQueryResult(
            query_name=f"Natural Language Search: '{query[:50]}...'",
            query_description="Natural language semantic search using query embeddings",
            execution_time_ms=int(embedding_time_ms),
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=es_query,
            es_features=[f"Search failed: {str(e)}"]
        )


def demo_natural_language_examples(
    es_client: Elasticsearch,
    config: Optional[AppConfig] = None
) -> List[DemoQueryResult]:
    """
    Run multiple natural language search examples.
    
    Demonstrates various types of natural language queries that can be
    understood semantically by the embedding model.
    
    Args:
        es_client: Elasticsearch client
        config: Application configuration
        
    Returns:
        List of DemoQueryResult objects, one for each example query
    """
    
    example_queries = [
        ("cozy family home near good schools and parks", "Family-oriented home search"),
        ("modern downtown condo with city views", "Urban condo search"),
        ("spacious property with home office and fast internet", "Work-from-home property search"),
        ("eco-friendly house with solar panels and energy efficiency", "Sustainable home search"),
        ("luxury estate with pool and entertainment areas", "Luxury property search")
    ]
    
    demo_results = []
    
    # Load config if not provided
    if config is None:
        config = AppConfig.load()
    
    # Initialize embedding service once for all queries
    try:
        embedding_service = QueryEmbeddingService(config=config.embedding)
        embedding_service.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize embedding service: {e}")
        # Return empty list on initialization failure
        return []
    
    try:
        for i, (query_text, query_description) in enumerate(example_queries, 1):
            # Generate embedding
            start_time = time.time()
            try:
                query_embedding = embedding_service.embed_query(query_text)
            except Exception as e:
                logger.error(f"Failed to generate embedding for query {i}: {e}")
                # Create error result for this query
                demo_results.append(DemoQueryResult(
                    query_name=f"Example {i}: {query_description}",
                    query_description=f"Natural language search: '{query_text}'",
                    execution_time_ms=0,
                    total_hits=0,
                    returned_hits=0,
                    results=[],
                    query_dsl={"error": f"Embedding generation failed: {str(e)}"},
                    es_features=[f"Failed to generate embedding for query {i}"]
                ))
                continue
            
            # Build and execute query
            es_query = {
                "knn": {
                    "field": "embedding",
                    "query_vector": query_embedding,
                    "k": 5,
                    "num_candidates": 50
                },
                "size": 5,
                "_source": [
                    "listing_id", "property_type", "price", "bedrooms", "bathrooms",
                    "square_feet", "address", "description"
                ]
            }
            
            try:
                response = es_client.search(index="properties", body=es_query)
                query_time = (time.time() - start_time) * 1000
                
                # Process results for this query
                results = []
                for hit in response['hits']['hits']:
                    result = hit['_source']
                    result['_score'] = hit['_score']
                    result['_similarity_score'] = hit['_score']
                    results.append(result)
                
                # Create DemoQueryResult for this specific example
                demo_results.append(DemoQueryResult(
                    query_name=f"Example {i}: {query_description}",
                    query_description=f"Natural language search: '{query_text}'",
                    execution_time_ms=int(query_time),
                    total_hits=response['hits']['total']['value'],
                    returned_hits=len(results),
                    results=results,
                    query_dsl=es_query,
                    es_features=[
                        f"Query {i} of {len(example_queries)}: {query_description}",
                        f"Execution time: {query_time:.1f}ms",
                        "KNN search with 1024-dimensional embeddings",
                        "Semantic understanding of natural language"
                    ],
                    indexes_used=[
                        "properties index with pre-computed embeddings",
                        f"Found {response['hits']['total']['value']} semantically similar properties"
                    ]
                ))
                
            except Exception as e:
                logger.error(f"Search failed for query {i}: {e}")
                demo_results.append(DemoQueryResult(
                    query_name=f"Example {i}: {query_description}",
                    query_description=f"Natural language search: '{query_text}'",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    total_hits=0,
                    returned_hits=0,
                    results=[],
                    query_dsl=es_query,
                    es_features=[f"Search failed: {str(e)}"]
                ))
    
    finally:
        embedding_service.close()
    
    return demo_results


def demo_semantic_vs_keyword_comparison(
    es_client: Elasticsearch,
    query: str = "stunning views from modern kitchen",
    size: int = 5,
    config: Optional[AppConfig] = None
) -> DemoQueryResult:
    """
    Compare semantic search with traditional keyword search.
    
    Runs the same query using both semantic (embedding-based) and
    keyword (text-based) search to demonstrate the differences.
    
    Args:
        es_client: Elasticsearch client
        query: Natural language search query
        size: Number of results to return
        config: Application configuration
        
    Returns:
        Dictionary with 'semantic' and 'keyword' DemoQueryResults
    """
    
    # Load config if not provided
    if config is None:
        config = AppConfig.load()
    
    # Run semantic search
    semantic_start = time.time()
    
    # Initialize embedding service
    try:
        embedding_service = QueryEmbeddingService(config=config.embedding)
        embedding_service.initialize()
        query_embedding = embedding_service.embed_query(query)
        embedding_service.close()
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        query_embedding = None
    
    semantic_results = []
    semantic_hits = 0
    
    if query_embedding:
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
        
        try:
            response = es_client.search(index="properties", body=semantic_query)
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
        "_source": [
            "listing_id", "property_type", "price", "bedrooms", "bathrooms",
            "square_feet", "address", "description", "features", "amenities"
        ]
    }
    
    keyword_results = []
    keyword_hits = 0
    
    try:
        response = es_client.search(index="properties", body=keyword_query)
        keyword_hits = response['hits']['total']['value']
        for hit in response['hits']['hits']:
            result = hit['_source']
            result['_score'] = hit['_score']
            keyword_results.append(result)
    except Exception as e:
        logger.error(f"Error in keyword search: {e}")
    
    keyword_time = (time.time() - keyword_start) * 1000
    
    # Compare results
    semantic_ids = {r.get('listing_id') for r in semantic_results if 'listing_id' in r}
    keyword_ids = {r.get('listing_id') for r in keyword_results if 'listing_id' in r}
    overlap = semantic_ids & keyword_ids
    
    # Combine results for comparison
    comparison_results = {
        'semantic': {
            'total_hits': semantic_hits,
            'top_results': semantic_results[:3] if semantic_results else [],
            'execution_time_ms': semantic_time
        },
        'keyword': {
            'total_hits': keyword_hits,
            'top_results': keyword_results[:3] if keyword_results else [],
            'execution_time_ms': keyword_time
        },
        'comparison': {
            'overlap_count': len(overlap),
            'unique_to_semantic': len(semantic_ids - keyword_ids),
            'unique_to_keyword': len(keyword_ids - semantic_ids),
            'semantic_top_score': semantic_results[0].get('_score', 0) if semantic_results else 0,
            'keyword_top_score': keyword_results[0].get('_score', 0) if keyword_results else 0
        }
    }
    
    return DemoQueryResult(
        query_name="Demo 14: Semantic vs Keyword Search Comparison",
        query_description=f"Comparing semantic and keyword search for: '{query}'",
        execution_time_ms=int(semantic_time + keyword_time),
        total_hits=semantic_hits + keyword_hits,
        returned_hits=len(semantic_results) + len(keyword_results),
        results=[comparison_results],
        query_dsl={
            "semantic_query": {"knn": "..."},
            "keyword_query": keyword_query
        },
        es_features=[
            "SEMANTIC SEARCH:",
            f"  • Found {semantic_hits} properties in {semantic_time:.1f}ms",
            f"  • Top score: {comparison_results['comparison']['semantic_top_score']:.3f}",
            "  • Uses AI embeddings for semantic understanding",
            "",
            "KEYWORD SEARCH:",
            f"  • Found {keyword_hits} properties in {keyword_time:.1f}ms",
            f"  • Top score: {comparison_results['comparison']['keyword_top_score']:.3f}",
            "  • Uses traditional text matching with BM25",
            "",
            "COMPARISON:",
            f"  • Overlap in top {size}: {len(overlap)} properties",
            f"  • Unique to semantic: {len(semantic_ids - keyword_ids)}",
            f"  • Unique to keyword: {len(keyword_ids - semantic_ids)}"
        ],
        indexes_used=[
            "properties index - tested with both search methods",
            f"Query tested: '{query}'"
        ],
        aggregations=comparison_results
    )