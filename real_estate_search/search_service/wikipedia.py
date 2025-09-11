"""
Wikipedia search service implementation.
"""

import logging
from typing import Dict, Any, List, Optional
from .elasticsearch_compat import Elasticsearch

from .base import BaseSearchService
from .models import (
    WikipediaSearchRequest,
    WikipediaSearchResponse,
    WikipediaSearchType
)
from ..models.wikipedia import WikipediaArticle

logger = logging.getLogger(__name__)


class WikipediaSearchService(BaseSearchService):
    """
    Service for searching Wikipedia articles in Elasticsearch.
    
    Handles full-text search, chunk-based search, summary search,
    category filtering, and highlighting for Wikipedia content.
    """
    
    def __init__(self, es_client: Elasticsearch):
        """
        Initialize the Wikipedia search service.
        
        Args:
            es_client: Elasticsearch client instance
        """
        super().__init__(es_client)
        self.full_text_index = "wikipedia"
        self.chunks_index_prefix = "wiki_chunks"
        self.summaries_index_prefix = "wiki_summaries"
    
    def search(self, request: WikipediaSearchRequest) -> WikipediaSearchResponse:
        """
        Main search method that routes to appropriate search type.
        
        Args:
            request: Wikipedia search request
            
        Returns:
            Wikipedia search response
        """
        try:
            # Determine index based on search type
            index = self._get_index_for_search_type(request.search_type)
            
            # Build query based on request parameters
            query = self._build_query(request)
            
            # Execute search
            es_response = self.execute_search(
                index=index,
                query=query,
                size=request.size,
                from_offset=request.from_offset
            )
            
            # Transform response
            return self._transform_response(es_response, request)
            
        except Exception as e:
            logger.error(f"Wikipedia search failed: {str(e)}")
            raise
    
    def search_fulltext(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        size: int = 10
    ) -> WikipediaSearchResponse:
        """
        Perform full-text search across Wikipedia articles.
        
        Args:
            query: Search query
            categories: Optional category filters
            size: Number of results
            
        Returns:
            Wikipedia search response
        """
        request = WikipediaSearchRequest(
            query=query,
            search_type=WikipediaSearchType.FULL_TEXT,
            categories=categories,
            include_highlights=True,
            size=size
        )
        return self.search(request)
    
    def search_chunks(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        size: int = 10
    ) -> WikipediaSearchResponse:
        """
        Search within article chunks.
        
        Args:
            query: Search query
            categories: Optional category filters
            size: Number of results
            
        Returns:
            Wikipedia search response
        """
        request = WikipediaSearchRequest(
            query=query,
            search_type=WikipediaSearchType.CHUNKS,
            categories=categories,
            include_highlights=True,
            size=size
        )
        return self.search(request)
    
    def search_summaries(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        size: int = 10
    ) -> WikipediaSearchResponse:
        """
        Search article summaries.
        
        Args:
            query: Search query
            categories: Optional category filters
            size: Number of results
            
        Returns:
            Wikipedia search response
        """
        request = WikipediaSearchRequest(
            query=query,
            search_type=WikipediaSearchType.SUMMARIES,
            categories=categories,
            include_highlights=True,
            size=size
        )
        return self.search(request)
    
    def search_by_category(
        self,
        categories: List[str],
        query: Optional[str] = None,
        size: int = 10
    ) -> WikipediaSearchResponse:
        """
        Search articles by category.
        
        Args:
            categories: Categories to filter by
            query: Optional text query
            size: Number of results
            
        Returns:
            Wikipedia search response
        """
        request = WikipediaSearchRequest(
            query=query or "",
            search_type=WikipediaSearchType.FULL_TEXT,
            categories=categories,
            size=size
        )
        return self.search(request)
    
    def _get_index_for_search_type(self, search_type: WikipediaSearchType) -> str:
        """
        Get the appropriate index name for the search type.
        
        Args:
            search_type: Type of search
            
        Returns:
            Index name
        """
        if search_type == WikipediaSearchType.FULL_TEXT:
            return self.full_text_index
        elif search_type == WikipediaSearchType.CHUNKS:
            return f"{self.chunks_index_prefix}_*"
        elif search_type == WikipediaSearchType.SUMMARIES:
            return f"{self.summaries_index_prefix}_*"
        else:
            return self.full_text_index
    
    def _build_query(self, request: WikipediaSearchRequest) -> Dict[str, Any]:
        """
        Build Elasticsearch query from request parameters.
        
        Args:
            request: Wikipedia search request
            
        Returns:
            Elasticsearch query DSL
        """
        # Build the main query
        bool_query = {"bool": {}}
        
        # Add text query if provided
        if request.query:
            # Use different fields based on search type
            if request.search_type == WikipediaSearchType.FULL_TEXT:
                fields = [
                    "title^3",
                    "full_content",
                    "summary^2",
                    "categories"
                ]
            elif request.search_type == WikipediaSearchType.CHUNKS:
                fields = [
                    "chunk_content",
                    "title^2"
                ]
            elif request.search_type == WikipediaSearchType.SUMMARIES:
                fields = [
                    "summary",
                    "title^2"
                ]
            else:
                fields = ["title", "full_content"]
            
            bool_query["bool"]["must"] = [{
                "multi_match": {
                    "query": request.query,
                    "fields": fields,
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            }]
        else:
            # If no query, match all
            bool_query["bool"]["must"] = [{"match_all": {}}]
        
        # Add category filters if provided
        if request.categories:
            bool_query["bool"]["filter"] = [{
                "terms": {
                    "categories": request.categories
                }
            }]
        
        query = {"query": bool_query}
        
        # Add highlighting if requested
        if request.include_highlights:
            highlight_fields = {}
            
            if request.search_type == WikipediaSearchType.FULL_TEXT:
                highlight_fields = {
                    "full_content": {
                        "fragment_size": request.highlight_fragment_size,
                        "number_of_fragments": 3
                    },
                    "summary": {
                        "fragment_size": request.highlight_fragment_size
                    }
                }
            elif request.search_type == WikipediaSearchType.CHUNKS:
                highlight_fields = {
                    "chunk_content": {
                        "fragment_size": request.highlight_fragment_size,
                        "number_of_fragments": 3
                    }
                }
            elif request.search_type == WikipediaSearchType.SUMMARIES:
                highlight_fields = {
                    "summary": {
                        "fragment_size": request.highlight_fragment_size,
                        "number_of_fragments": 2
                    }
                }
            
            if highlight_fields:
                query["highlight"] = {
                    "fields": highlight_fields,
                    "pre_tags": ["<em>"],
                    "post_tags": ["</em>"]
                }
        
        # Add source filtering based on search type
        if request.search_type == WikipediaSearchType.FULL_TEXT:
            query["_source"] = [
                "page_id", "title", "url", "long_summary", "short_summary",
                "categories", "key_topics", "content_length"
            ]
        elif request.search_type == WikipediaSearchType.CHUNKS:
            query["_source"] = [
                "page_id", "chunk_id", "title", "url",
                "chunk_content", "categories"
            ]
        elif request.search_type == WikipediaSearchType.SUMMARIES:
            query["_source"] = [
                "page_id", "title", "url", "long_summary", "short_summary",
                "categories", "key_topics"
            ]
        
        return query
    
    def _transform_response(
        self,
        es_response: Dict[str, Any],
        request: WikipediaSearchRequest
    ) -> WikipediaSearchResponse:
        """
        Transform Elasticsearch response to WikipediaSearchResponse.
        
        Args:
            es_response: Raw Elasticsearch response
            request: Original search request
            
        Returns:
            Transformed Wikipedia search response
        """
        results = []
        
        for hit in es_response.get("hits", {}).get("hits", []):
            source = hit["_source"]
            
            # Build Wikipedia article
            result = WikipediaArticle(
                page_id=source.get("page_id", ""),
                title=source.get("title", ""),
                url=source.get("url"),
                long_summary=source.get("long_summary"),
                short_summary=source.get("short_summary"),
                categories=source.get("categories", []),
                key_topics=source.get("key_topics", []),
                content_length=source.get("content_length"),
                score=hit.get("_score", 0)
            )
            
            # Note: chunk_id and highlights are not stored in WikipediaArticle model
            # These are search-specific fields that could be added if needed
            
            results.append(result)
        
        # Build response
        return WikipediaSearchResponse(
            results=results,
            total_hits=self.calculate_total_hits(es_response),
            execution_time_ms=es_response.get("execution_time_ms", 0),
            search_type=request.search_type,
            applied_categories=request.categories
        )