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
        List of DemoQueryResults for different example queries
    """
    
    example_queries = [
        "cozy family home near good schools and parks",
        "modern downtown condo with city views",
        "spacious property with home office and fast internet",
        "eco-friendly house with solar panels and energy efficiency",
        "luxury estate with pool and entertainment areas",
        "affordable starter home for first-time buyers",
        "historic Victorian house with original architecture",
        "beach house with ocean access and outdoor living",
        "mountain retreat with privacy and natural surroundings",
        "urban loft with industrial design and open concept"
    ]
    
    results = []
    
    logger.info("=" * 60)
    logger.info("NATURAL LANGUAGE SEMANTIC SEARCH EXAMPLES")
    logger.info("=" * 60)
    
    for i, query in enumerate(example_queries, 1):
        logger.info(f"\nExample {i}/{len(example_queries)}: '{query}'")
        logger.info("-" * 40)
        
        result = demo_natural_language_search(
            es_client=es_client,
            query=query,
            size=3,  # Fewer results per query for overview
            config=config
        )
        
        # Log summary
        if result.returned_hits > 0:
            logger.info(f"✓ Found {result.total_hits} matching properties")
            logger.info(f"  Top result score: {result.results[0].get('_score', 0):.3f}")
            if 'address' in result.results[0]:
                addr = result.results[0]['address']
                logger.info(f"  Top match: {addr.get('street', 'Unknown')}, {addr.get('city', 'Unknown')}")
        else:
            logger.info("✗ No results found")
        
        results.append(result)
    
    logger.info("\n" + "=" * 60)
    logger.info("SEMANTIC SEARCH EXAMPLES COMPLETE")
    logger.info("=" * 60)
    
    return results


def demo_semantic_vs_keyword_comparison(
    es_client: Elasticsearch,
    query: str = "stunning views from modern kitchen",
    size: int = 5,
    config: Optional[AppConfig] = None
) -> Dict[str, DemoQueryResult]:
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
    
    logger.info("=" * 60)
    logger.info("SEMANTIC VS KEYWORD SEARCH COMPARISON")
    logger.info(f"Query: '{query}'")
    logger.info("=" * 60)
    
    # Run semantic search
    logger.info("\n1. SEMANTIC SEARCH (using embeddings):")
    semantic_result = demo_natural_language_search(
        es_client=es_client,
        query=query,
        size=size,
        config=config
    )
    
    # Run keyword search
    logger.info("\n2. KEYWORD SEARCH (traditional text matching):")
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
    
    try:
        response = es_client.search(index="properties", body=keyword_query)
        
        keyword_results = []
        for hit in response['hits']['hits']:
            result = hit['_source']
            result['_score'] = hit['_score']
            keyword_results.append(result)
        
        keyword_result = DemoQueryResult(
            query_name=f"Keyword Search: '{query[:50]}...'",
            query_description=f"Traditional text-based search: '{query}'",
            execution_time_ms=response.get('took', 0),
            total_hits=response['hits']['total']['value'],
            returned_hits=len(keyword_results),
            results=keyword_results,
            query_dsl=keyword_query,
            es_features=[
                "Multi-Match Query - Text matching across multiple fields",
                "Field Boosting - Weighted importance of different text fields",
                "Fuzzy Matching - Handle typos and variations",
                "BM25 Scoring - Traditional text relevance algorithm"
            ]
        )
    except Exception as e:
        logger.error(f"Error in keyword search: {e}")
        keyword_result = DemoQueryResult(
            query_name=f"Keyword Search: '{query[:50]}...'",
            query_description=f"Traditional text-based search: '{query}'",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=keyword_query
        )
    
    # Compare results
    logger.info("\n" + "=" * 60)
    logger.info("COMPARISON SUMMARY:")
    logger.info("-" * 40)
    
    # Find overlap
    semantic_ids = {r.get('listing_id') for r in semantic_result.results if 'listing_id' in r}
    keyword_ids = {r.get('listing_id') for r in keyword_result.results if 'listing_id' in r}
    overlap = semantic_ids & keyword_ids
    
    logger.info(f"Semantic search found: {semantic_result.total_hits} properties")
    logger.info(f"Keyword search found: {keyword_result.total_hits} properties")
    logger.info(f"Overlap in top {size} results: {len(overlap)} properties")
    logger.info(f"Unique to semantic: {len(semantic_ids - keyword_ids)} properties")
    logger.info(f"Unique to keyword: {len(keyword_ids - semantic_ids)} properties")
    
    if semantic_result.returned_hits > 0 and keyword_result.returned_hits > 0:
        logger.info(f"\nTop semantic result score: {semantic_result.results[0].get('_score', 0):.3f}")
        logger.info(f"Top keyword result score: {keyword_result.results[0].get('_score', 0):.3f}")
    
    logger.info("=" * 60)
    
    return {
        "semantic": semantic_result,
        "keyword": keyword_result
    }