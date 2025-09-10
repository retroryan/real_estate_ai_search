"""
Demo runner for semantic search functionality.

Orchestrates semantic search demonstrations using the modular services.
"""

from typing import Optional
import logging
from elasticsearch import Elasticsearch

from ...config import AppConfig
from ...embeddings.exceptions import (
    EmbeddingServiceError, 
    EmbeddingGenerationError,
    ConfigurationError
)
from ..property.models import PropertySearchResult
from .constants import (
    DEFAULT_QUERY,
    DEFAULT_SIZE,
    EXAMPLE_QUERIES,
    MATCH_EXPLANATIONS
)
from .embedding_service import get_embedding_service
from ..property.query_builder import PropertyQueryBuilder
from .search_executor import SearchExecutor
# SemanticDisplayService removed - using result model display methods


logger = logging.getLogger(__name__)


def demo_natural_language_search(
    es_client: Elasticsearch,
    query: str = DEFAULT_QUERY,
    size: int = DEFAULT_SIZE,
    config: Optional[AppConfig] = None
) -> PropertySearchResult:
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
        PropertySearchResult with semantically similar properties
    """
    query_name = f"Natural Language Search: '{query}'"
    query_description = f"Semantic search using natural language query: '{query}'"
    
    # Initialize services
    executor = SearchExecutor(es_client)
    query_builder = PropertyQueryBuilder()
    
    # Generate query embedding
    embedding_time_ms = 0
    query_embedding = None
    
    try:
        with get_embedding_service(config) as embedding_service:
            query_embedding, embedding_time_ms = embedding_service.generate_query_embedding(query)
    except (ConfigurationError, EmbeddingServiceError, EmbeddingGenerationError) as e:
        logger.error(f"Failed to generate embedding: {e}")
        return executor.create_error_result(
            query_name=query_name,
            query_description=query_description,
            error_message=f"Embedding generation failed: {str(e)}"
        )
    
    # Build and execute KNN query
    es_query = query_builder.knn_semantic_search(query_embedding, size)
    
    try:
        raw_results, total_hits, search_time_ms = executor.execute_search(
            es_query, "properties"
        )
        
        total_time_ms = embedding_time_ms + search_time_ms
        property_results = executor.convert_to_property_results(raw_results)
        
        result = PropertySearchResult(
            query_name=query_name,
            query_description=query_description,
            execution_time_ms=int(total_time_ms),
            total_hits=total_hits,
            returned_hits=len(property_results),
            results=property_results,
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
        
        return result
        
    except Exception as e:
        logger.error(f"Error in natural language search: {e}")
        return executor.create_error_result(
            query_name=query_name,
            query_description=query_description,
            error_message=f"Search failed: {str(e)}",
            execution_time_ms=int(embedding_time_ms)
        )


def demo_natural_language_examples(
    es_client: Elasticsearch,
    config: Optional[AppConfig] = None
) -> PropertySearchResult:
    """
    Run multiple natural language search examples.
    
    Demonstrates various types of natural language queries that can be
    understood semantically by the embedding model.
    
    Args:
        es_client: Elasticsearch client
        config: Application configuration
        
    Returns:
        PropertySearchResult containing all example query results
    """
    # Initialize services
    executor = SearchExecutor(es_client)
    query_builder = PropertyQueryBuilder()
    
    # Early return if no examples configured
    if not EXAMPLE_QUERIES:
        return executor.create_error_result(
            query_name="Natural Language Examples",
            query_description="Multiple natural language queries",
            error_message="No example queries configured"
        )
    
    all_properties = []
    total_execution_time = 0
    total_hits_sum = 0
    query_descriptions = []
    successful_queries = 0
    failed_queries = 0
    
    try:
        with get_embedding_service(config) as embedding_service:
            for i, (query_text, query_description) in enumerate(EXAMPLE_QUERIES, 1):
                try:
                    # Generate embedding
                    query_embedding, embedding_time_ms = embedding_service.generate_query_embedding(query_text)
                    
                    # Build and execute query
                    es_query = query_builder.knn_semantic_search(
                        query_embedding, 
                        size=5
                    )
                    
                    raw_results, total_hits, search_time_ms = executor.execute_search(
                        es_query, "properties"
                    )
                    
                    total_time_ms = embedding_time_ms + search_time_ms
                    property_results = executor.convert_to_property_results(raw_results)
                    
                    # Collect results
                    all_properties.extend(property_results)
                    total_execution_time += total_time_ms
                    total_hits_sum += total_hits
                    query_descriptions.append(f"{i}. {query_description}: '{query_text}'")
                    successful_queries += 1
                    
                    # Note: Display is handled by commands.py, not here
                    
                except Exception as e:
                    logger.error(f"Failed to process query {i}: {e}")
                    query_descriptions.append(f"{i}. {query_description}: ERROR - {str(e)}")
                    failed_queries += 1
                    # Error already logged above, no console display needed
                    
    except Exception as e:
        logger.error(f"Failed to initialize embedding service: {e}")
        return executor.create_error_result(
            query_name="Natural Language Examples",
            query_description="Multiple natural language queries",
            error_message=f"Embedding service initialization failed: {str(e)}"
        )
    
    # Check if any queries succeeded
    if successful_queries == 0:
        return executor.create_error_result(
            query_name="Natural Language Examples",
            query_description="Multiple natural language queries",
            error_message=f"All {len(EXAMPLE_QUERIES)} queries failed"
        )
    
    # Note: Display is handled by commands.py, not here
    
    # Calculate average time safely
    avg_time = total_execution_time / successful_queries if successful_queries > 0 else 0
    
    # Build description string
    description = "Demonstration of " + "; ".join(query_descriptions) if query_descriptions else "No queries executed"
    
    # Return combined result
    return PropertySearchResult(
        query_name="Natural Language Search Examples",
        query_description=description,
        execution_time_ms=int(total_execution_time),
        total_hits=total_hits_sum,
        returned_hits=len(all_properties),
        results=all_properties[:10],  # Limit to first 10 for display
        query_dsl={"multiple_queries": f"Executed {successful_queries} of {len(EXAMPLE_QUERIES)} semantic searches"},
        es_features=[
            f"Executed {successful_queries} natural language queries successfully",
            f"Failed queries: {failed_queries}" if failed_queries > 0 else "All queries succeeded",
            f"Total execution time: {total_execution_time:.1f}ms",
            f"Average time per query: {avg_time:.1f}ms" if successful_queries > 0 else "No successful queries",
            "KNN search with 1024-dimensional embeddings",
            "Semantic understanding across multiple query types"
        ],
        indexes_used=[
            "properties index with pre-computed embeddings",
            f"Total properties found across all queries: {total_hits_sum}"
        ]
    )


def demo_semantic_vs_keyword_comparison(
    es_client: Elasticsearch,
    query: str = "stunning views from modern kitchen",
    size: int = 5,
    config: Optional[AppConfig] = None
) -> PropertySearchResult:
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
        PropertySearchResult with combined results from both search methods
    """
    # Initialize services
    executor = SearchExecutor(es_client)
    query_builder = PropertyQueryBuilder()
    
    # Run semantic search
    semantic_results = []
    semantic_hits = 0
    semantic_time = 0
    
    try:
        with get_embedding_service(config) as embedding_service:
            query_embedding, embedding_time = embedding_service.generate_query_embedding(query)
            
            semantic_query = query_builder.knn_semantic_search(query_embedding, size)
            raw_results, semantic_hits, search_time = executor.execute_search(
                semantic_query, "properties"
            )
            semantic_results = raw_results
            semantic_time = embedding_time + search_time
            
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
    
    # Run keyword search
    keyword_query = query_builder.keyword_search(query, size)
    keyword_results = []
    keyword_hits = 0
    keyword_time = 0
    
    try:
        raw_results, keyword_hits, keyword_time = executor.execute_search(
            keyword_query, "properties"
        )
        keyword_results = raw_results
    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
    
    # Compare and combine results
    semantic_ids = {r.get('listing_id') for r in semantic_results if 'listing_id' in r}
    keyword_ids = {r.get('listing_id') for r in keyword_results if 'listing_id' in r}
    overlap = semantic_ids & keyword_ids
    
    comparison_results = {
        'semantic': {
            'total_hits': semantic_hits,
            'top_results': semantic_results[:3],
            'execution_time_ms': semantic_time
        },
        'keyword': {
            'total_hits': keyword_hits,
            'top_results': keyword_results[:3],
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
    
    # Combine results for display
    combined_results = []
    seen_ids = set()
    
    # Add semantic results first with search type marker
    for res in semantic_results:
        if res.get('listing_id') not in seen_ids:
            res['search_type'] = 'semantic'
            res['description'] = f"[SEMANTIC] {res.get('description', '')}"
            combined_results.append(res)
            seen_ids.add(res.get('listing_id'))
    
    # Add unique keyword results with search type marker
    for res in keyword_results:
        if res.get('listing_id') not in seen_ids:
            res['search_type'] = 'keyword'
            res['description'] = f"[KEYWORD] {res.get('description', '')}"
            combined_results.append(res)
            seen_ids.add(res.get('listing_id'))
    
    # Convert to PropertyResult objects
    property_results = executor.convert_to_property_results(combined_results)
    
    result = PropertySearchResult(
        query_name="Demo 13: Semantic vs Keyword Search Comparison (Combined Results)",
        query_description=f"Comparing semantic and keyword search for: '{query}'",
        execution_time_ms=int(semantic_time + keyword_time),
        total_hits=semantic_hits + keyword_hits,
        returned_hits=len(property_results),
        results=property_results,
        query_dsl={
            "semantic_query": {"knn": "...truncated..."},
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
            f"  • Unique to keyword: {len(keyword_ids - semantic_ids)}",
            "",
            "RESULTS TABLE BELOW:",
            "  • Shows combined results from BOTH search methods",
            "  • Results marked with [SEMANTIC] or [KEYWORD] prefix",
            "  • Semantic results appear first, followed by keyword-only results"
        ],
        indexes_used=[
            "properties index - tested with both search methods",
            f"Query tested: '{query}'"
        ],
        aggregations=comparison_results
    )
    
    return result