"""Wikipedia API Client Implementation."""

import logging
from typing import List, Optional, Iterator

from property_finder_models import EnrichedWikipediaArticle, WikipediaSummary

from .base import BaseAPIClient
from .config import APIClientConfig
from .exceptions import NotFoundError, APIError
from .wikipedia_models import (
    WikipediaArticleListRequest,
    WikipediaArticleListResponse,
    WikipediaArticleResponse,
    WikipediaSummaryListRequest,
    WikipediaSummaryListResponse,
    WikipediaSummaryResponse
)


class WikipediaAPIClient(BaseAPIClient):
    """API client for Wikipedia articles and summaries."""
    
    def __init__(self, config: APIClientConfig, logger: logging.Logger):
        """Initialize the Wikipedia API client.
        
        Args:
            config: API client configuration
            logger: Logger instance for structured logging
        """
        super().__init__(config, logger)
        self.logger.info(
            "Initialized Wikipedia API client",
            extra={"base_url": str(config.base_url)}
        )
    
    def get_articles(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        relevance_min: Optional[float] = None,
        sort_by: str = "relevance",
        include_embeddings: bool = False,
        collection_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> List[EnrichedWikipediaArticle]:
        """Get Wikipedia articles with optional filtering.
        
        Args:
            city: Filter by city name
            state: Filter by state name
            relevance_min: Minimum relevance score (0.0 to 1.0)
            sort_by: Sort by field (relevance, title, page_id)
            include_embeddings: Include embedding data in response
            collection_name: ChromaDB collection name for embeddings
            page: Page number (1-based)
            page_size: Number of items per page
            
        Returns:
            List of enriched Wikipedia articles
            
        Raises:
            APIError: If request fails
        """
        self.logger.debug(
            "Fetching Wikipedia articles",
            extra={
                "city": city,
                "state": state,
                "relevance_min": relevance_min,
                "sort_by": sort_by,
                "page": page,
                "page_size": page_size
            }
        )
        
        # Build request parameters
        params = {
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by
        }
        
        if city:
            params["city"] = city
        if state:
            params["state"] = state
        if relevance_min is not None:
            params["relevance_min"] = relevance_min
        if include_embeddings:
            params["include_embeddings"] = include_embeddings
        if collection_name:
            params["collection_name"] = collection_name
        
        # Make request
        response_data = self.get("articles", params=params)
        
        # Validate and parse response
        response = WikipediaArticleListResponse(**response_data)
        
        self.logger.info(
            f"Retrieved {len(response.data)} Wikipedia articles",
            extra={
                "total": response.metadata.total_count,
                "page": response.metadata.page
            }
        )
        
        return response.data
    
    def get_all_articles(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        relevance_min: Optional[float] = None,
        sort_by: str = "relevance",
        include_embeddings: bool = False,
        collection_name: Optional[str] = None,
        page_size: int = 50
    ) -> Iterator[List[EnrichedWikipediaArticle]]:
        """Get all Wikipedia articles with automatic pagination.
        
        Args:
            city: Filter by city name
            state: Filter by state name
            relevance_min: Minimum relevance score (0.0 to 1.0)
            sort_by: Sort by field (relevance, title, page_id)
            include_embeddings: Include embedding data in response
            collection_name: ChromaDB collection name for embeddings
            page_size: Number of items per page
            
        Yields:
            Lists of enriched Wikipedia articles from each page
            
        Raises:
            APIError: If request fails
        """
        self.logger.info(
            "Fetching all Wikipedia articles with pagination",
            extra={
                "city": city,
                "state": state,
                "page_size": page_size
            }
        )
        
        page = 1
        while True:
            # Get current page
            articles = self.get_articles(
                city=city,
                state=state,
                relevance_min=relevance_min,
                sort_by=sort_by,
                include_embeddings=include_embeddings,
                collection_name=collection_name,
                page=page,
                page_size=page_size
            )
            
            # If no articles returned, we're done
            if not articles:
                break
                
            yield articles
            
            # If we got fewer than requested, this is the last page
            if len(articles) < page_size:
                break
                
            page += 1
    
    def get_article_by_id(
        self,
        page_id: int,
        include_embeddings: bool = False
    ) -> EnrichedWikipediaArticle:
        """Get a single Wikipedia article by page ID.
        
        Args:
            page_id: Wikipedia page ID
            include_embeddings: Include embedding data in response
            
        Returns:
            Enriched Wikipedia article data
            
        Raises:
            NotFoundError: If article not found
            APIError: If request fails
        """
        self.logger.debug(
            "Fetching Wikipedia article by ID",
            extra={"page_id": page_id}
        )
        
        try:
            params = {}
            if include_embeddings:
                params["include_embeddings"] = include_embeddings
            
            response_data = self.get(f"articles/{page_id}", params=params if params else None)
            response = WikipediaArticleResponse(**response_data)
            
            self.logger.info(
                "Retrieved Wikipedia article by ID",
                extra={"page_id": page_id, "title": response.data.title}
            )
            
            return response.data
            
        except NotFoundError:
            self.logger.warning(
                f"Wikipedia article not found: {page_id}",
                extra={"page_id": page_id}
            )
            raise
    
    def get_summaries(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        confidence_min: Optional[float] = None,
        include_key_topics: bool = True,
        include_embeddings: bool = False,
        collection_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> List[WikipediaSummary]:
        """Get Wikipedia summaries with optional filtering.
        
        Args:
            city: Filter by city name
            state: Filter by state name
            confidence_min: Minimum confidence score (0.0 to 1.0)
            include_key_topics: Include key topics in response
            include_embeddings: Include embedding data in response
            collection_name: ChromaDB collection name for embeddings
            page: Page number (1-based)
            page_size: Number of items per page
            
        Returns:
            List of Wikipedia summaries
            
        Raises:
            APIError: If request fails
        """
        self.logger.debug(
            "Fetching Wikipedia summaries",
            extra={
                "city": city,
                "state": state,
                "confidence_min": confidence_min,
                "page": page,
                "page_size": page_size
            }
        )
        
        # Build request parameters
        params = {
            "page": page,
            "page_size": page_size,
            "include_key_topics": include_key_topics
        }
        
        if city:
            params["city"] = city
        if state:
            params["state"] = state
        if confidence_min is not None:
            params["confidence_min"] = confidence_min
        if include_embeddings:
            params["include_embeddings"] = include_embeddings
        if collection_name:
            params["collection_name"] = collection_name
        
        # Make request
        response_data = self.get("summaries", params=params)
        
        # Validate and parse response
        response = WikipediaSummaryListResponse(**response_data)
        
        self.logger.info(
            f"Retrieved {len(response.data)} Wikipedia summaries",
            extra={
                "total": response.metadata.total_count,
                "page": response.metadata.page
            }
        )
        
        return response.data
    
    def get_all_summaries(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        confidence_min: Optional[float] = None,
        include_key_topics: bool = True,
        include_embeddings: bool = False,
        collection_name: Optional[str] = None,
        page_size: int = 50
    ) -> Iterator[List[WikipediaSummary]]:
        """Get all Wikipedia summaries with automatic pagination.
        
        Args:
            city: Filter by city name
            state: Filter by state name
            confidence_min: Minimum confidence score (0.0 to 1.0)
            include_key_topics: Include key topics in response
            include_embeddings: Include embedding data in response
            collection_name: ChromaDB collection name for embeddings
            page_size: Number of items per page
            
        Yields:
            Lists of Wikipedia summaries from each page
            
        Raises:
            APIError: If request fails
        """
        self.logger.info(
            "Fetching all Wikipedia summaries with pagination",
            extra={
                "city": city,
                "state": state,
                "page_size": page_size
            }
        )
        
        page = 1
        while True:
            # Get current page
            summaries = self.get_summaries(
                city=city,
                state=state,
                confidence_min=confidence_min,
                include_key_topics=include_key_topics,
                include_embeddings=include_embeddings,
                collection_name=collection_name,
                page=page,
                page_size=page_size
            )
            
            # If no summaries returned, we're done
            if not summaries:
                break
                
            yield summaries
            
            # If we got fewer than requested, this is the last page
            if len(summaries) < page_size:
                break
                
            page += 1
    
    def get_summary_by_id(
        self,
        page_id: int,
        include_key_topics: bool = True,
        include_embeddings: bool = False
    ) -> WikipediaSummary:
        """Get a single Wikipedia summary by page ID.
        
        Args:
            page_id: Wikipedia page ID
            include_key_topics: Include key topics in response
            include_embeddings: Include embedding data in response
            
        Returns:
            Wikipedia summary data
            
        Raises:
            NotFoundError: If summary not found
            APIError: If request fails
        """
        self.logger.debug(
            "Fetching Wikipedia summary by ID",
            extra={"page_id": page_id}
        )
        
        try:
            params = {
                "include_key_topics": include_key_topics
            }
            if include_embeddings:
                params["include_embeddings"] = include_embeddings
            
            response_data = self.get(f"summaries/{page_id}", params=params)
            response = WikipediaSummaryResponse(**response_data)
            
            self.logger.info(
                "Retrieved Wikipedia summary by ID",
                extra={"page_id": page_id, "title": response.data.article_title}
            )
            
            return response.data
            
        except NotFoundError:
            self.logger.warning(
                f"Wikipedia summary not found: {page_id}",
                extra={"page_id": page_id}
            )
            raise