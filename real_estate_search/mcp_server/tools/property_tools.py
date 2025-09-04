"""MCP tools for property search."""

from typing import Dict, Any, Optional
from fastmcp import Context

from ..models.search import PropertySearchRequest, PropertyFilter
from ..services.property_search import PropertySearchService
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
            search_type=search_type,
            include_highlights=True,
            include_aggregations=False
        )
        
        # Execute search
        response = property_search_service.search(request)
        
        # Format response for MCP
        return {
            "query": query,
            "search_type": search_type,
            "total_results": response.metadata.total_hits,
            "returned_results": response.metadata.returned_hits,
            "execution_time_ms": response.metadata.execution_time_ms,
            "properties": [
                {
                    "listing_id": prop.get("listing_id"),
                    "property_type": prop.get("property_type"),
                    "price": prop.get("price"),
                    "bedrooms": prop.get("bedrooms"),
                    "bathrooms": prop.get("bathrooms"),
                    "square_feet": prop.get("square_feet"),
                    "description": prop.get("description", "")[:500],  # Truncate long descriptions
                    "address": {
                        "street": prop.get("address", {}).get("street"),
                        "city": prop.get("address", {}).get("city"),
                        "state": prop.get("address", {}).get("state"),
                        "zip_code": prop.get("address", {}).get("zip_code")
                    },
                    "neighborhood": prop.get("neighborhood", {}).get("name") if prop.get("neighborhood") else None,
                    "features": prop.get("features", []),
                    "amenities": prop.get("amenities", []),
                    "score": prop.get("_score"),
                    "highlights": prop.get("_highlights", {})
                }
                for prop in response.results
            ]
        }
        
    except Exception as e:
        logger.error(f"Property search failed: {e}")
        # Return standardized error response with required fields
        return {
            "query": query,
            "search_type": search_type,
            "total_results": 0,
            "returned_results": 0,
            "execution_time_ms": 0,
            "properties": [],
            "error": str(e)
        }


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
    """Get comprehensive property details from denormalized property_relationships index.
    
    Returns complete property information including embedded neighborhood data 
    and Wikipedia articles in a single high-performance query.
    
    Args:
        listing_id: Unique property listing ID
        include_wikipedia: Include Wikipedia articles in response
        include_neighborhood: Include neighborhood information in response
        wikipedia_limit: Maximum number of Wikipedia articles to return (default 3)
        
    Returns:
        Rich property details with all embedded data
    """
    # Get request ID safely without hasattr
    request_id = getattr(context, 'request_id', "unknown")
    logger = get_request_logger(request_id)
    logger.info(f"Getting rich property details: {listing_id}")
    
    try:
        # Get services from context
        property_search_service: PropertySearchService = context.get("property_search_service")
        if not property_search_service:
            raise ValueError("Property search service not available")
        
        # Get rich property details
        property_data = property_search_service.get_rich_property_details(
            listing_id=listing_id,
            include_wikipedia=include_wikipedia,
            include_neighborhood=include_neighborhood,
            wikipedia_limit=wikipedia_limit
        )
        
        if not property_data:
            return {
                "error": f"Property not found: {listing_id}",
                "listing_id": listing_id
            }
        
        # Return the rich property data
        return {
            "listing_id": listing_id,
            "property": property_data,
            "source_index": "property_relationships"
        }
        
    except Exception as e:
        logger.error(f"Failed to get rich property details: {e}")
        return {
            "error": str(e),
            "listing_id": listing_id
        }