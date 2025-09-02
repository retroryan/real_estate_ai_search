"""MCP tool for hybrid property search."""

from typing import Dict, Any, Optional, List
from fastmcp import Context
from pydantic import ValidationError

from ..models.hybrid import (
    HybridSearchRequest, 
    HybridSearchResponse, 
    HybridSearchMetadata, 
    LocationExtractionMetadata, 
    HybridSearchProperty, 
    PropertyAddress
)
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
    # Get request ID safely without hasattr
    request_id = getattr(context, 'request_id', "unknown")
    logger = get_request_logger(request_id)
    logger.info(f"Hybrid property search: {query}")
    
    # Validate input parameters using Pydantic
    request_model = HybridSearchRequest(
        query=query,
        size=size,
        include_location_extraction=include_location_extraction
    )
    
    logger.info(f"Validated request: query length={len(request_model.query)}, size={request_model.size}")
    
    try:
        # Get hybrid search engine from context
        hybrid_search_engine: HybridSearchEngine = context.get("hybrid_search_engine")
        if not hybrid_search_engine:
            raise ValueError("Hybrid search engine service not available")
        
        # Execute hybrid search with location extraction
        logger.info(f"Executing hybrid search: query='{request_model.query}', size={request_model.size}")
        hybrid_result = hybrid_search_engine.search_with_location(request_model.query, request_model.size)
        
        # Format properties for MCP response
        properties: List[HybridSearchProperty] = []
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
            
            property_result = HybridSearchProperty(
                listing_id=result.listing_id,
                property_type=prop_data.get('property_type'),
                address=address,
                price=prop_data.get('price'),
                bedrooms=prop_data.get('bedrooms'),
                bathrooms=prop_data.get('bathrooms'),
                square_feet=prop_data.get('square_feet'),
                description=prop_data.get('description', '')[:500] if prop_data.get('description') else None,  # Truncate long descriptions
                features=prop_data.get('features', []),
                hybrid_score=result.hybrid_score
            )
            properties.append(property_result)
        
        # Build location extraction metadata if requested
        location_metadata: Optional[LocationExtractionMetadata] = None
        if request_model.include_location_extraction and hybrid_result.location_intent:
            location_metadata = LocationExtractionMetadata(
                city=hybrid_result.location_intent.city,
                state=hybrid_result.location_intent.state,
                has_location=hybrid_result.location_intent.has_location,
                cleaned_query=hybrid_result.location_intent.cleaned_query
            )
        
        # Create metadata
        metadata = HybridSearchMetadata(
            query=request_model.query,
            total_hits=hybrid_result.total_hits,
            returned_hits=len(properties),
            execution_time_ms=hybrid_result.execution_time_ms,
            location_extracted=location_metadata
        )
        
        # Create and validate response using Pydantic
        response = HybridSearchResponse(
            results=properties,
            metadata=metadata
        )
        logger.info(f"Search completed successfully: {len(properties)} results in {hybrid_result.execution_time_ms}ms")
        return response.model_dump()
        
    except Exception as e:
        logger.error(f"Hybrid property search failed: {e}")
        raise