"""
Wikipedia search with automatic location extraction for demo queries.

This module provides location-aware Wikipedia search functionality by extracting
location information from natural language queries and applying geographic filters.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple

from elasticsearch import Elasticsearch

from ..models.results import WikipediaSearchResult
from ..models import WikipediaArticle
from ..hybrid.location import LocationUnderstandingModule, LocationIntent

logger = logging.getLogger(__name__)

# Constants for field boosting and configuration
WIKIPEDIA_INDEX = "wikipedia"
DEFAULT_SEARCH_SIZE = 10
SEARCH_FIELDS = {
    "title": 2.0,
    "short_summary": 1.5,
    "long_summary": 1.0,
    "categories": 1.0,
    "key_topics": 1.0
}
SOURCE_FIELDS = [
    "page_id", "title", "short_summary", "city", "state",
    "categories", "key_topics", "url"
]


class WikipediaLocationSearcher:
    """
    Handles Wikipedia searches with automatic location extraction and filtering.
    
    This class encapsulates the logic for extracting location information from
    natural language queries and building appropriate Elasticsearch queries.
    """
    
    def __init__(self, es_client: Elasticsearch):
        """
        Initialize the Wikipedia location searcher.
        
        Args:
            es_client: Elasticsearch client instance
        """
        self.es_client = es_client
        self.location_module = LocationUnderstandingModule()
    
    def build_location_filters(self, location_intent: LocationIntent) -> List[Dict[str, Any]]:
        """
        Build Elasticsearch filters from location intent for Wikipedia index.
        
        Args:
            location_intent: Extracted location information from query
            
        Returns:
            List of Elasticsearch filter clauses for Wikipedia documents
        """
        filters = []
        
        if not location_intent.has_location:
            return filters
        
        if location_intent.city:
            filters.append({
                "match": {
                    "city": location_intent.city
                }
            })
            logger.debug(f"Added city filter: {location_intent.city}")
        
        if location_intent.state:
            filters.append({
                "match": {
                    "state": location_intent.state
                }
            })
            logger.debug(f"Added state filter: {location_intent.state}")
        
        return filters
    
    def build_search_query(self, search_text: str) -> Dict[str, Any]:
        """
        Build the main search query for Wikipedia content.
        
        Args:
            search_text: Cleaned search text after location extraction
            
        Returns:
            Elasticsearch query clause
        """
        if not search_text:
            return {"match_all": {}}
        
        fields = [f"{field}^{boost}" for field, boost in SEARCH_FIELDS.items()]
        
        return {
            "multi_match": {
                "query": search_text,
                "fields": fields,
                "type": "best_fields"
            }
        }
    
    def build_query_body(
        self,
        search_text: str,
        location_filters: List[Dict[str, Any]],
        size: int
    ) -> Dict[str, Any]:
        """
        Build the complete Elasticsearch query body.
        
        Args:
            search_text: Cleaned search text
            location_filters: List of location-based filters
            size: Number of results to return
            
        Returns:
            Complete Elasticsearch query body
        """
        search_query = self.build_search_query(search_text)
        
        return {
            "query": {
                "bool": {
                    "must": [search_query],
                    "filter": location_filters
                }
            },
            "size": size,
            "_source": SOURCE_FIELDS
        }
    
    def convert_hits_to_articles(self, hits: List[Dict[str, Any]]) -> List[WikipediaArticle]:
        """
        Convert Elasticsearch hits to WikipediaArticle objects.
        
        Args:
            hits: List of Elasticsearch hit objects
            
        Returns:
            List of WikipediaArticle instances
        """
        articles = []
        
        for hit in hits:
            source = hit.get('_source', {})
            
            article = WikipediaArticle(
                page_id=str(source.get('page_id', '')),
                title=source.get('title', ''),
                long_summary=source.get('long_summary'),
                short_summary=source.get('short_summary'),
                city=source.get('city'),
                state=source.get('state'),
                url=source.get('url', ''),
                score=hit.get('_score', 0.0)
            )
            articles.append(article)
        
        return articles
    
    def create_search_result(
        self,
        query: str,
        location_intent: LocationIntent,
        query_body: Dict[str, Any],
        response: Dict[str, Any],
        articles: List[WikipediaArticle],
        execution_time_ms: int
    ) -> WikipediaSearchResult:
        """
        Create a WikipediaSearchResult from search components.
        
        Args:
            query: Original search query
            location_intent: Extracted location information
            query_body: Elasticsearch query used
            response: Elasticsearch response
            articles: List of article results
            execution_time_ms: Query execution time in milliseconds
            
        Returns:
            WikipediaSearchResult instance
        """
        es_features = [
            "Location Extraction - Automatic location understanding from natural language",
            "Geographic Filtering - Apply city/state/neighborhood filters",
            "Multi-Match Query - Search across title, summary, and content fields",
            "Field Boosting - Prioritize title matches over content"
        ]
        
        if location_intent.has_location:
            location_info = f"Extracted Location - City: {location_intent.city}, State: {location_intent.state}"
        else:
            location_info = "No location extracted"
        
        es_features.append(location_info)
        
        return WikipediaSearchResult(
            query_name=f"Wikipedia Location Search: '{query}'",
            query_description="Location-aware Wikipedia search with automatic extraction",
            execution_time_ms=execution_time_ms,
            total_hits=response['hits']['total']['value'],
            returned_hits=len(articles),
            query_dsl=query_body,
            results=articles,
            es_features=es_features,
            indexes_used=["wikipedia index - Enriched Wikipedia articles"]
        )
    
    def search(
        self,
        query: str,
        size: int = DEFAULT_SEARCH_SIZE
    ) -> WikipediaSearchResult:
        """
        Execute a location-aware Wikipedia search.
        
        Args:
            query: Natural language search query
            size: Maximum number of results to return
            
        Returns:
            WikipediaSearchResult with matching articles
            
        Raises:
            Exception: If the search fails
        """
        start_time = time.time()
        
        # Extract location information
        location_intent = self.location_module(query)
        logger.info(
            f"Location extraction - has_location: {location_intent.has_location}, "
            f"city: {location_intent.city}, state: {location_intent.state}"
        )
        
        # Use cleaned query for search
        search_text = location_intent.cleaned_query
        logger.info(f"Using cleaned query: '{search_text}'")
        
        # Build filters and query
        location_filters = self.build_location_filters(location_intent)
        query_body = self.build_query_body(search_text, location_filters, size)
        
        # Execute search
        try:
            response = self.es_client.search(
                index=WIKIPEDIA_INDEX,
                body=query_body
            )
        except Exception as e:
            logger.error(f"Wikipedia location search failed: {e}")
            raise
        
        # Process results
        articles = self.convert_hits_to_articles(response['hits']['hits'])
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return self.create_search_result(
            query=query,
            location_intent=location_intent,
            query_body=query_body,
            response=response,
            articles=articles,
            execution_time_ms=execution_time_ms
        )


def demo_wikipedia_location_search(
    es_client: Elasticsearch,
    query: str = "Tell me about the Temescal neighborhood in Oakland - what amenities and culture does it offer?",
    size: int = DEFAULT_SEARCH_SIZE
) -> WikipediaSearchResult:
    """
    Wikipedia article search with automatic location extraction.
    
    This function provides a convenient interface for the demo system to perform
    location-aware Wikipedia searches. It automatically extracts location information
    from natural language queries and applies geographic filters.
    
    Examples:
        >>> result = demo_wikipedia_location_search(es_client, "museums in San Francisco")
        # Extracts "San Francisco" and searches for museums
        
        >>> result = demo_wikipedia_location_search(es_client, "Oakland parks and recreation")
        # Extracts "Oakland" and searches for parks and recreation
        
        >>> result = demo_wikipedia_location_search(es_client, "Temescal neighborhood history")
        # Extracts "Temescal" and searches for neighborhood history
    
    Args:
        es_client: Elasticsearch client instance
        query: Natural language search query with optional location information
        size: Maximum number of results to return (default: 10)
        
    Returns:
        WikipediaSearchResult containing location-filtered articles
        
    Raises:
        Exception: If the search operation fails
    """
    searcher = WikipediaLocationSearcher(es_client)
    return searcher.search(query, size)