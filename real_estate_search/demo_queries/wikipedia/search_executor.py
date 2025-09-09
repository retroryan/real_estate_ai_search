"""
Search execution module for Wikipedia queries.

This module handles all Elasticsearch interactions, including query execution,
result processing, and error handling.
"""

import time
from typing import Dict, Any, List, Optional
from elasticsearch import Elasticsearch
from .models import (
    SearchQuery,
    SearchResult,
    SearchHit,
    WikipediaDocument
)
from .query_builder import WikipediaQueryBuilder


class WikipediaSearchExecutor:
    """Executor for Wikipedia search queries against Elasticsearch."""
    
    def __init__(self, es_client: Elasticsearch):
        """Initialize the search executor.
        
        Args:
            es_client: Elasticsearch client instance
        """
        self.es_client = es_client
        self.query_builder = WikipediaQueryBuilder()
    
    def execute_query(self, query: SearchQuery) -> SearchResult:
        """Execute a search query against Elasticsearch.
        
        Args:
            query: SearchQuery object with query configuration
            
        Returns:
            SearchResult with hits and metadata
        """
        try:
            # Build complete search request
            search_body = self.query_builder.build_complete_search_request(query)
            
            # Execute search with timing
            start_time = time.time()
            response = self.es_client.search(
                index=query.index,
                body=search_body
            )
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Process response into SearchResult
            return self._process_response(
                response=response,
                query=query,
                execution_time_ms=execution_time_ms
            )
            
        except Exception as e:
            # Return error result
            return SearchResult(
                query=query,
                success=False,
                error=str(e),
                execution_time_ms=0
            )
    
    def _process_response(
        self,
        response: Dict[str, Any],
        query: SearchQuery,
        execution_time_ms: int
    ) -> SearchResult:
        """Process Elasticsearch response into SearchResult.
        
        Args:
            response: Raw Elasticsearch response
            query: Original query
            execution_time_ms: Query execution time
            
        Returns:
            Processed SearchResult
        """
        # Extract total hits
        total_hits = response['hits']['total']['value']
        
        # Process individual hits
        hits = []
        for hit in response['hits']['hits']:
            # Create WikipediaDocument from source
            document = WikipediaDocument(**hit['_source'])
            
            # Extract highlights
            highlights = {}
            if 'highlight' in hit:
                highlights = hit['highlight']
            
            # Create SearchHit
            search_hit = SearchHit(
                document=document,
                score=hit['_score'],
                highlights=highlights
            )
            hits.append(search_hit)
        
        return SearchResult(
            query=query,
            total_hits=total_hits,
            hits=hits,
            success=True,
            execution_time_ms=execution_time_ms
        )
    
    def execute_multiple_queries(
        self,
        queries: List[SearchQuery]
    ) -> List[SearchResult]:
        """Execute multiple queries in sequence.
        
        Args:
            queries: List of SearchQuery objects
            
        Returns:
            List of SearchResult objects
        """
        results = []
        for query in queries:
            result = self.execute_query(query)
            results.append(result)
        return results
    
    def get_document_by_id(
        self,
        page_id: str,
        index: str = "wikipedia"
    ) -> Optional[WikipediaDocument]:
        """Fetch a single document by its ID.
        
        Args:
            page_id: Wikipedia page ID
            index: Elasticsearch index name
            
        Returns:
            WikipediaDocument if found, None otherwise
        """
        try:
            response = self.es_client.get(
                index=index,
                id=page_id,
                _source=True
            )
            
            if response and '_source' in response:
                return WikipediaDocument(**response['_source'])
            return None
            
        except Exception:
            return None
    
    def get_documents_by_ids(
        self,
        page_ids: List[str],
        index: str = "wikipedia"
    ) -> Dict[str, WikipediaDocument]:
        """Fetch multiple documents by their IDs.
        
        Args:
            page_ids: List of Wikipedia page IDs
            index: Elasticsearch index name
            
        Returns:
            Dictionary mapping page_id to WikipediaDocument
        """
        documents = {}
        
        for page_id in page_ids:
            doc = self.get_document_by_id(page_id, index)
            if doc:
                documents[page_id] = doc
                
        return documents
    
    def test_connection(self) -> bool:
        """Test Elasticsearch connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            return self.es_client.ping()
        except Exception:
            return False
    
    def get_index_stats(self, index: str = "wikipedia") -> Optional[Dict[str, Any]]:
        """Get statistics for the Wikipedia index.
        
        Args:
            index: Index name
            
        Returns:
            Index statistics or None if error
        """
        try:
            stats = self.es_client.indices.stats(index=index)
            return {
                "document_count": stats['_all']['primaries']['docs']['count'],
                "size_in_bytes": stats['_all']['primaries']['store']['size_in_bytes'],
                "size_in_mb": stats['_all']['primaries']['store']['size_in_bytes'] / (1024 * 1024)
            }
        except Exception:
            return None