"""
FastAPI application for Property Search API.
Clean, type-safe REST API implementation.
"""

import time
import uuid
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Path, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from ..config.settings import Settings
from ..search.search_engine import PropertySearchEngine
from ..search.models import SearchRequest, SearchFilters, GeoSearchParams, GeoPoint
from ..search.exceptions import SearchError, QueryValidationError
from .models import (
    SearchRequestAPI,
    GeoSearchRequestAPI,
    SearchResponseAPI,
    PropertySummary,
    PropertyDetail,
    SimilarPropertiesRequest,
    ErrorResponse,
    ErrorDetail,
    HealthStatus,
    SearchFiltersRequest
)
from .dependencies import get_search_engine, get_settings, get_request_id


logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.
    Initialize resources on startup, cleanup on shutdown.
    """
    # Startup
    logger.info("Starting Property Search API")
    settings = Settings.load()
    app.state.settings = settings
    app.state.search_engine = PropertySearchEngine(settings)
    
    # Test Elasticsearch connection
    try:
        if app.state.search_engine.es.ping():
            logger.info("Connected to Elasticsearch")
        else:
            logger.error("Failed to connect to Elasticsearch")
    except Exception as e:
        logger.error(f"Elasticsearch connection error: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Property Search API")
    if hasattr(app.state, 'search_engine'):
        app.state.search_engine.close()


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Args:
        settings: Optional settings override
        
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Property Search API",
        description="RESTful API for searching real estate properties",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom exception handlers
    @app.exception_handler(SearchError)
    async def search_error_handler(request: Request, exc: SearchError):
        """Handle search errors."""
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=str(exc),
                status_code=500,
                request_id=request.state.request_id if hasattr(request.state, 'request_id') else None,
                errors=[ErrorDetail(
                    code=exc.error_code if hasattr(exc, 'error_code') else "SEARCH_ERROR",
                    message=str(exc)
                )]
            ).model_dump()
        )
    
    @app.exception_handler(QueryValidationError)
    async def query_validation_error_handler(request: Request, exc: QueryValidationError):
        """Handle query validation errors."""
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=str(exc),
                status_code=400,
                request_id=request.state.request_id if hasattr(request.state, 'request_id') else None,
                errors=[ErrorDetail(
                    code="INVALID_QUERY",
                    message=str(exc)
                )]
            ).model_dump()
        )
    
    # Add request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """Add unique request ID to each request."""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        response = await call_next(request)
        process_time = int((time.time() - start_time) * 1000)
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-MS"] = str(process_time)
        
        return response
    
    return app


# Create the FastAPI app
app = create_app()


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/api/health", response_model=HealthStatus)
async def health_check(
    search_engine: PropertySearchEngine = Depends(get_search_engine)
) -> HealthStatus:
    """
    Health check endpoint.
    
    Returns system health status including Elasticsearch connectivity
    and index status.
    """
    try:
        # Check Elasticsearch
        es_health = {}
        es_status = "unhealthy"
        
        if search_engine.es.ping():
            es_status = "healthy"
            info = search_engine.es.info()
            es_health = {
                "status": "connected",
                "cluster_name": info.get('cluster_name'),
                "version": info.get('version', {}).get('number')
            }
        else:
            es_health = {"status": "disconnected"}
        
        # Check index
        index_health = {}
        index_status = "unhealthy"
        
        try:
            alias = search_engine.settings.index.alias
            if search_engine.es.indices.exists_alias(name=alias):
                index_status = "healthy"
                count_response = search_engine.es.count(index=alias)
                index_health = {
                    "status": "available",
                    "alias": alias,
                    "document_count": count_response['count']
                }
            else:
                index_health = {"status": "not_found", "alias": alias}
        except Exception as e:
            index_health = {"status": "error", "error": str(e)}
        
        # Determine overall status
        if es_status == "healthy" and index_status == "healthy":
            overall_status = "healthy"
        elif es_status == "healthy" or index_status == "healthy":
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return HealthStatus(
            status=overall_status,
            elasticsearch=es_health,
            index=index_health,
            metrics={
                "uptime_seconds": int(time.time() - getattr(app.state, 'start_time', time.time()))
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthStatus(
            status="unhealthy",
            elasticsearch={"status": "error", "error": str(e)},
            index={"status": "error"}
        )


@app.post("/api/search", response_model=SearchResponseAPI)
async def search_properties(
    request: SearchRequestAPI,
    search_engine: PropertySearchEngine = Depends(get_search_engine),
    request_id: str = Depends(get_request_id)
) -> SearchResponseAPI:
    """
    Search for properties.
    
    Supports text search, filtered search, and combined text + filter search.
    """
    try:
        start_time = time.time()
        
        # Convert API request to internal search request
        filters = None
        if request.filters:
            filters = SearchFilters(
                min_price=request.filters.min_price,
                max_price=request.filters.max_price,
                min_bedrooms=request.filters.min_bedrooms,
                max_bedrooms=request.filters.max_bedrooms,
                min_bathrooms=request.filters.min_bathrooms,
                max_bathrooms=request.filters.max_bathrooms,
                min_square_feet=request.filters.min_square_feet,
                max_square_feet=request.filters.max_square_feet,
                property_types=request.filters.property_types,
                property_status=request.filters.property_status,
                cities=request.filters.cities,
                neighborhoods=request.filters.neighborhoods,
                zip_codes=request.filters.zip_codes,
                min_year_built=request.filters.min_year_built,
                max_year_built=request.filters.max_year_built,
                listed_within_days=request.filters.listed_within_days,
                required_features=request.filters.required_features,
                required_amenities=request.filters.required_amenities
            )
        
        # Create internal search request
        internal_request = SearchRequest(
            query_type=request.query_type,
            query_text=request.query,
            filters=filters,
            sort_by=request.sort_by,
            page=request.page,
            size=request.size,
            include_aggregations=request.include_aggregations,
            include_highlights=request.include_highlights
        )
        
        # Execute search
        response = search_engine.search(internal_request)
        
        # Convert response to API format
        properties = []
        for i, hit in enumerate(response.hits):
            es_hit = {
                '_source': hit.property.model_dump(),
                '_score': hit.score,
                '_id': hit.doc_id
            }
            if hit.distance is not None:
                es_hit['sort'] = [hit.distance]
            
            properties.append(PropertySummary.from_search_hit(es_hit, hit.doc_id))
        
        # Calculate total pages
        total_pages = max(1, (response.total + request.size - 1) // request.size)
        
        process_time = int((time.time() - start_time) * 1000)
        
        return SearchResponseAPI(
            properties=properties,
            total=response.total,
            page=request.page,
            size=request.size,
            total_pages=total_pages,
            took_ms=response.took_ms,
            aggregations=response.aggregations if request.include_aggregations else None,
            request_id=request_id
        )
        
    except QueryValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SearchError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Search failed: {e}", request_id=request_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/geo-search", response_model=SearchResponseAPI)
async def geo_search(
    request: GeoSearchRequestAPI,
    search_engine: PropertySearchEngine = Depends(get_search_engine),
    request_id: str = Depends(get_request_id)
) -> SearchResponseAPI:
    """
    Search properties within a geographic radius.
    
    Find properties within a specified distance from a center point.
    """
    try:
        # Convert filters
        filters = None
        if request.filters:
            filters = SearchFilters(
                min_price=request.filters.min_price,
                max_price=request.filters.max_price,
                min_bedrooms=request.filters.min_bedrooms,
                max_bedrooms=request.filters.max_bedrooms,
                min_bathrooms=request.filters.min_bathrooms,
                max_bathrooms=request.filters.max_bathrooms,
                min_square_feet=request.filters.min_square_feet,
                max_square_feet=request.filters.max_square_feet,
                property_types=request.filters.property_types,
                property_status=request.filters.property_status,
                cities=request.filters.cities,
                neighborhoods=request.filters.neighborhoods,
                zip_codes=request.filters.zip_codes
            )
        
        # Execute geo search
        response = search_engine.geo_search(
            center_lat=request.latitude,
            center_lon=request.longitude,
            radius=request.radius,
            unit=request.unit.value,
            filters=filters,
            size=request.size * request.page  # Get enough for pagination
        )
        
        # Paginate results
        start_idx = (request.page - 1) * request.size
        end_idx = start_idx + request.size
        paginated_hits = response.hits[start_idx:end_idx]
        
        # Convert to API format
        properties = []
        for hit in paginated_hits:
            es_hit = {
                '_source': hit.property.model_dump(),
                '_score': hit.score,
                '_id': hit.doc_id
            }
            if hit.distance is not None:
                es_hit['sort'] = [hit.distance]
            
            properties.append(PropertySummary.from_search_hit(es_hit, hit.doc_id))
        
        total_pages = max(1, (response.total + request.size - 1) // request.size)
        
        return SearchResponseAPI(
            properties=properties,
            total=response.total,
            page=request.page,
            size=request.size,
            total_pages=total_pages,
            took_ms=response.took_ms,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Geo search failed: {e}", request_id=request_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/properties/{property_id}", response_model=PropertyDetail)
async def get_property(
    property_id: str = Path(..., description="Property document ID"),
    search_engine: PropertySearchEngine = Depends(get_search_engine)
) -> PropertyDetail:
    """
    Get detailed information for a specific property.
    
    Returns full property details including all fields.
    """
    try:
        # Get property from Elasticsearch
        response = search_engine.es.get(
            index=search_engine.settings.index.alias,
            id=property_id
        )
        
        if not response['found']:
            raise HTTPException(status_code=404, detail="Property not found")
        
        return PropertyDetail.from_elasticsearch(response['_source'], property_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get property {property_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/properties/{property_id}/similar", response_model=SearchResponseAPI)
async def find_similar_properties(
    property_id: str = Path(..., description="Property document ID"),
    request: SimilarPropertiesRequest = SimilarPropertiesRequest(),
    search_engine: PropertySearchEngine = Depends(get_search_engine),
    request_id: str = Depends(get_request_id)
) -> SearchResponseAPI:
    """
    Find properties similar to a given property.
    
    Uses Elasticsearch's More Like This query to find similar properties
    based on features, description, and characteristics.
    """
    try:
        # Convert filters if provided
        filters = None
        if request.filters:
            filters = SearchFilters(
                min_price=request.filters.min_price,
                max_price=request.filters.max_price,
                min_bedrooms=request.filters.min_bedrooms,
                max_bedrooms=request.filters.max_bedrooms,
                property_types=request.filters.property_types,
                cities=request.filters.cities
            )
        
        # Create similar properties request
        from ..search.models import SearchRequest
        from ..search.enums import QueryType
        
        internal_request = SearchRequest(
            query_type=QueryType.SIMILAR,
            similar_to_id=property_id,
            filters=filters,
            size=request.max_results,
            include_aggregations=False
        )
        
        # Execute search
        response = search_engine.search(internal_request)
        
        # Filter out source property if requested
        if not request.include_source:
            response.hits = [hit for hit in response.hits if hit.doc_id != property_id]
        
        # Convert to API format
        properties = []
        for hit in response.hits:
            es_hit = {
                '_source': hit.property.model_dump(),
                '_score': hit.score,
                '_id': hit.doc_id
            }
            properties.append(PropertySummary.from_search_hit(es_hit, hit.doc_id))
        
        return SearchResponseAPI(
            properties=properties,
            total=len(properties),
            page=1,
            size=request.max_results,
            total_pages=1,
            took_ms=response.took_ms,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Similar properties search failed: {e}", request_id=request_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/stats")
async def get_statistics(
    search_engine: PropertySearchEngine = Depends(get_search_engine)
) -> Dict[str, Any]:
    """
    Get aggregate statistics about the property market.
    
    Returns market statistics including price ranges, property types,
    and location distributions.
    """
    try:
        # Execute aggregation-only query
        body = {
            "size": 0,
            "aggs": {
                "price_stats": {"stats": {"field": "price"}},
                "sqft_stats": {"stats": {"field": "square_feet"}},
                "property_types": {
                    "terms": {"field": "property_type", "size": 20}
                },
                "cities": {
                    "terms": {"field": "address.city.keyword", "size": 50}
                },
                "price_ranges": {
                    "range": {
                        "field": "price",
                        "ranges": [
                            {"to": 300000, "key": "Under $300k"},
                            {"from": 300000, "to": 500000, "key": "$300k-$500k"},
                            {"from": 500000, "to": 750000, "key": "$500k-$750k"},
                            {"from": 750000, "to": 1000000, "key": "$750k-$1M"},
                            {"from": 1000000, "key": "Over $1M"}
                        ]
                    }
                },
                "bedroom_distribution": {
                    "terms": {"field": "bedrooms", "size": 10}
                }
            }
        }
        
        response = search_engine.es.search(
            index=search_engine.settings.index.alias,
            body=body
        )
        
        return {
            "total_properties": response['hits']['total']['value'],
            "aggregations": response.get('aggregations', {})
        }
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Property Search API",
        "version": "1.0.0",
        "documentation": "/api/docs",
        "health": "/api/health"
    }