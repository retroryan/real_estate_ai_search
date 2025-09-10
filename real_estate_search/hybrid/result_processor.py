"""
Result processor module for handling Elasticsearch search results.

Transforms raw Elasticsearch responses into structured search results
with proper scoring and metadata.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .models import SearchResult, HybridSearchResult, LocationIntent
from real_estate_search.models import PropertyListing

logger = logging.getLogger(__name__)


class SearchMetadata(BaseModel):
    """Metadata about search execution."""
    rrf_used: bool = Field(..., description="Whether RRF was used")
    rank_constant: int = Field(..., description="RRF rank constant used")
    total_retrievers: int = Field(..., description="Number of retrievers used")
    elasticsearch_took: int = Field(..., description="Elasticsearch execution time in ms")


class ResultProcessor:
    """
    Processes Elasticsearch responses into structured results.
    
    Handles:
    - Result extraction and transformation
    - Score calculation and ranking
    - Metadata collection
    - Error handling
    """
    
    def __init__(self):
        """Initialize the result processor."""
        logger.debug("Initialized ResultProcessor")
    
    def process_response(
        self,
        query: str,
        response: Dict[str, Any],
        execution_time_ms: int,
        location_intent: Optional[LocationIntent] = None,
        rrf_params: Optional[Dict[str, Any]] = None
    ) -> HybridSearchResult:
        """
        Process Elasticsearch response into structured results.
        
        Args:
            query: Original query text
            response: Raw Elasticsearch response
            execution_time_ms: Total execution time in milliseconds
            location_intent: Location extraction information if available
            rrf_params: RRF parameters used in the query
            
        Returns:
            Structured HybridSearchResult
        """
        # Extract results
        results = self._extract_results(response)
        
        # Build metadata
        metadata = self._build_metadata(response, rrf_params)
        
        # Log summary
        self._log_summary(query, response, execution_time_ms, location_intent)
        
        return HybridSearchResult(
            query=query,
            total_hits=self._get_total_hits(response),
            execution_time_ms=execution_time_ms,
            results=results,
            search_metadata=metadata.model_dump(),
            location_intent=location_intent
        )
    
    def _extract_results(self, response: Dict[str, Any]) -> List[SearchResult]:
        """
        Extract search results from Elasticsearch response.
        
        Clean, direct conversion from Elasticsearch hits to SearchResult objects.
        
        Args:
            response: Elasticsearch response
            
        Returns:
            List of SearchResult objects
        """
        hits = response.get('hits', {}).get('hits', [])
        results = [self._create_search_result(hit) for hit in hits]
        
        logger.debug(f"Extracted {len(results)} search results")
        return results
    
    def _create_search_result(self, hit: Dict[str, Any]) -> SearchResult:
        """
        Create SearchResult directly from Elasticsearch hit.
        
        Clean conversion without intermediate steps or data mutation.
        
        Args:
            hit: Complete Elasticsearch hit
            
        Returns:
            SearchResult with property data and scoring
        """
        # Direct conversion using proper method
        property_listing = PropertyListing.from_elasticsearch_hit(hit)
        
        # Extract score from hit (not from property)
        score = hit.get('_score', 0.0)
        
        # Set hybrid_score on the PropertyListing since RRF provides a combined score
        property_listing.hybrid_score = score
        
        return SearchResult(
            listing_id=property_listing.listing_id,
            hybrid_score=score,
            text_score=None,  # RRF combines scores internally
            vector_score=None,  # Individual scores not available with RRF
            property_data=property_listing
        )
    
    def _build_metadata(
        self,
        response: Dict[str, Any],
        rrf_params: Optional[Dict[str, Any]] = None
    ) -> SearchMetadata:
        """
        Build search metadata from response and parameters.
        
        Args:
            response: Elasticsearch response
            rrf_params: RRF parameters used
            
        Returns:
            SearchMetadata object
        """
        # Default RRF parameters
        if rrf_params is None:
            rrf_params = {
                'rank_constant': 60,
                'total_retrievers': 2
            }
        
        return SearchMetadata(
            rrf_used=True,
            rank_constant=rrf_params.get('rank_constant', 60),
            total_retrievers=rrf_params.get('total_retrievers', 2),
            elasticsearch_took=response.get('took', 0)
        )
    
    def _get_total_hits(self, response: Dict[str, Any]) -> int:
        """
        Extract total hits from response.
        
        Args:
            response: Elasticsearch response
            
        Returns:
            Total number of matching documents
        """
        hits = response.get('hits', {})
        total = hits.get('total', {})
        
        # Handle different response formats
        if isinstance(total, dict):
            return total.get('value', 0)
        elif isinstance(total, int):
            return total
        else:
            return 0
    
    def _log_summary(
        self,
        query: str,
        response: Dict[str, Any],
        execution_time_ms: int,
        location_intent: Optional[LocationIntent]
    ) -> None:
        """
        Log search result summary.
        
        Args:
            query: Original query
            response: Elasticsearch response
            execution_time_ms: Execution time
            location_intent: Location information
        """
        total_hits = self._get_total_hits(response)
        hits = response.get('hits', {}).get('hits', [])
        
        logger.info(
            f"Search completed - Query: '{query}', "
            f"Hits: {total_hits}, "
            f"Time: {execution_time_ms}ms"
        )
        
        if total_hits == 0:
            self._log_no_results(query, location_intent)
        else:
            self._log_top_results(hits)
    
    def _log_no_results(
        self,
        query: str,
        location_intent: Optional[LocationIntent]
    ) -> None:
        """
        Log information when no results are found.
        
        Args:
            query: Original query
            location_intent: Location information
        """
        logger.warning(f"No results found for query: '{query}'")
        
        if location_intent and location_intent.has_location:
            logger.warning(
                f"Location filters applied - "
                f"City: {location_intent.city}, "
                f"State: {location_intent.state}"
            )
    
    def _log_top_results(self, hits: List[Dict[str, Any]]) -> None:
        """
        Log information about top results.
        
        Args:
            hits: List of Elasticsearch hits
        """
        if hits:
            top_score = hits[0].get('_score', 'N/A')
            logger.info(f"Top result score: {top_score}")
            
            # Log top 3 results for debugging
            for i, hit in enumerate(hits[:3]):
                source = hit.get('_source', {})
                listing_id = source.get('listing_id', 'Unknown')
                score = hit.get('_score', 0)
                logger.debug(
                    f"Result {i+1}: ID={listing_id}, Score={score}"
                )