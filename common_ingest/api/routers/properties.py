"""
Property and neighborhood API endpoints.

Provides REST endpoints for loading and filtering property and neighborhood data
with pagination, city filtering, and optional embedding inclusion.
"""

import math
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Path, Request
from fastapi.responses import JSONResponse

from ...utils.logger import setup_logger
from ..dependencies import PropertyServiceDep, NeighborhoodServiceDep
from ..schemas.requests import PropertyFilter, NeighborhoodFilter, PaginationParams
from ..schemas.responses import (
    PropertyListResponse,
    NeighborhoodListResponse,
    PropertyResponse,
    NeighborhoodResponse,
    ResponseMetadata,
    ResponseLinks
)

logger = setup_logger(__name__)
router = APIRouter()


def _build_pagination_links(
    request: Request,
    page: int,
    total_pages: int,
    base_path: str,
    query_params: dict
) -> ResponseLinks:
    """
    Build pagination navigation links.
    
    Args:
        request: FastAPI request object
        page: Current page number
        total_pages: Total number of pages
        base_path: Base URL path for the endpoint
        query_params: Query parameters to preserve in links
        
    Returns:
        ResponseLinks: Navigation links for pagination
    """
    base_url = f"{request.url.scheme}://{request.url.netloc}{base_path}"
    
    # Build query string
    def build_url(page_num: int) -> str:
        params = {**query_params, "page": page_num}
        query_string = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        return f"{base_url}?{query_string}" if query_string else base_url
    
    return ResponseLinks(
        self=build_url(page),
        first=build_url(1),
        last=build_url(total_pages),
        next=build_url(page + 1) if page < total_pages else None,
        previous=build_url(page - 1) if page > 1 else None
    )


@router.get("/properties", response_model=PropertyListResponse)
async def get_properties(
    request: Request,
    property_service: PropertyServiceDep,
    city: Optional[str] = Query(None, description="Filter by city name (case-insensitive)"),
    include_embeddings: bool = Query(False, description="Include embedding data in response"),
    page: int = Query(1, ge=1, le=1000, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=500, description="Number of items per page")
):
    """
    Load properties with optional city filtering and pagination.
    
    This endpoint loads enriched property data with automatic address normalization,
    feature deduplication, and property type mapping. Supports city-based filtering
    and optional embedding data inclusion.
    
    - **city**: Filter by city name (e.g., "San Francisco", "Park City")
    - **include_embeddings**: Include vector embedding data in response
    - **page**: Page number for pagination (1-based)
    - **page_size**: Number of items per page (max 500)
    """
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.info(
        f"Loading properties - city: {city}, include_embeddings: {include_embeddings}, "
        f"page: {page}, page_size: {page_size}",
        extra={"correlation_id": correlation_id}
    )
    
    try:
        # Use service to get paginated properties
        paginated_properties, total_count, total_pages = property_service.get_properties(
            city=city,
            page=page,
            page_size=page_size,
            correlation_id=correlation_id
        )
        
        # TODO: Handle include_embeddings when embedding integration is implemented
        if include_embeddings:
            logger.warning(
                "Embedding inclusion requested but not yet implemented",
                extra={"correlation_id": correlation_id}
            )
        
        # Build response metadata
        metadata = ResponseMetadata(
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
        
        # Build pagination links
        query_params = {"city": city, "include_embeddings": include_embeddings, "page_size": page_size}
        links = _build_pagination_links(request, page, total_pages, "/api/v1/properties", query_params)
        
        logger.info(
            f"Loaded {len(paginated_properties)} properties (page {page}/{total_pages})",
            extra={"correlation_id": correlation_id}
        )
        
        return PropertyListResponse(
            data=paginated_properties,
            metadata=metadata,
            links=links
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404 for invalid page)
        raise
    except Exception as e:
        logger.error(
            f"Failed to load properties: {str(e)}",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to load properties"
        )


@router.get("/properties/{property_id}", response_model=PropertyResponse)
async def get_property(
    request: Request,
    property_service: PropertyServiceDep,
    property_id: str = Path(..., description="Property listing ID")
):
    """
    Get a single property by its listing ID.
    
    Returns detailed information for a specific property including all enriched data.
    
    - **property_id**: The property listing ID (e.g., "prop-oak-125")
    """
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.info(
        f"Loading property: {property_id}",
        extra={"correlation_id": correlation_id}
    )
    
    try:
        # Use service to get property by ID
        property_data = property_service.get_property_by_id(
            property_id=property_id,
            correlation_id=correlation_id
        )
        
        if not property_data:
            raise HTTPException(
                status_code=404,
                detail=f"Property '{property_id}' not found"
            )
        
        logger.info(
            f"Found property: {property_id}",
            extra={"correlation_id": correlation_id}
        )
        
        return PropertyResponse(
            data=property_data,
            metadata={
                "property_id": property_id,
                "city": property_data.address.city,
                "state": property_data.address.state
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to load property {property_id}: {str(e)}",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to load property"
        )


@router.get("/neighborhoods", response_model=NeighborhoodListResponse)
async def get_neighborhoods(
    request: Request,
    neighborhood_service: NeighborhoodServiceDep,
    city: Optional[str] = Query(None, description="Filter by city name (case-insensitive)"),
    include_embeddings: bool = Query(False, description="Include embedding data in response"),
    page: int = Query(1, ge=1, le=1000, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=500, description="Number of items per page")
):
    """
    Load neighborhoods with optional city filtering and pagination.
    
    This endpoint loads enriched neighborhood data with automatic city/state expansion,
    characteristic normalization, and geographic data processing.
    
    - **city**: Filter by city name (e.g., "San Francisco", "Park City")
    - **include_embeddings**: Include vector embedding data in response
    - **page**: Page number for pagination (1-based)
    - **page_size**: Number of items per page (max 500)
    """
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.info(
        f"Loading neighborhoods - city: {city}, include_embeddings: {include_embeddings}, "
        f"page: {page}, page_size: {page_size}",
        extra={"correlation_id": correlation_id}
    )
    
    try:
        # Use service to get paginated neighborhoods
        paginated_neighborhoods, total_count, total_pages = neighborhood_service.get_neighborhoods(
            city=city,
            page=page,
            page_size=page_size,
            correlation_id=correlation_id
        )
        
        # TODO: Handle include_embeddings when embedding integration is implemented
        if include_embeddings:
            logger.warning(
                "Embedding inclusion requested but not yet implemented",
                extra={"correlation_id": correlation_id}
            )
        
        # Build response metadata
        metadata = ResponseMetadata(
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
        
        # Build pagination links
        query_params = {"city": city, "include_embeddings": include_embeddings, "page_size": page_size}
        links = _build_pagination_links(request, page, total_pages, "/api/v1/neighborhoods", query_params)
        
        logger.info(
            f"Loaded {len(paginated_neighborhoods)} neighborhoods (page {page}/{total_pages})",
            extra={"correlation_id": correlation_id}
        )
        
        return NeighborhoodListResponse(
            data=paginated_neighborhoods,
            metadata=metadata,
            links=links
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404 for invalid page)
        raise
    except Exception as e:
        logger.error(
            f"Failed to load neighborhoods: {str(e)}",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to load neighborhoods"
        )


@router.get("/neighborhoods/{neighborhood_id}", response_model=NeighborhoodResponse)
async def get_neighborhood(
    request: Request,
    neighborhood_service: NeighborhoodServiceDep,
    neighborhood_id: str = Path(..., description="Neighborhood ID")
):
    """
    Get a single neighborhood by its ID.
    
    Returns detailed information for a specific neighborhood including all enriched data.
    
    - **neighborhood_id**: The neighborhood ID (e.g., "sf-pac-heights-001")
    """
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.info(
        f"Loading neighborhood: {neighborhood_id}",
        extra={"correlation_id": correlation_id}
    )
    
    try:
        # Use service to get neighborhood by ID
        neighborhood_data = neighborhood_service.get_neighborhood_by_id(
            neighborhood_id=neighborhood_id,
            correlation_id=correlation_id
        )
        
        if not neighborhood_data:
            raise HTTPException(
                status_code=404,
                detail=f"Neighborhood '{neighborhood_id}' not found"
            )
        
        logger.info(
            f"Found neighborhood: {neighborhood_id}",
            extra={"correlation_id": correlation_id}
        )
        
        return NeighborhoodResponse(
            data=neighborhood_data,
            metadata={
                "neighborhood_id": neighborhood_id,
                "city": neighborhood_data.city,
                "state": neighborhood_data.state
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to load neighborhood {neighborhood_id}: {str(e)}",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to load neighborhood"
        )