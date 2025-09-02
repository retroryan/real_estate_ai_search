"""MCP tools for Wikipedia search."""

from typing import Dict, Any, Optional, List
from fastmcp import Context

from ..models.search import WikipediaSearchRequest
from ..services.wikipedia_search import WikipediaSearchService
from ..utils.logging import get_request_logger


async def search_wikipedia(
    context: Context,
    query: str,
    search_in: str = "full",
    city: Optional[str] = None,
    state: Optional[str] = None,
    categories: Optional[List[str]] = None,
    size: int = 10,
    search_type: str = "hybrid"
) -> Dict[str, Any]:
    """Search Wikipedia articles for location and topic information.
    
    This tool enables semantic search across Wikipedia content to provide rich contextual
    information about locations, landmarks, and topics relevant to real estate searches.
    
    Args:
        query: Natural language query (e.g., "Golden Gate Bridge history", "Mission District culture")
        search_in: What to search - "full" (complete articles), "summaries", or "chunks"
        city: Filter by city name
        state: Filter by state (2-letter code)
        categories: Filter by Wikipedia categories
        size: Number of results to return (1-50, default 10)
        search_type: Search mode - "hybrid" (default), "semantic", or "text"
        
    Returns:
        Search results with Wikipedia article information
    """
    # Get request ID safely without hasattr
    request_id = getattr(context, 'request_id', "unknown")
    logger = get_request_logger(request_id)
    logger.info(f"Wikipedia search: {query} in {search_in}")
    
    try:
        # Get services from context
        wikipedia_search_service: WikipediaSearchService = context.get("wikipedia_search_service")
        if not wikipedia_search_service:
            raise ValueError("Wikipedia search service not available")
        
        # Create search request
        request = WikipediaSearchRequest(
            query=query,
            search_in=search_in,
            city=city,
            state=state,
            categories=categories,
            size=min(size, 50),  # Cap at 50
            search_type=search_type,
            include_highlights=True
        )
        
        # Execute search
        response = wikipedia_search_service.search(request)
        
        # Format response for MCP
        articles = []
        for article in response.results:
            article_data = {
                "page_id": article.get("page_id"),
                "title": article.get("title"),
                "entity_type": article.get("entity_type"),
                "score": article.get("_score")
            }
            
            # Add content based on search type
            if search_in == "chunks":
                article_data.update({
                    "chunk_id": article.get("chunk_id"),
                    "chunk_text": article.get("chunk_text", "")[:1000],  # Truncate long chunks
                    "chunk_index": article.get("chunk_index"),
                    "total_chunks": article.get("total_chunks")
                })
            else:
                article_data.update({
                    "short_summary": article.get("short_summary", "")[:500],
                    "long_summary": article.get("long_summary", "")[:1000] if article.get("long_summary") else None,
                    "key_topics": article.get("key_topics", []),
                    "categories": article.get("categories", [])
                })
            
            # Add location info if available
            if article.get("city"):
                article_data["location"] = {
                    "city": article.get("city"),
                    "state": article.get("state"),
                    "coordinates": {
                        "lat": article.get("latitude"),
                        "lon": article.get("longitude")
                    } if article.get("latitude") and article.get("longitude") else None
                }
            
            # Add highlights if available
            if article.get("_highlights"):
                article_data["highlights"] = article["_highlights"]
            
            articles.append(article_data)
        
        return {
            "query": query,
            "search_in": search_in,
            "search_type": search_type,
            "total_results": response.metadata.total_hits,
            "returned_results": response.metadata.returned_hits,
            "execution_time_ms": response.metadata.execution_time_ms,
            "articles": articles
        }
        
    except Exception as e:
        logger.error(f"Wikipedia search failed: {e}")
        return {
            "error": str(e),
            "query": query,
            "search_in": search_in,
            "search_type": search_type
        }


async def get_wikipedia_article(
    context: Context,
    page_id: str
) -> Dict[str, Any]:
    """Get complete Wikipedia article details.
    
    Args:
        page_id: Wikipedia page ID
        
    Returns:
        Complete Wikipedia article information
    """
    # Get request ID safely without hasattr
    request_id = getattr(context, 'request_id', "unknown")
    logger = get_request_logger(request_id)
    logger.info(f"Getting Wikipedia article: {page_id}")
    
    try:
        # Get services from context
        es_client = context.get("es_client")
        config = context.get("config")
        
        if not es_client or not config:
            raise ValueError("Required services not available")
        
        # Try to get from main Wikipedia index
        article_doc = es_client.get_document(
            index="wikipedia",
            doc_id=page_id
        )
        
        if not article_doc:
            return {
                "error": f"Wikipedia article not found: {page_id}",
                "page_id": page_id
            }
        
        # Format article data
        article_data = {
            "page_id": page_id,
            "title": article_doc.get("title"),
            "url": article_doc.get("url"),
            "short_summary": article_doc.get("short_summary"),
            "long_summary": article_doc.get("long_summary"),
            "key_topics": article_doc.get("key_topics", []),
            "categories": article_doc.get("categories", []),
            "content_loaded": article_doc.get("content_loaded", False),
            "location": {
                "city": article_doc.get("city"),
                "state": article_doc.get("state"),
                "coordinates": {
                    "lat": article_doc.get("latitude"),
                    "lon": article_doc.get("longitude")
                } if article_doc.get("latitude") and article_doc.get("longitude") else None
            } if article_doc.get("city") else None
        }
        
        # Include full content if it's loaded and not too long
        if article_doc.get("content_loaded") and article_doc.get("full_content"):
            content = article_doc.get("full_content", "")
            if len(content) <= 10000:  # Include full content if reasonable length
                article_data["full_content"] = content
            else:
                article_data["content_preview"] = content[:2000] + "..."
                article_data["content_length"] = len(content)
        
        return article_data
        
    except Exception as e:
        logger.error(f"Failed to get Wikipedia article: {e}")
        return {
            "error": str(e),
            "page_id": page_id
        }


async def search_wikipedia_by_location(
    context: Context,
    city: str,
    state: Optional[str] = None,
    query: Optional[str] = None,
    size: int = 10
) -> Dict[str, Any]:
    """Search Wikipedia articles by location.
    
    Find Wikipedia articles related to a specific geographic location, useful for
    understanding neighborhood context, local attractions, and area information.
    
    Args:
        city: City name to search for
        state: Optional state filter (2-letter code)
        query: Optional additional search terms
        size: Number of results to return (1-20, default 10)
        
    Returns:
        Wikipedia articles related to the specified location
    """
    # Get request ID safely without hasattr
    request_id = getattr(context, 'request_id', "unknown")
    logger = get_request_logger(request_id)
    logger.info(f"Location-based Wikipedia search: {city}, {state}")
    
    try:
        # Get services from context
        wikipedia_search_service: WikipediaSearchService = context.get("wikipedia_search_service")
        if not wikipedia_search_service:
            raise ValueError("Wikipedia search service not available")
        
        # Build search query
        if query:
            search_query = f"{query} {city}"
        else:
            search_query = f"{city} landmarks attractions neighborhoods history"
        
        # Create search request
        request = WikipediaSearchRequest(
            query=search_query,
            search_in="full",
            city=city,
            state=state,
            size=min(size, 20),
            search_type="hybrid",
            include_highlights=True
        )
        
        # Execute search
        response = wikipedia_search_service.search(request)
        
        # Format response focusing on location relevance
        articles = []
        for article in response.results:
            article_data = {
                "page_id": article.get("page_id"),
                "title": article.get("title"),
                "short_summary": article.get("short_summary", "")[:300],
                "location_match": {
                    "city": article.get("city"),
                    "state": article.get("state"),
                    "coordinates": {
                        "lat": article.get("latitude"),
                        "lon": article.get("longitude")
                    } if article.get("latitude") and article.get("longitude") else None
                },
                "key_topics": article.get("key_topics", [])[:10],  # Limit topics
                "score": article.get("_score"),
                "highlights": article.get("_highlights", {})
            }
            articles.append(article_data)
        
        return {
            "location": {"city": city, "state": state},
            "search_query": search_query,
            "total_results": response.metadata.total_hits,
            "returned_results": response.metadata.returned_hits,
            "execution_time_ms": response.metadata.execution_time_ms,
            "articles": articles
        }
        
    except Exception as e:
        logger.error(f"Location-based Wikipedia search failed: {e}")
        return {
            "error": str(e),
            "location": {"city": city, "state": state}
        }