"""
Base search service class for all entity-specific search services.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import TransportError
from .models import SearchError

logger = logging.getLogger(__name__)


class BaseSearchService:
    """
    Base class for all search services.
    
    Provides common functionality for Elasticsearch operations,
    error handling, and response transformation.
    """
    
    def __init__(self, es_client: Elasticsearch):
        """
        Initialize the base search service.
        
        Args:
            es_client: Elasticsearch client instance
        """
        self.es_client = es_client
        self.logger = logger
        
    def execute_search(
        self,
        index: str,
        query: Dict[str, Any],
        size: int = 10,
        from_offset: int = 0
    ) -> Dict[str, Any]:
        """
        Execute a search query against Elasticsearch.
        
        Args:
            index: Index name to search
            query: Elasticsearch query DSL
            size: Number of results to return
            from_offset: Pagination offset
            
        Returns:
            Raw Elasticsearch response
            
        Raises:
            TransportError: If search fails
        """
        try:
            start_time = datetime.now()
            
            # Use the new API without 'body' parameter (deprecated)
            es_response = self.es_client.search(
                index=index,
                **query,
                size=size,
                from_=from_offset
            )
            
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Create a new dict with the response body and add execution time
            # ObjectApiResponse is immutable, so we need to create a new dict
            response = dict(es_response.body)
            response['execution_time_ms'] = execution_time_ms
            
            self.logger.debug(
                f"Search executed on index '{index}' in {execution_time_ms}ms, "
                f"found {response['hits']['total']['value']} results"
            )
            
            return response
            
        except TransportError as e:
            self.logger.error(f"Elasticsearch error during search: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during search: {str(e)}")
            raise TransportError(f"Search failed: {str(e)}")
    
    def get_document(
        self,
        index: str,
        doc_id: str,
        source_fields: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single document by ID.
        
        Args:
            index: Index name
            doc_id: Document ID
            source_fields: Fields to include in response
            
        Returns:
            Document source or None if not found
        """
        try:
            params = {"index": index, "id": doc_id}
            if source_fields:
                params["_source"] = source_fields
                
            response = self.es_client.get(**params)
            # ObjectApiResponse delegates to body, which is a dict
            return response.get("_source")
            
        except Exception as e:
            self.logger.warning(f"Failed to get document {doc_id} from {index}: {str(e)}")
            return None
    
    def multi_search(
        self,
        searches: List[tuple[str, Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple searches in a single request.
        
        Args:
            searches: List of (index, query) tuples
            
        Returns:
            List of search responses
        """
        try:
            body = []
            for index, query in searches:
                body.append({"index": index})
                body.append(query)
            
            # msearch still uses body parameter
            response = self.es_client.msearch(body=body)
            # ObjectApiResponse delegates to body, which is a dict
            return response.get("responses", [])
            
        except Exception as e:
            self.logger.error(f"Multi-search failed: {str(e)}")
            raise TransportError(f"Multi-search failed: {str(e)}")
    
    def validate_index_exists(self, index: str) -> bool:
        """
        Check if an index exists.
        
        Args:
            index: Index name
            
        Returns:
            True if index exists, False otherwise
        """
        try:
            return self.es_client.indices.exists(index=index)
        except Exception as e:
            self.logger.error(f"Failed to check index existence: {str(e)}")
            return False
    
    def handle_search_error(self, error: Exception, context: str = "") -> SearchError:
        """
        Convert an exception to a SearchError model.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            SearchError model
        """
        error_type = type(error).__name__
        message = str(error)
        
        if context:
            message = f"{context}: {message}"
        
        self.logger.error(f"Search error ({error_type}): {message}")
        
        return SearchError(
            error_type=error_type,
            message=message,
            details={"context": context} if context else None
        )
    
    def extract_highlights(self, hit: Dict[str, Any]) -> Optional[Dict[str, List[str]]]:
        """
        Extract highlights from a search hit.
        
        Args:
            hit: Elasticsearch search hit
            
        Returns:
            Dictionary of field names to highlighted snippets
        """
        if "highlight" not in hit:
            return None
            
        highlights = {}
        for field, snippets in hit["highlight"].items():
            highlights[field] = snippets
            
        return highlights if highlights else None
    
    def calculate_total_hits(self, response: Dict[str, Any]) -> int:
        """
        Extract total hits from Elasticsearch response.
        
        Args:
            response: Elasticsearch response
            
        Returns:
            Total number of hits
        """
        hits = response.get("hits", {})
        total = hits.get("total", {})
        
        # Elasticsearch 7+ always returns total as dict with 'value' field
        # We directly access it without type checking
        return total.get("value", 0) if total else 0