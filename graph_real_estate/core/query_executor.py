"""Query executor implementation for database operations"""

from typing import List, Dict, Any, Optional
import logging
from neo4j import Driver, Transaction
from neo4j.exceptions import Neo4jError, TransientError
import time


class QueryExecutor:
    """Executes database queries with proper error handling and retry logic"""
    
    def __init__(self, driver: Driver, database: str = "neo4j", max_retries: int = 3):
        """
        Initialize query executor
        
        Args:
            driver: Neo4j driver instance
            database: Database name
            max_retries: Maximum number of retries for transient errors
        """
        self.driver = driver
        self.database = database
        self.max_retries = max_retries
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a query (auto-detects read vs write)
        
        Args:
            query: Cypher query string
            params: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        # Determine if this is a write operation
        write_keywords = ['CREATE', 'DELETE', 'SET', 'MERGE', 'REMOVE', 'DETACH', 'DROP']
        is_write = any(keyword in query.upper() for keyword in write_keywords)
        
        if is_write:
            return self.execute_write(query, params)
        else:
            return self.execute_read(query, params)
    
    def execute_read(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a read transaction
        
        Args:
            query: Cypher query string
            params: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        def work(tx: Transaction) -> List[Dict[str, Any]]:
            result = tx.run(query, **(params or {}))
            return [dict(record) for record in result]
        
        return self._execute_with_retry(work, write=False)
    
    def execute_write(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a write transaction
        
        Args:
            query: Cypher query string
            params: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        def work(tx: Transaction) -> List[Dict[str, Any]]:
            result = tx.run(query, **(params or {}))
            return [dict(record) for record in result]
        
        return self._execute_with_retry(work, write=True)
    
    def batch_execute(self, query: str, batch_data: List[Dict], batch_size: int = 1000) -> int:
        """
        Execute query in batches for better performance
        
        Args:
            query: Cypher query template (should use 'item' variable)
            batch_data: List of dictionaries to process
            batch_size: Size of each batch
            
        Returns:
            Number of items processed
        """
        if not batch_data:
            return 0
        
        total_processed = 0
        
        for i in range(0, len(batch_data), batch_size):
            batch = batch_data[i:i + batch_size]
            
            batch_query = f"""
            UNWIND $batch AS item
            {query}
            """
            
            try:
                self.execute_write(batch_query, {'batch': batch})
                total_processed += len(batch)
                
                # Log progress for large batches
                if len(batch_data) > batch_size * 10 and (i + batch_size) % (batch_size * 10) == 0:
                    self.logger.info(f"Processed {total_processed}/{len(batch_data)} items")
                    
            except Exception as e:
                self.logger.error(f"Batch execution failed at index {i}: {e}")
                raise
        
        return total_processed
    
    def _execute_with_retry(self, work, write: bool = False) -> List[Dict[str, Any]]:
        """
        Execute work function with retry logic for transient errors
        
        Args:
            work: Function to execute within transaction
            write: Whether this is a write transaction
            
        Returns:
            Result from work function
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                with self.driver.session(database=self.database) as session:
                    if write:
                        return session.execute_write(work)
                    else:
                        return session.execute_read(work)
                        
            except TransientError as e:
                last_error = e
                wait_time = 2 ** attempt  # Exponential backoff
                self.logger.warning(
                    f"Transient error on attempt {attempt + 1}/{self.max_retries}: {e}. "
                    f"Retrying in {wait_time} seconds..."
                )
                time.sleep(wait_time)
                
            except Neo4jError as e:
                self.logger.error(f"Neo4j error: {e}")
                raise
                
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                raise
        
        # If we've exhausted all retries
        self.logger.error(f"Failed after {self.max_retries} attempts")
        raise last_error
    
    def create_constraint(self, name: str, query: str) -> bool:
        """
        Create a database constraint
        
        Args:
            name: Constraint name for logging
            query: Constraint creation query
            
        Returns:
            True if created or already exists, False on error
        """
        try:
            self.execute_write(query)
            self.logger.info(f"Created constraint: {name}")
            return True
        except Exception as e:
            if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                self.logger.debug(f"Constraint already exists: {name}")
                return True
            else:
                self.logger.error(f"Failed to create constraint {name}: {e}")
                return False
    
    def create_index(self, name: str, query: str) -> bool:
        """
        Create a database index
        
        Args:
            name: Index name for logging
            query: Index creation query
            
        Returns:
            True if created or already exists, False on error
        """
        try:
            self.execute_write(query)
            self.logger.info(f"Created index: {name}")
            return True
        except Exception as e:
            if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                self.logger.debug(f"Index already exists: {name}")
                return True
            else:
                self.logger.error(f"Failed to create index {name}: {e}")
                return False
    
    def count_nodes(self, label: str = "") -> int:
        """
        Count nodes with a specific label
        
        Args:
            label: Node label (empty string for all nodes)
            
        Returns:
            Number of nodes
        """
        if label:
            query = f"MATCH (n:{label}) RETURN count(n) as count"
        else:
            query = "MATCH (n) RETURN count(n) as count"
        result = self.execute_read(query)
        return result[0]['count'] if result else 0
    
    def count_relationships(self, rel_type: Optional[str] = None) -> int:
        """
        Count relationships of a specific type
        
        Args:
            rel_type: Relationship type (None for all relationships)
            
        Returns:
            Number of relationships
        """
        if rel_type:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
        else:
            query = "MATCH ()-[r]->() RETURN count(r) as count"
        
        result = self.execute_read(query)
        return result[0]['count'] if result else 0
    
    def clear_database(self) -> None:
        """Clear all nodes and relationships from database"""
        query = "MATCH (n) DETACH DELETE n"
        self.execute_write(query)
        self.logger.info("Database cleared")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get database statistics
        
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        # Node counts
        node_labels = [
            "Property", "Neighborhood", "City", "County", "State",
            "WikipediaArticle", "Feature", "PropertyType", "PriceRange"
        ]
        
        for label in node_labels:
            stats[f"nodes_{label}"] = self.count_nodes(label)
        
        # Relationship counts
        rel_types = [
            "IN_NEIGHBORHOOD", "IN_CITY", "IN_COUNTY", "IN_STATE",
            "HAS_FEATURE", "OF_TYPE", "IN_PRICE_RANGE",
            "NEAR", "NEAR_BY", "DESCRIBES", "RELEVANT_TO"
        ]
        
        for rel_type in rel_types:
            stats[f"relationships_{rel_type}"] = self.count_relationships(rel_type)
        
        # Total counts
        stats["total_nodes"] = self.count_nodes("")  # All nodes
        stats["total_relationships"] = self.count_relationships()  # All relationships
        
        return stats