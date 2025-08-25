"""
Wikipedia business logic service.

Handles all business operations for Wikipedia articles and summaries including 
filtering, pagination, and data retrieval.
"""

import math
from typing import List, Optional, Tuple, Union

from property_finder_models import EnrichedWikipediaArticle, WikipediaSummary
from ..loaders.wikipedia_loader import WikipediaLoader
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class WikipediaService:
    """Business logic service for Wikipedia operations."""
    
    def __init__(self, wikipedia_loader: WikipediaLoader):
        self.wikipedia_loader = wikipedia_loader
        
    def get_articles(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        relevance_min: Optional[float] = None,
        sort_by: str = "relevance",
        page: int = 1,
        page_size: int = 50,
        correlation_id: Optional[str] = None
    ) -> Tuple[List[EnrichedWikipediaArticle], int, int]:
        """
        Get Wikipedia articles with filtering and pagination.
        
        Args:
            city: Optional city filter
            state: Optional state filter
            relevance_min: Minimum relevance score filter
            sort_by: Sort order (relevance, title, page_id)
            page: Page number (1-based)
            page_size: Number of items per page
            correlation_id: Request correlation ID for logging
            
        Returns:
            Tuple of (paginated_articles, total_count, total_pages)
        """
        logger.info(
            f"Getting articles - city: {city}, state: {state}, relevance_min: {relevance_min}, "
            f"sort_by: {sort_by}, page: {page}, page_size: {page_size}",
            extra={"correlation_id": correlation_id}
        )
        
        # Load data using generic interface
        articles = self.wikipedia_loader.load_by_filter(
            city=city, 
            state=state, 
            relevance_min=relevance_min
        )
        
        # Apply sorting
        if sort_by == "relevance":
            articles.sort(key=lambda x: x.relevance_score, reverse=True)
        elif sort_by == "title":
            articles.sort(key=lambda x: x.title.lower())
        elif sort_by == "page_id":
            articles.sort(key=lambda x: x.page_id)
            
        # Apply pagination logic
        total_count = len(articles)
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Validate page number
        if page > total_pages and total_count > 0:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail=f"Page {page} not found. Total pages available: {total_pages}"
            )
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_articles = articles[start_idx:end_idx]
        
        return paginated_articles, total_count, total_pages
        
    def get_article_by_id(
        self, 
        page_id: int,
        correlation_id: Optional[str] = None
    ) -> Optional[EnrichedWikipediaArticle]:
        """Get single Wikipedia article by page ID."""
        logger.info(
            f"Getting article by page ID: {page_id}",
            extra={"correlation_id": correlation_id}
        )
        
        # Load all articles and find the specific one
        all_articles = self.wikipedia_loader.load_all()
        for article in all_articles:
            if article.page_id == page_id:
                return article
        return None
        
    def get_summaries(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        confidence_min: Optional[float] = None,
        page: int = 1,
        page_size: int = 50,
        correlation_id: Optional[str] = None
    ) -> Tuple[List[WikipediaSummary], int, int]:
        """
        Get Wikipedia summaries with filtering and pagination.
        
        Args:
            city: Optional city filter
            state: Optional state filter
            confidence_min: Minimum confidence score filter
            page: Page number (1-based)
            page_size: Number of items per page
            correlation_id: Request correlation ID for logging
            
        Returns:
            Tuple of (paginated_summaries, total_count, total_pages)
        """
        logger.info(
            f"Getting summaries - city: {city}, state: {state}, confidence_min: {confidence_min}, "
            f"page: {page}, page_size: {page_size}",
            extra={"correlation_id": correlation_id}
        )
        
        # Load summaries using the existing method
        if city or state:
            summaries = self.wikipedia_loader.load_summaries_by_location(city=city, state=state)
        else:
            summaries = self.wikipedia_loader.load_summaries()
        
        # Apply confidence filter if specified
        if confidence_min is not None:
            summaries = [s for s in summaries if s.overall_confidence >= confidence_min]
            
        # Apply pagination logic
        total_count = len(summaries)
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Validate page number
        if page > total_pages and total_count > 0:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail=f"Page {page} not found. Total pages available: {total_pages}"
            )
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_summaries = summaries[start_idx:end_idx]
        
        return paginated_summaries, total_count, total_pages
        
    def get_summary_by_id(
        self, 
        page_id: int,
        correlation_id: Optional[str] = None
    ) -> Optional[WikipediaSummary]:
        """Get single Wikipedia summary by page ID."""
        logger.info(
            f"Getting summary by page ID: {page_id}",
            extra={"correlation_id": correlation_id}
        )
        
        # Load all summaries and find the specific one
        all_summaries = self.wikipedia_loader.load_summaries()
        for summary in all_summaries:
            if summary.page_id == page_id:
                return summary
        return None