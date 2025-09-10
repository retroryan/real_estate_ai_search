"""
Base demo runner providing common execution patterns.

This module provides a base class that encapsulates common demo execution
patterns, reducing code duplication across all demo runners.
"""

from typing import Dict, Any, Optional, TypeVar, Generic, Callable, Tuple, List
from abc import ABC, abstractmethod
from elasticsearch import Elasticsearch
import logging
import time

from .demo_config import demo_config

logger = logging.getLogger(__name__)

# Type variable for result types
ResultType = TypeVar('ResultType')


class BaseDemoRunner(ABC, Generic[ResultType]):
    """
    Base class for all demo runners providing common execution patterns.
    
    This class encapsulates the common flow of:
    1. Building queries
    2. Executing searches
    3. Processing results
    4. Creating result objects
    5. Error handling
    """
    
    def __init__(self, es_client: Elasticsearch):
        """
        Initialize the base demo runner.
        
        Args:
            es_client: Elasticsearch client instance
        """
        self.es_client = es_client
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def execute_demo(
        self,
        demo_name: str,
        query_builder_func: Callable[[], Dict[str, Any]],
        result_processor_func: Callable[..., ResultType],
        index_name: str = None,
        **kwargs
    ) -> ResultType:
        """
        Execute a demo following the standard pattern.
        
        Args:
            demo_name: Name of the demo for logging
            query_builder_func: Function that builds the Elasticsearch query
            result_processor_func: Function that processes the response into result object
            index_name: Elasticsearch index to search (uses config default if None)
            **kwargs: Additional arguments passed to functions
            
        Returns:
            Result object of type ResultType
        """
        start_time = time.time()
        
        try:
            # Build query
            self.logger.info(f"Building query for {demo_name}")
            query_dsl = query_builder_func()
            
            # Use default index if not specified
            if index_name is None:
                index_name = demo_config.indexes.properties_index
            
            # Execute search
            self.logger.info(f"Executing {demo_name} on index '{index_name}'")
            response = self.es_client.search(index=index_name, body=query_dsl)
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Process response into result object
            self.logger.info(f"Processing results for {demo_name}")
            result = result_processor_func(response, execution_time_ms, query_dsl=query_dsl, **kwargs)
            
            self.logger.info(f"Completed {demo_name} in {execution_time_ms:.1f}ms")
            return result
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Error in {demo_name}: {e}")
            
            # Return error result
            return self.create_error_result(
                demo_name=demo_name,
                error_message=str(e),
                execution_time_ms=execution_time_ms,
                query_dsl=query_dsl if 'query_dsl' in locals() else {},
                **kwargs
            )
    
    @abstractmethod
    def create_error_result(
        self,
        demo_name: str,
        error_message: str,
        execution_time_ms: float,
        query_dsl: Dict[str, Any],
        **kwargs
    ) -> ResultType:
        """
        Create an error result object.
        
        Args:
            demo_name: Name of the failed demo
            error_message: Error description
            execution_time_ms: Time taken before error
            query_dsl: Query that was being executed
            **kwargs: Additional context
            
        Returns:
            Error result object of type ResultType
        """
        pass
    
    def safe_extract_hits(self, response: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
        """
        Safely extract hits and total count from Elasticsearch response.
        
        Args:
            response: Elasticsearch response dictionary
            
        Returns:
            Tuple of (hits_list, total_count)
        """
        try:
            hits = response.get('hits', {}).get('hits', [])
            
            # Handle different total formats (ES 7+ vs older)
            total_hits = response.get('hits', {}).get('total', 0)
            if isinstance(total_hits, dict):
                total_count = total_hits.get('value', 0)
            else:
                total_count = total_hits
                
            return hits, total_count
            
        except Exception as e:
            self.logger.warning(f"Error extracting hits: {e}")
            return [], 0
    
    def safe_extract_aggregations(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safely extract aggregations from Elasticsearch response.
        
        Args:
            response: Elasticsearch response dictionary
            
        Returns:
            Aggregations dictionary or empty dict if none
        """
        return response.get('aggregations', {})
    
    def safe_get_execution_time(self, response: Dict[str, Any]) -> int:
        """
        Safely extract execution time from Elasticsearch response.
        
        Args:
            response: Elasticsearch response dictionary
            
        Returns:
            Execution time in milliseconds
        """
        return response.get('took', 0)
    
    def build_es_features_list(self, features: List[str], demo_context: str = "") -> List[str]:
        """
        Build a standardized list of Elasticsearch features used.
        
        Args:
            features: List of feature descriptions
            demo_context: Additional context about the demo
            
        Returns:
            Formatted list of ES features
        """
        base_features = [
            "Elasticsearch Query DSL - Structured query language",
            "JSON-based Search - Flexible query construction"
        ]
        
        if demo_context:
            base_features.append(f"Demo Context: {demo_context}")
        
        return base_features + features
    
    def build_indexes_used_list(self, primary_index: str, context: str = "") -> List[str]:
        """
        Build a standardized list of indexes used.
        
        Args:
            primary_index: Main index being searched
            context: Additional context about index usage
            
        Returns:
            Formatted list of indexes used
        """
        indexes = [f"{primary_index} - {self.get_index_description(primary_index)}"]
        
        if context:
            indexes.append(context)
        
        return indexes
    
    def get_index_description(self, index_name: str) -> str:
        """
        Get a human-readable description of an index.
        
        Args:
            index_name: Name of the index
            
        Returns:
            Description of the index purpose
        """
        descriptions = {
            "properties": "Real estate property listings with embeddings",
            "neighborhoods": "Neighborhood data with demographics and ratings",
            "wikipedia": "Wikipedia articles with location-based content",
            "property_relationships": "Denormalized properties with embedded neighborhood and Wikipedia data"
        }
        
        return descriptions.get(index_name, f"Index: {index_name}")
    
    def validate_query_dsl(self, query_dsl: Dict[str, Any]) -> bool:
        """
        Validate that a query DSL is properly structured.
        
        Args:
            query_dsl: Query DSL to validate
            
        Returns:
            True if valid, logs warnings if not
        """
        if not query_dsl:
            self.logger.warning("Query DSL is empty")
            return False
        
        if not isinstance(query_dsl, dict):
            self.logger.warning("Query DSL must be a dictionary")
            return False
        
        # Basic validation - should have query, size, or aggs
        required_keys = ['query', 'size', 'aggs', 'knn']
        if not any(key in query_dsl for key in required_keys):
            self.logger.warning(f"Query DSL should contain one of: {required_keys}")
            return False
        
        return True