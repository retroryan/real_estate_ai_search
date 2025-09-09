"""MCP tools for property search."""

from typing import Dict, Any, Optional, List
from fastmcp import Context

from ...search_service.models import PropertySearchRequest, PropertyFilter
from ...search_service.properties import PropertySearchService
from ..utils.logging import get_request_logger
from ...indexer.enums import IndexName


async def search_properties(
    context: Context,
    query: str,
    property_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_bedrooms: Optional[int] = None,
    max_bedrooms: Optional[int] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    size: int = 20,
    search_type: str = "hybrid"
) -> Dict[str, Any]:
    """Search for properties using natural language queries.
    
    This tool enables semantic search across property listings, combining natural language
    understanding with structured filters to find relevant properties.
    
    Args:
        query: Natural language description of desired property (e.g., "modern home with pool")
        property_type: Filter by property type (House, Condo, Townhouse, etc.)
        min_price: Minimum price filter
        max_price: Maximum price filter
        min_bedrooms: Minimum number of bedrooms
        max_bedrooms: Maximum number of bedrooms
        city: Filter by city name
        state: Filter by state (2-letter code)
        size: Number of results to return (1-100, default 20)
        search_type: Search mode - "hybrid" (default), "semantic", or "text"
        
    Returns:
        Search results with property details and metadata
    """
    # Get request ID safely without hasattr
    request_id = getattr(context, 'request_id', "unknown")
    logger = get_request_logger(request_id)
    logger.info(f"Property search: {query}")
    
    try:
        # Get services from context
        property_search_service: PropertySearchService = context.get("property_search_service")
        if not property_search_service:
            raise ValueError("Property search service not available")
        
        # Build filters if provided
        filters = None
        if any([property_type, min_price, max_price, min_bedrooms, max_bedrooms, city, state]):
            filters = PropertyFilter(
                property_type=property_type,
                min_price=min_price,
                max_price=max_price,
                min_bedrooms=min_bedrooms,
                max_bedrooms=max_bedrooms,
                city=city,
                state=state
            )
        
        # Create search request
        request = PropertySearchRequest(
            query=query,
            filters=filters,
            size=min(size, 100),  # Cap at 100
            include_highlights=True
        )
        
        # Execute search
        response = property_search_service.search(request)
        
        # Return search_service response directly as dict
        return response.model_dump()
        
    except Exception as e:
        logger.error(f"Property search failed: {e}")
        # Return error in search_service format
        from ...search_service.models import SearchError
        error = SearchError(
            error_type="SEARCH_FAILED",
            message=str(e),
            details={"query": query, "search_type": search_type}
        )
        return {"error": error.model_dump()}


async def get_property_details(
    context: Context,
    listing_id: str
) -> Dict[str, Any]:
    """Get detailed information for a specific property.
    
    Args:
        listing_id: Unique property listing ID
        
    Returns:
        Complete property details
    """
    # Get request ID safely without hasattr
    request_id = getattr(context, 'request_id', "unknown")
    logger = get_request_logger(request_id)
    logger.info(f"Getting property details: {listing_id}")
    
    try:
        # Get services from context
        es_client = context.get("es_client")
        config = context.get("config")
        
        if not es_client or not config:
            raise ValueError("Required services not available")
        
        # Get property document
        property_doc = es_client.get_document(
            index=IndexName.PROPERTIES,
            doc_id=listing_id
        )
        
        if not property_doc:
            return {
                "error": f"Property not found: {listing_id}",
                "listing_id": listing_id
            }
        
        return {
            "listing_id": listing_id,
            "property": property_doc
        }
        
    except Exception as e:
        logger.error(f"Failed to get property details: {e}")
        return {
            "error": str(e),
            "listing_id": listing_id
        }


async def get_rich_property_details(
    context: Context,
    listing_id: str,
    include_wikipedia: bool = True,
    include_neighborhood: bool = True,
    wikipedia_limit: int = 3
) -> Dict[str, Any]:
    """Get comprehensive property details.
    
    Returns property with optional neighborhood and Wikipedia data.
    
    Args:
        listing_id: Unique property listing ID
        include_wikipedia: Include Wikipedia articles in response
        include_neighborhood: Include neighborhood information in response
        wikipedia_limit: Maximum number of Wikipedia articles to return (default 3)
        
    Returns:
        Property details with optional enrichments
    """
    # Get request ID safely without hasattr
    request_id = getattr(context, 'request_id', "unknown")
    logger = get_request_logger(request_id)
    logger.info(f"Getting rich property details: {listing_id}")
    
    try:
        # Get services from context
        es_client = context.get("es_client")
        config = context.get("config")
        
        if not es_client or not config:
            raise ValueError("Required services not available")
        
        # Get property document
        property_doc = es_client.get_document(
            index=IndexName.PROPERTIES,
            doc_id=listing_id
        )
        
        if not property_doc:
            return {
                "error": f"Property not found: {listing_id}",
                "listing_id": listing_id
            }
        
        # Start with base property data
        result = {
            "listing_id": listing_id,
            "property": property_doc,
            "source_index": IndexName.PROPERTIES
        }
        
        # Add neighborhood data if requested
        if include_neighborhood and property_doc.get("neighborhood_id"):
            neighborhood_doc = es_client.get_document(
                index=IndexName.NEIGHBORHOODS,
                doc_id=property_doc["neighborhood_id"]
            )
            if neighborhood_doc:
                result["property"]["neighborhood"] = neighborhood_doc
        
        # Add Wikipedia articles if requested
        if include_wikipedia:
            # Get city from property for Wikipedia search
            city = property_doc.get("address", {}).get("city")
            if city:
                # Search for related Wikipedia articles
                from ...search_service.wikipedia import WikipediaSearchService
                from ...search_service.models import WikipediaSearchRequest, WikipediaSearchType
                
                wiki_service = WikipediaSearchService(es_client.client)
                wiki_request = WikipediaSearchRequest(
                    query=f"{city} {property_doc.get('neighborhood_name', '')}",
                    search_type=WikipediaSearchType.FULL_TEXT,
                    size=wikipedia_limit
                )
                wiki_response = wiki_service.search(wiki_request)
                
                if wiki_response.results:
                    wikipedia_articles = []
                    for article in wiki_response.results:
                        wikipedia_articles.append({
                            "page_id": article.page_id,
                            "title": article.title,
                            "url": article.url,
                            "summary": article.long_summary or article.short_summary or "",
                            "relationship_type": "location",
                            "confidence": article.score / 10.0 if article.score else 0.5
                        })
                    result["property"]["wikipedia_articles"] = wikipedia_articles
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get rich property details: {e}")
        return {
            "error": str(e),
            "listing_id": listing_id
        }