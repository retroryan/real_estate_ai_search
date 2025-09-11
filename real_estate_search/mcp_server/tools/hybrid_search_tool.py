"""MCP tool for natural language property search using hybrid search engine."""

from typing import Dict, Any
from ..fastmcp_compat import Context
from ...search_service.elasticsearch_compat import Elasticsearch

from ...hybrid import HybridSearchEngine
from ...search_service.models import (
    PropertySearchResponse,
    PropertyResult,
    PropertyAddress,
    SearchError
)
from ..utils.logging import get_request_logger


async def search_properties_hybrid(
    context: Context,
    query: str,
    size: int = 10,
    include_location_extraction: bool = False
) -> Dict[str, Any]:
    """Search properties using natural language with AI understanding.
    
    This tool uses the HybridSearchEngine to:
    - Extract location information from natural language queries
    - Generate semantic embeddings for conceptual matching
    - Combine text and vector search with RRF
    - Apply location filters efficiently during search
    
    Args:
        query: Natural language search query
        size: Number of results to return (1-100, default 10)
        include_location_extraction: Include location extraction details in response
        
    Returns:
        Search results with property details and optional location metadata
    """
    # Get request ID for logging
    request_id = getattr(context, 'request_id', "unknown")
    logger = get_request_logger(request_id)
    logger.info(f"Natural language property search: {query}")
    
    try:
        # Get Elasticsearch client from context - note: this is the ElasticsearchClient wrapper
        es_client_wrapper = context.get("es_client")
        if not es_client_wrapper:
            raise ValueError("Elasticsearch client not available")
        
        # Get the actual Elasticsearch client from the wrapper
        es_client: Elasticsearch = es_client_wrapper.client
        
        # Get config from context
        config = context.get("config")
        
        # Initialize hybrid search engine (it will load its own AppConfig if config is None)
        hybrid_engine = HybridSearchEngine(es_client, None)
        
        # Execute location-aware search
        hybrid_result = hybrid_engine.search_with_location(
            query=query,
            size=min(size, 100)  # Cap at 100
        )
        
        # Transform to PropertySearchResponse format
        property_results = []
        for search_result in hybrid_result.results:
            # Extract property data
            property_data = search_result.property_data
            
            # Build PropertyAddress
            address_data = property_data.get("address", {})
            address = PropertyAddress(
                street=address_data.get("street", ""),
                city=address_data.get("city", ""),
                state=address_data.get("state", ""),
                zip_code=address_data.get("zip_code", "")
            )
            
            # Build PropertyResult
            result = PropertyResult(
                listing_id=property_data.get("listing_id", ""),
                property_type=property_data.get("property_type", ""),
                price=property_data.get("price", 0),
                bedrooms=property_data.get("bedrooms", 0),
                bathrooms=property_data.get("bathrooms", 0),
                square_feet=property_data.get("square_feet", 0),
                address=address,
                description=property_data.get("description", ""),
                features=property_data.get("features", []),
                score=search_result.hybrid_score
            )
            
            property_results.append(result)
        
        # Build response
        response = PropertySearchResponse(
            results=property_results,
            total_hits=hybrid_result.total_hits,
            execution_time_ms=hybrid_result.execution_time_ms
        )
        
        # Convert to dict for MCP response
        response_dict = response.model_dump()
        
        # Add location extraction metadata if requested
        if include_location_extraction and hybrid_result.location_intent:
            location_intent = hybrid_result.location_intent
            response_dict["location_extraction"] = {
                "extracted": location_intent.has_location,
                "city": location_intent.city,
                "state": location_intent.state,
                "neighborhood": location_intent.neighborhood,
                "zip_code": location_intent.zip_code,
                "cleaned_query": location_intent.cleaned_query,
                "confidence": location_intent.confidence
            }
        
        # Add search metadata
        response_dict["search_metadata"] = {
            "search_type": "hybrid_with_location",
            "rrf_used": True,
            "location_extracted": hybrid_result.location_intent.has_location if hybrid_result.location_intent else False
        }
        
        return response_dict
        
    except Exception as e:
        logger.error(f"Natural language property search failed: {e}")
        # Return error in search_service format
        error = SearchError(
            error_type="SEARCH_FAILED",
            message=str(e),
            details={"query": query, "search_type": "hybrid_with_location"}
        )
        return {"error": error.model_dump()}