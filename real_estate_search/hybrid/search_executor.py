"""
Search executor module for executing Elasticsearch queries.

Handles the actual execution of searches against Elasticsearch,
including error handling, retries, and performance monitoring.
"""

import logging
import time
import json
from typing import Dict, Any, Optional
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import (
    ConnectionError,
    RequestError,
    NotFoundError,
    TransportError,
    ApiError
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ExecutionMetrics(BaseModel):
    """Metrics about search execution."""
    start_time: float = Field(..., description="Start timestamp")
    end_time: Optional[float] = Field(None, description="End timestamp")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    retry_count: int = Field(0, description="Number of retries performed")
    success: bool = Field(False, description="Whether execution succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class SearchExecutor:
    """
    Executes searches against Elasticsearch with robust error handling.
    
    Features:
    - Query execution with retries
    - Performance monitoring
    - Detailed logging
    - Error handling and recovery
    """
    
    def __init__(
        self,
        es_client: Elasticsearch,
        index_name: str = "properties",
        max_retries: int = 3
    ):
        """
        Initialize the search executor.
        
        Args:
            es_client: Elasticsearch client instance
            index_name: Name of the index to search
            max_retries: Maximum number of retry attempts
        """
        self.es_client = es_client
        self.index_name = index_name
        self.max_retries = max_retries
        logger.debug(f"Initialized SearchExecutor for index: {index_name}")
    
    def execute(
        self,
        query: Dict[str, Any],
        debug: bool = False
    ) -> tuple[Dict[str, Any], ExecutionMetrics]:
        """
        Execute a search query against Elasticsearch.
        
        Args:
            query: Elasticsearch query dictionary
            debug: Whether to enable debug logging
            
        Returns:
            Tuple of (response, metrics)
            
        Raises:
            ApiError: If query execution fails after retries
        """
        metrics = ExecutionMetrics(start_time=time.time())
        
        # Log query if debug enabled
        if debug:
            self._log_query(query)
        
        # Execute with retries
        response = self._execute_with_retry(query, metrics)
        
        # Finalize metrics
        metrics.end_time = time.time()
        metrics.execution_time_ms = int((metrics.end_time - metrics.start_time) * 1000)
        metrics.success = True
        
        # Log execution summary
        self._log_execution_summary(metrics, response)
        
        return response, metrics
    
    def _execute_with_retry(
        self,
        query: Dict[str, Any],
        metrics: ExecutionMetrics
    ) -> Dict[str, Any]:
        """
        Execute query with retry logic.
        
        Args:
            query: Elasticsearch query
            metrics: Execution metrics to update
            
        Returns:
            Elasticsearch response
            
        Raises:
            ApiError: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Execute query
                response = self.es_client.search(
                    index=self.index_name,
                    body=query
                )
                
                # Success - return response
                return response
                
            except ConnectionError as e:
                # Connection issues - retry
                last_error = e
                metrics.retry_count = attempt + 1
                logger.warning(
                    f"Connection error on attempt {attempt + 1}/{self.max_retries}: {e}"
                )
                
                # Wait before retry (exponential backoff)
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    
            except RequestError as e:
                # Query syntax error - don't retry
                metrics.error_message = str(e)
                logger.error(f"Query syntax error: {e}")
                raise
                
            except NotFoundError as e:
                # Index not found - don't retry
                metrics.error_message = f"Index '{self.index_name}' not found"
                logger.error(metrics.error_message)
                raise
                
            except (TransportError, ApiError) as e:
                # Other Elasticsearch errors
                last_error = e
                metrics.retry_count = attempt + 1
                logger.error(f"Elasticsearch error on attempt {attempt + 1}: {e}")
                
                # Only retry for certain error types
                if self._should_retry(e):
                    if attempt < self.max_retries - 1:
                        time.sleep(1)
                else:
                    raise
        
        # All retries failed
        metrics.success = False
        metrics.error_message = str(last_error)
        error_msg = f"Query failed after {self.max_retries} attempts: {last_error}"
        logger.error(error_msg)
        raise TransportError(error_msg) from last_error
    
    def _should_retry(self, error: Exception) -> bool:
        """
        Determine if an error is retryable.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if the operation should be retried
        """
        # Retry on connection and timeout errors
        retryable_errors = [
            'ConnectionTimeout',
            'ConnectionError',
            'ReadTimeoutError',
            'TransportError'
        ]
        
        error_type = type(error).__name__
        return error_type in retryable_errors
    
    def _log_query(self, query: Dict[str, Any]) -> None:
        """
        Log query details for debugging.
        
        Args:
            query: Elasticsearch query dictionary
        """
        # Truncate vectors for logging
        logged_query = self._truncate_vectors(query)
        
        logger.debug(
            f"Executing query on index '{self.index_name}': "
            f"{json.dumps(logged_query, indent=2, default=str)}"
        )
    
    def _truncate_vectors(self, obj: Any) -> Any:
        """
        Truncate vector fields for logging.
        
        Args:
            obj: Object to process
            
        Returns:
            Object with truncated vectors
        """
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if key == 'query_vector' and isinstance(value, list) and len(value) > 3:
                    result[key] = value[:3] + ['...truncated...']
                else:
                    result[key] = self._truncate_vectors(value)
            return result
        elif isinstance(obj, list):
            return [self._truncate_vectors(item) for item in obj]
        else:
            return obj
    
    def _log_execution_summary(
        self,
        metrics: ExecutionMetrics,
        response: Dict[str, Any]
    ) -> None:
        """
        Log execution summary.
        
        Args:
            metrics: Execution metrics
            response: Elasticsearch response
        """
        total_hits = response.get('hits', {}).get('total', {}).get('value', 0)
        
        logger.info(
            f"Search executed - "
            f"Index: {self.index_name}, "
            f"Time: {metrics.execution_time_ms}ms, "
            f"Hits: {total_hits}, "
            f"Retries: {metrics.retry_count}"
        )
        
        # Log Elasticsearch's internal timing
        es_took = response.get('took', 'N/A')
        if es_took != 'N/A':
            logger.debug(f"Elasticsearch internal execution time: {es_took}ms")
    
    def validate_connection(self) -> bool:
        """
        Validate Elasticsearch connection.
        
        Returns:
            True if connection is valid
        """
        try:
            # Check cluster health
            health = self.es_client.cluster.health()
            status = health.get('status', 'unknown')
            
            if status == 'red':
                logger.warning("Elasticsearch cluster status is RED")
            elif status == 'yellow':
                logger.info("Elasticsearch cluster status is YELLOW")
            else:
                logger.debug("Elasticsearch cluster status is GREEN")
            
            # Check if index exists
            if not self.es_client.indices.exists(index=self.index_name):
                logger.error(f"Index '{self.index_name}' does not exist")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate Elasticsearch connection: {e}")
            return False