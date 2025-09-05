"""
Wikipedia search with automatic location extraction for demo queries.

Phase 1 implementation: Direct integration of LocationUnderstandingModule
with Wikipedia search functionality.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from elasticsearch import Elasticsearch

from .result_models import WikipediaSearchResult, WikipediaArticle
from ..hybrid.location import LocationUnderstandingModule, LocationFilterBuilder

logger = logging.getLogger(__name__)


def demo_wikipedia_location_search(
    es_client: Elasticsearch,
    query: str = "Tell me about the Temescal neighborhood in Oakland - what amenities and culture does it offer?",
    size: int = 10
) -> WikipediaSearchResult:
    """
    Wikipedia article search with automatic location extraction.
    
    Automatically extracts location from natural language queries and 
    applies geographic filters to Wikipedia search.
    
    Examples:
        "museums in San Francisco" -> Extracts "San Francisco", searches for museums
        "Oakland parks and recreation" -> Extracts "Oakland", searches for parks
        "Temescal neighborhood history" -> Extracts "Temescal", searches for history
    
    Args:
        es_client: Elasticsearch client
        query: Natural language search query with optional location
        size: Number of results
        
    Returns:
        WikipediaSearchResult with location-filtered articles
    """
    start_time = time.time()
    
    # Initialize location extraction
    location_module = LocationUnderstandingModule()
    filter_builder = LocationFilterBuilder()
    
    # Extract location from query
    location_intent = location_module(query)
    logger.info(f"Location extraction - has_location: {location_intent.has_location}, "
               f"city: {location_intent.city}, state: {location_intent.state}")
    
    # Use cleaned query for search
    search_text = location_intent.cleaned_query
    logger.info(f"Using cleaned query: '{search_text}'")
    
    # Build location filters
    location_filters = filter_builder.build_filters(location_intent)
    
    # Build Elasticsearch query
    must_clauses = []
    if search_text:
        must_clauses.append({
            "multi_match": {
                "query": search_text,
                "fields": [
                    "title^2",
                    "short_summary^1.5",
                    "long_summary",
                    "categories",
                    "key_topics"
                ],
                "type": "best_fields"
            }
        })
    else:
        must_clauses.append({"match_all": {}})
    
    # Combine with location filters
    query_body = {
        "query": {
            "bool": {
                "must": must_clauses,
                "filter": location_filters if location_filters else []
            }
        },
        "size": size,
        "_source": [
            "page_id", "title", "short_summary", "city", "state",
            "categories", "key_topics", "url"
        ]
    }
    
    # Execute search
    try:
        response = es_client.search(index="wikipedia", body=query_body)
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Convert results
        articles = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            articles.append(WikipediaArticle(
                page_id=str(source.get('page_id', '')),
                title=source.get('title', ''),
                summary=source.get('short_summary', ''),
                city=source.get('city'),
                state=source.get('state'),
                url=source.get('url', ''),
                score=hit['_score']
            ))
        
        return WikipediaSearchResult(
            query_name=f"Wikipedia Location Search: '{query}'",
            query_description=f"Location-aware Wikipedia search with automatic extraction",
            execution_time_ms=execution_time_ms,
            total_hits=response['hits']['total']['value'],
            returned_hits=len(articles),
            query_dsl=query_body,
            results=articles,
            es_features=[
                "Location Extraction - Automatic location understanding from natural language",
                "Geographic Filtering - Apply city/state/neighborhood filters",
                "Multi-Match Query - Search across title, summary, and content fields",
                "Field Boosting - Prioritize title matches over content",
                f"Extracted Location - City: {location_intent.city}, State: {location_intent.state}" if location_intent.has_location else "No location extracted"
            ],
            indexes_used=["wikipedia index - Enriched Wikipedia articles"]
        )
        
    except Exception as e:
        logger.error(f"Wikipedia location search failed: {e}")
        raise