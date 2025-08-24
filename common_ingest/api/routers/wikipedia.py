"""
Wikipedia API endpoints.

Provides REST endpoints for loading and filtering Wikipedia articles and summaries
with location-based filtering, confidence thresholds, and sorting options.
"""

import math
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Path as PathParam, Request
from fastapi.responses import JSONResponse

from ...utils.logger import setup_logger
from ..dependencies import WikipediaServiceDep
from ..schemas.requests import WikipediaArticleFilter, WikipediaSummaryFilter, PaginationParams
from ..schemas.responses import (
    WikipediaArticleListResponse,
    WikipediaSummaryListResponse,
    WikipediaArticleResponse,
    WikipediaSummaryResponse,
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
    Build pagination navigation links for Wikipedia endpoints.
    
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
        params = {**query_params, 'page': page_num}
        query_string = '&'.join(f"{k}={v}" for k, v in params.items() if v is not None)
        return f"{base_url}?{query_string}" if query_string else base_url
    
    return ResponseLinks(
        self=build_url(page),
        first=build_url(1),
        last=build_url(total_pages),
        next=build_url(page + 1) if page < total_pages else None,
        previous=build_url(page - 1) if page > 1 else None
    )


@router.get("/articles", response_model=WikipediaArticleListResponse)
async def get_articles(
    request: Request,
    wikipedia_service: WikipediaServiceDep,
    city: Optional[str] = Query(None, min_length=1, max_length=100, description="Filter by city name"),
    state: Optional[str] = Query(None, min_length=1, max_length=100, description="Filter by state name"),
    relevance_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum relevance score"),
    sort_by: str = Query("relevance", pattern="^(relevance|title|page_id)$", description="Sort by relevance, title, or page_id"),
    include_embeddings: bool = Query(False, description="Include embedding data in response"),
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Number of items per page")
):
    """
    Load Wikipedia articles with optional location-based filtering and sorting.
    
    Provides access to enriched Wikipedia articles with location information extracted
    from article content. Supports filtering by city/state and sorting by relevance score.
    
    - **city**: Filter by city name (e.g., "San Francisco", "Park City")
    - **state**: Filter by state name (e.g., "California", "Utah")
    - **relevance_min**: Minimum relevance score threshold (0.0 to 1.0)
    - **sort_by**: Sort articles by relevance (default), title, or page_id
    - **include_embeddings**: Include vector embedding data in response
    - **page**: Page number for pagination (1-based)
    - **page_size**: Number of items per page (max 500)
    """
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.info(
        f"Loading Wikipedia articles - city: {city}, state: {state}, "
        f"relevance_min: {relevance_min}, sort_by: {sort_by}, "
        f"include_embeddings: {include_embeddings}, page: {page}, page_size: {page_size}",
        extra={"correlation_id": correlation_id}
    )
    
    try:
        # Use service to get paginated articles
        paginated_articles, total_count, total_pages = wikipedia_service.get_articles(
            city=city,
            state=state,
            relevance_min=relevance_min,
            sort_by=sort_by,
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
        query_params = {
            'city': city,
            'state': state,
            'relevance_min': relevance_min,
            'sort_by': sort_by,
            'include_embeddings': include_embeddings,
            'page_size': page_size
        }
        links = _build_pagination_links(request, page, total_pages, "/api/v1/wikipedia/articles", query_params)
        
        logger.info(
            f"Loaded {len(paginated_articles)} articles (page {page}/{total_pages})",
            extra={"correlation_id": correlation_id}
        )
        
        return WikipediaArticleListResponse(
            data=paginated_articles,
            metadata=metadata,
            links=links
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404 for invalid page)
        raise
    except Exception as e:
        logger.error(
            f"Failed to load Wikipedia articles: {str(e)}",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to load Wikipedia articles"
        )


@router.get("/articles/{page_id}", response_model=WikipediaArticleResponse)
async def get_article(
    request: Request,
    wikipedia_service: WikipediaServiceDep,
    page_id: int = PathParam(..., description="Wikipedia page ID"),
    include_embeddings: bool = Query(False, description="Include embedding data in response")
):
    """
    Get a single Wikipedia article by its page ID.
    
    Returns detailed information about a specific Wikipedia article including
    location data, relevance score, and full article text.
    
    - **page_id**: Wikipedia page ID (numeric)
    - **include_embeddings**: Include vector embedding data in response
    """
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.info(
        f"Loading Wikipedia article: {page_id}",
        extra={"correlation_id": correlation_id}
    )
    
    try:
        # Use service to get article by ID
        article = wikipedia_service.get_article_by_id(
            page_id=page_id,
            correlation_id=correlation_id
        )
        
        if not article:
            raise HTTPException(
                status_code=404,
                detail=f"Wikipedia article with page_id '{page_id}' not found"
            )
        
        # TODO: Handle include_embeddings when embedding integration is implemented
        if include_embeddings:
            logger.warning(
                "Embedding inclusion requested but not yet implemented",
                extra={"correlation_id": correlation_id}
            )
        
        logger.info(
            f"Found Wikipedia article: {article.title}",
            extra={"correlation_id": correlation_id}
        )
        
        return WikipediaArticleResponse(
            data=article,
            metadata={
                "source": "wikipedia_database",
                "page_id": page_id,
                "relevance_score": article.relevance_score
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            f"Failed to load Wikipedia article {page_id}: {str(e)}",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to load Wikipedia article"
        )


@router.get("/summaries", response_model=WikipediaSummaryListResponse)
async def get_summaries(
    request: Request,
    wikipedia_service: WikipediaServiceDep,
    city: Optional[str] = Query(None, min_length=1, max_length=100, description="Filter by city name"),
    state: Optional[str] = Query(None, min_length=1, max_length=100, description="Filter by state name"),
    confidence_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence score"),
    include_key_topics: bool = Query(True, description="Include key topics in response"),
    include_embeddings: bool = Query(False, description="Include embedding data in response"),
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Number of items per page")
):
    """
    Load Wikipedia summaries with optional location and confidence filtering.
    
    Provides access to processed Wikipedia summaries with location extraction
    and confidence scores. Useful for getting structured overviews of articles.
    
    - **city**: Filter by extracted city name (e.g., "San Francisco", "Park City")
    - **state**: Filter by extracted state name (e.g., "California", "Utah")
    - **confidence_min**: Minimum confidence score threshold (0.0 to 1.0)
    - **include_key_topics**: Include key topics extracted from article content
    - **include_embeddings**: Include vector embedding data in response
    - **page**: Page number for pagination (1-based)
    - **page_size**: Number of items per page (max 500)
    """
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.info(
        f"Loading Wikipedia summaries - city: {city}, state: {state}, "
        f"confidence_min: {confidence_min}, include_key_topics: {include_key_topics}, "
        f"include_embeddings: {include_embeddings}, page: {page}, page_size: {page_size}",
        extra={"correlation_id": correlation_id}
    )
    
    try:
        # Use service to get paginated summaries
        paginated_summaries, total_count, total_pages = wikipedia_service.get_summaries(
            city=city,
            state=state,
            confidence_min=confidence_min,
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
        query_params = {
            'city': city,
            'state': state,
            'confidence_min': confidence_min,
            'include_key_topics': include_key_topics,
            'include_embeddings': include_embeddings,
            'page_size': page_size
        }
        links = _build_pagination_links(request, page, total_pages, "/api/v1/wikipedia/summaries", query_params)
        
        logger.info(
            f"Loaded {len(paginated_summaries)} summaries (page {page}/{total_pages})",
            extra={"correlation_id": correlation_id}
        )
        
        return WikipediaSummaryListResponse(
            data=paginated_summaries,
            metadata=metadata,
            links=links
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404 for invalid page)
        raise
    except Exception as e:
        logger.error(
            f"Failed to load Wikipedia summaries: {str(e)}",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to load Wikipedia summaries"
        )


@router.get("/summaries/{page_id}", response_model=WikipediaSummaryResponse)
async def get_summary(
    request: Request,
    wikipedia_service: WikipediaServiceDep,
    page_id: int = PathParam(..., description="Wikipedia page ID"),
    include_key_topics: bool = Query(True, description="Include key topics in response"),
    include_embeddings: bool = Query(False, description="Include embedding data in response")
):
    """
    Get a single Wikipedia summary by its page ID.
    
    Returns processed summary information for a specific Wikipedia article
    including extracted location data and confidence scores.
    
    - **page_id**: Wikipedia page ID (numeric)
    - **include_key_topics**: Include key topics extracted from article
    - **include_embeddings**: Include vector embedding data in response
    """
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.info(
        f"Loading Wikipedia summary: {page_id}",
        extra={"correlation_id": correlation_id}
    )
    
    try:
        # Use service to get summary by ID
        summary = wikipedia_service.get_summary_by_id(
            page_id=page_id,
            correlation_id=correlation_id
        )
        
        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"Wikipedia summary with page_id '{page_id}' not found"
            )
        
        # TODO: Handle include_embeddings when embedding integration is implemented
        if include_embeddings:
            logger.warning(
                "Embedding inclusion requested but not yet implemented",
                extra={"correlation_id": correlation_id}
            )
        
        logger.info(
            f"Found Wikipedia summary: {summary.article_title}",
            extra={"correlation_id": correlation_id}
        )
        
        return WikipediaSummaryResponse(
            data=summary,
            metadata={
                "source": "wikipedia_database",
                "page_id": page_id,
                "confidence_score": summary.overall_confidence,
                "extracted_location": {
                    "city": summary.best_city,
                    "state": summary.best_state
                }
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            f"Failed to load Wikipedia summary {page_id}: {str(e)}",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to load Wikipedia summary"
        )