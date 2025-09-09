"""
Core hybrid search engine implementation.

Combines semantic vector search with traditional text search using
Elasticsearch's native RRF (Reciprocal Rank Fusion) for optimal results.
"""

import time
from typing import Optional
from elasticsearch import Elasticsearch

from real_estate_search.config import AppConfig
from real_estate_search.embeddings import QueryEmbeddingService
from .models import HybridSearchParams, HybridSearchResult
from .location import LocationUnderstandingModule
from .query_builder import RRFQueryBuilder
from .search_executor import SearchExecutor
from .result_processor import ResultProcessor
from .logging_config import LoggerFactory, PerformanceLogger

logger = LoggerFactory.get_logger("HybridSearchEngine")


class HybridSearchEngine:
    """
    Hybrid search engine combining vector and text search with RRF.
    
    Uses modular architecture with separate components for:
    - Query building (RRFQueryBuilder)
    - Search execution (SearchExecutor)
    - Result processing (ResultProcessor)
    - Location understanding (LocationUnderstandingModule)
    """
    
    def __init__(self, es_client: Elasticsearch, config: Optional[AppConfig] = None):
        """
        Initialize the hybrid search engine with modular components.
        
        Args:
            es_client: Elasticsearch client instance
            config: Application configuration (loads default if None)
        """
        self.config = config or AppConfig.load()
        
        # Initialize modular components
        self.embedding_service = QueryEmbeddingService(config=self.config.embedding)
        self.location_module = LocationUnderstandingModule()
        self.query_builder = RRFQueryBuilder()
        self.search_executor = SearchExecutor(es_client=es_client)
        self.result_processor = ResultProcessor()
        self.performance_logger = PerformanceLogger("HybridSearchEngine.Performance")
        
        logger.info("Initialized HybridSearchEngine with modular architecture")
    
    def search(self, params: HybridSearchParams) -> HybridSearchResult:
        """
        Execute hybrid search with RRF fusion and optional location filtering.
        
        Uses modular components for:
        1. Query embedding generation
        2. Query building with filters
        3. Search execution with retries
        4. Result processing and transformation
        
        Args:
            params: Search parameters with optional location intent
            
        Returns:
            HybridSearchResult with ranked results
        """
        start_time = time.time()
        embedding_start = 0
        embedding_time = 0
        
        logger.info(f"Starting hybrid search for query: '{params.query_text}'")
        
        # Determine query text for search
        query_for_search = self._get_search_query(params)
        
        # Generate query embedding
        embedding_start = time.time()
        query_vector = self._generate_embedding(query_for_search, params.query_text)
        embedding_time = int((time.time() - embedding_start) * 1000)
        
        # Build Elasticsearch query
        query_body = self.query_builder.build_query(params, query_vector, query_for_search)
        
        # Execute search with error handling
        try:
            response, metrics = self.search_executor.execute(query_body)
            
            # Calculate total execution time
            total_execution_time = int((time.time() - start_time) * 1000)
            
            # Process results
            rrf_params = {
                'rank_constant': params.rank_constant,
                'total_retrievers': 2
            }
            
            result = self.result_processor.process_response(
                query=params.query_text,
                response=response,
                execution_time_ms=total_execution_time,
                location_intent=params.location_intent,
                rrf_params=rrf_params
            )
            
            # Log performance metrics
            self.performance_logger.log_search_performance(
                query=params.query_text,
                total_time_ms=total_execution_time,
                es_time_ms=metrics.execution_time_ms,
                embedding_time_ms=embedding_time,
                result_count=result.total_hits
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise
    
    def _get_search_query(self, params: HybridSearchParams) -> str:
        """
        Determine the query text to use for search.
        
        Args:
            params: Search parameters
            
        Returns:
            Query text (cleaned if location was extracted)
        """
        if params.location_intent and params.location_intent.has_location:
            query = params.location_intent.cleaned_query
            logger.info(
                f"Using cleaned query: '{query}' with location filters - "
                f"City: {params.location_intent.city}, State: {params.location_intent.state}"
            )
            return query
        return params.query_text
    
    def _generate_embedding(self, query_for_search: str, original_query: str) -> list[float]:
        """
        Generate embedding vector for the search query.
        
        Args:
            query_for_search: Query text to embed
            original_query: Original query for logging
            
        Returns:
            Query embedding vector
        """
        self.embedding_service.initialize()
        try:
            query_vector = self.embedding_service.embed_query(query_for_search)
            logger.info(
                f"Generated embedding vector of dimension {len(query_vector)} "
                f"for query: '{query_for_search}'"
            )
            if query_for_search != original_query:
                logger.debug(f"Original query was: '{original_query}'")
            return query_vector
        finally:
            self.embedding_service.close()
    
    def search_with_location(self, query: str, size: int = 10) -> HybridSearchResult:
        """
        Execute location-aware hybrid search.
        
        Automatically extracts location from natural language query
        and applies geographic filters along with hybrid search.
        
        Args:
            query: Natural language search query
            size: Number of results to return
            
        Returns:
            HybridSearchResult with location-filtered results
        """
        logger.info(f"Starting location-aware search for: '{query}'")
        
        # Extract location intent using DSPy module
        location_intent = self.location_module(query)
        self._log_location_extraction(location_intent)
        
        # Build parameters and execute search
        params = HybridSearchParams(
            query_text=query,
            size=size,
            location_intent=location_intent
        )
        
        return self.search(params)
    
    def _log_location_extraction(self, location_intent) -> None:
        """
        Log extracted location information.
        
        Args:
            location_intent: Extracted location intent
        """
        if location_intent.has_location:
            components = []
            if location_intent.city:
                components.append(f"City: {location_intent.city}")
            if location_intent.state:
                components.append(f"State: {location_intent.state}")
            if location_intent.neighborhood:
                components.append(f"Neighborhood: {location_intent.neighborhood}")
            if location_intent.zip_code:
                components.append(f"ZIP: {location_intent.zip_code}")
            
            logger.info(
                f"Location extracted - {', '.join(components)}, "
                f"Confidence: {location_intent.confidence:.2f}"
            )
        else:
            logger.info("No location detected in query")
    
