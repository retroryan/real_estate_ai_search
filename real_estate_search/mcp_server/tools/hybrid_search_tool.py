"""MCP tool for hybrid property search."""

from typing import Dict, Any, Optional, List
from fastmcp import Context

from ..models.responses import PropertySearchResponse, Property, PropertyAddress
from ..utils.logging import get_request_logger
from ...hybrid import HybridSearchEngine, HybridSearchParams


async def search_properties_hybrid(
    context: Context,
    query: str,
    size: int = 10,
    include_location_extraction: bool = False
) -> Dict[str, Any]:
    """Search for properties using hybrid search with location understanding.
    
    This tool combines semantic vector search, traditional text search, and geographic
    filtering using Elasticsearch's native RRF (Reciprocal Rank Fusion). It automatically
    extracts location information from natural language queries using DSPy.
    
    Args:
        query: Natural language property search query (e.g., "luxury waterfront condo in San Francisco")
        size: Number of results to return (1-50, default 10)  
        include_location_extraction: Include location extraction details in response (default false)
        
    Returns:
        Dict containing HybridSearchResponse with property results and metadata
        
    Raises:
        ValidationError: If input parameters are invalid
        ValueError: If required services are not available
        Exception: For other search execution errors
    """
    # Get request ID safely
    request_id = getattr(context, 'request_id', "unknown")
    logger = get_request_logger(request_id)
    logger.info(f"Hybrid property search: {query}")
    
    try:
        # Get hybrid search engine from context
        hybrid_search_engine: HybridSearchEngine = context.get("hybrid_search_engine")
        if not hybrid_search_engine:
            raise ValueError("Hybrid search engine service not available")
        
        # Execute hybrid search with location extraction
        logger.info(f"Executing hybrid search: query='{query}', size={size}")
        hybrid_result = hybrid_search_engine.search_with_location(query, size)
        
        # Format properties for standard response
        properties: List[Property] = []
        for result in hybrid_result.results:
            # Access property data from SearchResult object
            prop_data = result.property_data
            
            # Extract address components safely
            address_data = prop_data.get('address', {})
            address = PropertyAddress(
                street=address_data.get('street'),
                city=address_data.get('city'),
                state=address_data.get('state'),
                zip_code=address_data.get('zip_code')
            )
            
            property_result = Property(
                listing_id=result.listing_id,
                property_type=prop_data.get('property_type'),
                address=address,
                price=prop_data.get('price'),
                bedrooms=prop_data.get('bedrooms'),
                bathrooms=prop_data.get('bathrooms'),
                square_feet=prop_data.get('square_feet'),
                description=prop_data.get('description', '')[:500] if prop_data.get('description') else None,
                features=prop_data.get('features', []),
                score=result.hybrid_score
            )
            properties.append(property_result)
        
        # Build location extraction if requested
        location_extracted = None
        if include_location_extraction and hybrid_result.location_intent:
            location_extracted = {
                'city': hybrid_result.location_intent.city,
                'state': hybrid_result.location_intent.state,
                'has_location': hybrid_result.location_intent.has_location,
                'cleaned_query': hybrid_result.location_intent.cleaned_query
            }
        
        # Create standard response
        response = PropertySearchResponse(
            properties=properties,
            total_results=hybrid_result.total_hits,
            returned_results=len(properties),
            execution_time_ms=hybrid_result.execution_time_ms,
            query=query,
            location_extracted=location_extracted
        )
        logger.info(f"Search completed successfully: {len(properties)} results in {hybrid_result.execution_time_ms}ms")
        return response.model_dump()
        
    except Exception as e:
        logger.error(f"Hybrid property search failed: {e}")
        raise