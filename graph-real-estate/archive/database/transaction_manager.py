"""Transaction management with retry logic for Neo4j operations"""
import time
import logging
from typing import List, Dict, Any, Callable, Optional
from neo4j import Driver
from neo4j.exceptions import ServiceUnavailable, TransientError, SessionExpired

logger = logging.getLogger(__name__)


class TransactionManager:
    """Manages Neo4j transactions with retry logic and proper error handling"""
    
    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1  # seconds
    MAX_RETRY_DELAY = 10  # seconds
    BACKOFF_MULTIPLIER = 2
    
    def __init__(self, driver: Driver):
        """
        Initialize transaction manager
        
        Args:
            driver: Neo4j database driver
        """
        self.driver = driver
    
    def execute_read(self, query: str, **params) -> List[Dict[str, Any]]:
        """
        Execute read transaction with retry logic
        
        Args:
            query: Cypher query to execute
            **params: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        return self._execute_with_retry(
            query=query,
            is_write=False,
            **params
        )
    
    def execute_write(self, query: str, **params) -> List[Dict[str, Any]]:
        """
        Execute write transaction with retry logic
        
        Args:
            query: Cypher query to execute
            **params: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        return self._execute_with_retry(
            query=query,
            is_write=True,
            **params
        )
    
    def _execute_with_retry(
        self, 
        query: str, 
        is_write: bool, 
        database: Optional[str] = None,
        **params
    ) -> List[Dict[str, Any]]:
        """
        Execute query with exponential backoff retry
        
        Args:
            query: Cypher query to execute
            is_write: Whether this is a write transaction
            database: Database name (optional)
            **params: Query parameters
            
        Returns:
            List of result records as dictionaries
            
        Raises:
            Exception: If all retries are exhausted
        """
        last_error = None
        delay = self.INITIAL_RETRY_DELAY
        
        for attempt in range(self.MAX_RETRIES):
            try:
                with self.driver.session(database=database) as session:
                    if is_write:
                        result = session.execute_write(
                            self._run_transaction,
                            query,
                            **params
                        )
                    else:
                        result = session.execute_read(
                            self._run_transaction,
                            query,
                            **params
                        )
                    
                    # Success - log if this was a retry
                    if attempt > 0:
                        logger.info(
                            f"Transaction succeeded on attempt {attempt + 1} "
                            f"after previous failures"
                        )
                    
                    return result
                    
            except (ServiceUnavailable, TransientError, SessionExpired) as e:
                last_error = e
                
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(
                        f"Transient error on attempt {attempt + 1}/{self.MAX_RETRIES}: "
                        f"{type(e).__name__}: {e}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    
                    # Exponential backoff with max delay
                    delay = min(delay * self.BACKOFF_MULTIPLIER, self.MAX_RETRY_DELAY)
                else:
                    logger.error(
                        f"Max retries ({self.MAX_RETRIES}) reached. "
                        f"Final error: {type(e).__name__}: {e}"
                    )
                    
            except Exception as e:
                # Non-transient error - don't retry
                logger.error(f"Non-transient error: {type(e).__name__}: {e}")
                raise
        
        # All retries exhausted
        if last_error:
            raise last_error
    
    @staticmethod
    def _run_transaction(tx, query: str, **params) -> List[Dict[str, Any]]:
        """
        Run transaction and return results
        
        Args:
            tx: Transaction object
            query: Cypher query
            **params: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        result = tx.run(query, **params)
        return [dict(record) for record in result]
    
    def execute_batch_write(
        self, 
        queries: List[tuple], 
        database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute multiple write queries in a single transaction
        
        Args:
            queries: List of (query, params) tuples
            database: Database name (optional)
            
        Returns:
            Dictionary with success status and results/errors
        """
        results = []
        
        def _batch_transaction(tx):
            batch_results = []
            for query, params in queries:
                result = tx.run(query, **params)
                batch_results.append([dict(record) for record in result])
            return batch_results
        
        try:
            with self.driver.session(database=database) as session:
                results = session.execute_write(_batch_transaction)
                
                logger.info(f"Successfully executed batch of {len(queries)} queries")
                return {
                    'success': True,
                    'query_count': len(queries),
                    'results': results
                }
                
        except Exception as e:
            logger.error(f"Batch transaction failed: {type(e).__name__}: {e}")
            return {
                'success': False,
                'query_count': len(queries),
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def execute_with_timeout(
        self,
        query: str,
        timeout_seconds: int = 30,
        is_write: bool = False,
        **params
    ) -> List[Dict[str, Any]]:
        """
        Execute query with custom timeout
        
        Args:
            query: Cypher query to execute
            timeout_seconds: Query timeout in seconds
            is_write: Whether this is a write transaction
            **params: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        # Add timeout to query
        timeout_ms = timeout_seconds * 1000
        timed_query = f"CALL apoc.cypher.runTimeboxed('{query}', {params}, {timeout_ms})"
        
        try:
            return self._execute_with_retry(
                query=timed_query,
                is_write=is_write
            )
        except Exception as e:
            if "exceeded timeout" in str(e).lower():
                logger.error(f"Query exceeded timeout of {timeout_seconds}s")
                raise TimeoutError(f"Query execution exceeded {timeout_seconds}s timeout")
            raise


def run_query(
    driver: Driver, 
    query: str, 
    params: Optional[Dict[str, Any]] = None, 
    database: Optional[str] = None,
    is_write: bool = False
) -> List[Dict[str, Any]]:
    """
    Execute a Cypher query with retry logic (backwards compatibility)
    
    Args:
        driver: Neo4j driver instance
        query: Cypher query to execute
        params: Query parameters
        database: Database name
        is_write: Whether this is a write operation
        
    Returns:
        List of result records as dictionaries
    """
    manager = TransactionManager(driver)
    
    if is_write:
        return manager.execute_write(query, **(params or {}))
    else:
        return manager.execute_read(query, **(params or {}))