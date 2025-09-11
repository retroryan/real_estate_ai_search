"""MCP tools for neighborhood search."""

from typing import Dict, Any, Optional
from ..fastmcp_compat import Context

from ...search_service.models import NeighborhoodSearchRequest
from ...search_service.neighborhoods import NeighborhoodSearchService
from ..utils.logging import get_request_logger


async def search_neighborhoods(
    context: Context,
    query: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    include_statistics: bool = False,
    include_related_properties: bool = False,
    include_related_wikipedia: bool = False,
    size: int = 10
) -> Dict[str, Any]:
    """Search for neighborhoods and related information.
    
    This tool searches Wikipedia articles categorized as neighborhoods, districts, or communities.
    It can optionally include aggregated property statistics and related entities.
    
    Args:
        query: Optional text query for neighborhood search
        city: Filter by city name
        state: Filter by state name
        include_statistics: Include aggregated property statistics
        include_related_properties: Include related property listings
        include_related_wikipedia: Include related Wikipedia articles
        size: Number of results to return (1-50, default 10)
        
    Returns:
        Dict containing NeighborhoodSearchResponse with neighborhood results and metadata
    """
    # Get request ID safely
    request_id = getattr(context, 'request_id', "unknown")
    logger = get_request_logger(request_id)
    logger.info(f"Neighborhood search: query={query}, city={city}, state={state}")
    
    try:
        # Get neighborhood search service from context
        neighborhood_search_service: NeighborhoodSearchService = context.get("neighborhood_search_service")
        if not neighborhood_search_service:
            raise ValueError("Neighborhood search service not available")
        
        # Create search request
        request = NeighborhoodSearchRequest(
            query=query,
            city=city,
            state=state,
            include_statistics=include_statistics,
            include_related_properties=include_related_properties,
            include_related_wikipedia=include_related_wikipedia,
            size=min(size, 50)  # Cap at 50
        )
        
        # Execute search
        response = neighborhood_search_service.search(request)
        
        # Return search_service response directly as dict
        return response.model_dump()
        
    except Exception as e:
        logger.error(f"Neighborhood search failed: {e}")
        return {
            "error": str(e),
            "query": query,
            "city": city,
            "state": state
        }


async def search_neighborhoods_by_location(
    context: Context,
    city: str,
    state: Optional[str] = None,
    include_statistics: bool = True,
    size: int = 10
) -> Dict[str, Any]:
    """Search for neighborhoods in a specific city with property statistics.
    
    This is a convenience function for location-based neighborhood searches.
    It automatically includes property statistics for the discovered neighborhoods.
    
    Args:
        city: City name to search in (required)
        state: Optional state filter for disambiguation
        include_statistics: Include property statistics (default true)
        size: Number of results to return (1-20, default 10)
        
    Returns:
        Dict containing NeighborhoodSearchResponse with neighborhood results and statistics
    """
    # Get request ID safely
    request_id = getattr(context, 'request_id', "unknown")
    logger = get_request_logger(request_id)
    logger.info(f"Location-based neighborhood search: {city}, {state}")
    
    try:
        # Get neighborhood search service from context
        neighborhood_search_service: NeighborhoodSearchService = context.get("neighborhood_search_service")
        if not neighborhood_search_service:
            raise ValueError("Neighborhood search service not available")
        
        # Create search request with statistics enabled
        request = NeighborhoodSearchRequest(
            city=city,
            state=state,
            include_statistics=include_statistics,
            include_related_properties=True,  # Include sample properties
            size=min(size, 20)  # Cap at 20
        )
        
        # Execute search
        response = neighborhood_search_service.search(request)
        
        # Return search_service response directly as dict
        return response.model_dump()
        
    except Exception as e:
        logger.error(f"Location-based neighborhood search failed: {e}")
        return {
            "error": str(e),
            "city": city,
            "state": state
        }