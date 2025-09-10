"""
Search execution and result processing for semantic search.

Handles Elasticsearch query execution and result conversion.
"""

from typing import Dict, Any, List, Tuple
import logging
import time
from elasticsearch import Elasticsearch

from ...models import PropertyListing
from ..property.models import PropertySearchResult


logger = logging.getLogger(__name__)


class SearchExecutor:
    """Executor for semantic and keyword searches."""
    
    def __init__(self, es_client: Elasticsearch):
        """
        Initialize the search executor.
        
        Args:
            es_client: Elasticsearch client instance
        """
        self.es_client = es_client
    
    def execute_search(
        self,
        query: Dict[str, Any],
        index: str = "properties"
    ) -> Tuple[List[Dict[str, Any]], int, float]:
        """
        Execute an Elasticsearch search and return processed results.
        
        Args:
            query: Query dictionary
            index: Index to search
            
        Returns:
            Tuple of (results list, total hits, execution time in ms)
            
        Raises:
            Exception: If search execution fails
        """
        start_time = time.time()
        
        try:
            response = self.es_client.search(index=index, body=query)
            execution_time_ms = (time.time() - start_time) * 1000
            
            results = []
            for hit in response['hits']['hits']:
                result = hit['_source']
                result['_score'] = hit['_score']
                result['_similarity_score'] = hit['_score']
                results.append(result)
            
            total_hits = response['hits']['total']['value']
            
            logger.info(f"Search executed: {total_hits} hits in {execution_time_ms:.1f}ms")
            return results, total_hits, execution_time_ms
            
        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            raise
    
    def convert_to_property_results(
        self, 
        raw_results: List[Dict[str, Any]]
    ) -> List[PropertyListing]:
        """
        Convert raw Elasticsearch results to PropertyListing objects.
        
        Args:
            raw_results: List of raw result dictionaries from Elasticsearch
            
        Returns:
            List of PropertyListing objects
        """
        return [PropertyListing.from_elasticsearch(result) for result in raw_results]
    
    def create_error_result(
        self,
        query_name: str,
        query_description: str,
        error_message: str,
        execution_time_ms: int = 0
    ) -> PropertySearchResult:
        """
        Create a PropertySearchResult for error cases.
        
        Args:
            query_name: Name of the query
            query_description: Description of the query
            error_message: Error message to include
            execution_time_ms: Execution time if available
            
        Returns:
            PropertySearchResult with error information
        """
        return PropertySearchResult(
            query_name=query_name,
            query_description=query_description,
            execution_time_ms=execution_time_ms,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl={"error": error_message},
            es_features=[f"Error: {error_message}"]
        )