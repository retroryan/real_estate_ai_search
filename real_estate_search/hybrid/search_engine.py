"""
Core hybrid search engine implementation.

Combines semantic vector search with traditional text search using
Elasticsearch's native RRF (Reciprocal Rank Fusion) for optimal results.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from elasticsearch import Elasticsearch

from real_estate_search.config import AppConfig
from real_estate_search.embeddings import QueryEmbeddingService
from .models import HybridSearchParams, HybridSearchResult, SearchResult, LocationIntent
from .location import LocationUnderstandingModule, LocationFilterBuilder

logger = logging.getLogger(__name__)


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
            logger.info(f"Location intent - City: {params.location_intent.city}, State: {params.location_intent.state}")
        
        # Generate query embedding
        self.embedding_service.initialize()
        try:
            query_vector = self.embedding_service.embed_query(query_for_search)
            logger.info(f"Generated embedding vector of dimension {len(query_vector)}")
            logger.debug(f"First 5 embedding values: {query_vector[:5]}")
            logger.info(f"Query for embedding: '{query_for_search}' (was: '{params.query_text}')")
        finally:
            self.embedding_service.close()
        
        # Build RRF query using native Elasticsearch syntax
        query_body = self._build_rrf_query(params, query_vector, query_for_search)
        
        # Log the complete query being sent to Elasticsearch with truncated vector
        import json
        
        def truncate_vectors(obj):
            """Truncate query_vector fields to first 3 elements for logging."""
            if isinstance(obj, dict):
                if 'query_vector' in obj and isinstance(obj['query_vector'], list) and len(obj['query_vector']) > 3:
                    return {**obj, 'query_vector': obj['query_vector'][:3] + ['...truncated...']}
                return {k: truncate_vectors(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [truncate_vectors(item) for item in obj]
            return obj
        
        logger.info(f"Elasticsearch query body: {json.dumps(truncate_vectors(query_body), default=str)}")
        
        # Log specific filter information
        if 'retriever' in query_body and 'rrf' in query_body['retriever']:
            retrievers = query_body['retriever']['rrf']['retrievers']
            for i, retriever in enumerate(retrievers):
                if 'standard' in retriever:
                    logger.info(f"Text retriever {i} filters: {retriever.get('standard', {}).get('query', {}).get('bool', {}).get('filter', 'No filters')}")
                elif 'knn' in retriever:
                    logger.info(f"KNN retriever {i} filters: {retriever.get('knn', {}).get('filter', 'No filters')}")
        
        # Execute search
        try:
            response = self.es_client.search(
                index="properties",
                body=query_body
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            total_hits = response['hits']['total']['value']
            logger.info(f"Hybrid search completed in {execution_time}ms - Found {total_hits} results")
            
            if total_hits == 0:
                logger.warning(f"No results found for query '{params.query_text}' with cleaned query '{query_for_search}'")
                logger.warning(f"Location filters applied - City: {params.location_intent.city if params.location_intent else 'None'}, "
                             f"State: {params.location_intent.state if params.location_intent else 'None'}")
            else:
                logger.info(f"Top result score: {response['hits']['hits'][0]['_score'] if response['hits']['hits'] else 'N/A'}")
            
            # Process results
            return self._process_results(params.query_text, response, execution_time, params.location_intent)
            
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
        
        IMPORTANT PERFORMANCE OPTIMIZATION:
        This method implements the EFFICIENT filtered vector search pattern by applying
        filters DURING the kNN search phase, not after. This is critical for performance
        because:
        
        1. Filters are applied DURING vector search (inside the knn retriever's filter parameter)
           - This reduces the search space BEFORE computing expensive vector similarities
           - Much more efficient than post-filtering which would compute similarities for ALL vectors
        
        2. The same filters are consistently applied to BOTH text and vector retrievers
           - Ensures both retrieval strategies respect the location constraints
           - Prevents irrelevant results from either retriever
        
        3. Uses Elasticsearch's native RRF (Reciprocal Rank Fusion) for optimal result combination
           - Better than manual score combination
           - Preserves the benefits of both search strategies
        
        ANTI-PATTERN TO AVOID:
        Never use post_filter after kNN search - it's inefficient because it:
        - Computes vector similarities for ALL documents first
        - THEN filters results, wasting computation on documents that will be discarded
        - Can lead to fewer results than requested if many are filtered out
        
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
        
        # EFFICIENT PATTERN: Wrap text query with filters if they exist
        # Filters are applied DURING the text search phase
        if location_filters:
            text_query = {
                "bool": {
                    "must": text_query,
                    "filter": location_filters  # Applied during search, not after
                }
            }
        
        # Build vector search configuration directly
        vector_config = {
            "field": "embedding",
            "query_vector": query_vector,
            "k": min(params.size * 5, 100),
            "num_candidates": min(params.size * 10, 200)
        }
        
        # CRITICAL OPTIMIZATION: Add filters to vector search if they exist
        # This ensures filtering happens DURING kNN search, not after (post_filter)
        # The filter parameter inside knn is the EFFICIENT approach
        if location_filters:
            vector_config["filter"] = location_filters  # CORRECT: Filter during kNN, not post_filter
        
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
        execution_time: int,
        location_intent: Optional[LocationIntent] = None
    ) -> HybridSearchResult:
        """
        Process Elasticsearch response into structured results.
        
        Args:
            query: Original query text
            response: Elasticsearch response
            execution_time: Query execution time in ms
            location_intent: Extracted location information used for filtering
            
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
            search_metadata=search_metadata,
            location_intent=location_intent
        )