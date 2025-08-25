"""Base loader class with common functionality"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from datetime import datetime

from database import get_neo4j_driver, run_query, close_neo4j_driver
from neo4j import Driver


class BaseLoader(ABC):
    """Abstract base class for all data loaders"""
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize base loader"""
        # Go up to real_estate_ai_search directory
        self.base_path = base_path or Path(__file__).parent.parent.parent.parent
        self.driver: Optional[Driver] = None
        self.logger = self._setup_logger()
        self.stats: Dict[str, Any] = {}
        self.start_time: Optional[datetime] = None
        
    def _setup_logger(self) -> logging.Logger:
        """Set up logging for the loader"""
        logger_name = self.__class__.__name__
        logger = logging.getLogger(logger_name)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def connect(self) -> None:
        """Establish database connection"""
        try:
            self.driver = get_neo4j_driver()
            self.logger.info("Database connection established")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close database connection"""
        if self.driver:
            try:
                close_neo4j_driver(self.driver)
                self.logger.info("Database connection closed")
            except Exception as e:
                self.logger.error(f"Error closing database connection: {e}")
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict]]:
        """Execute a Cypher query with error handling"""
        if not self.driver:
            raise RuntimeError("Database connection not established")
        
        try:
            result = run_query(self.driver, query, params or {})
            return result
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            self.logger.debug(f"Query: {query}")
            self.logger.debug(f"Params: {params}")
            raise
    
    def batch_execute(self, query: str, batch_data: List[Dict], batch_size: int = 1000) -> int:
        """Execute query in batches for better performance"""
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
                self.execute_query(batch_query, {'batch': batch})
                total_processed += len(batch)
                
                if (i + batch_size) % (batch_size * 10) == 0:
                    self.logger.info(f"Processed {total_processed}/{len(batch_data)} items")
                    
            except Exception as e:
                self.logger.error(f"Batch execution failed at index {i}: {e}")
                raise
        
        return total_processed
    
    def create_constraint(self, constraint_name: str, query: str) -> bool:
        """Create a database constraint"""
        try:
            self.execute_query(query)
            self.logger.info(f"Created constraint: {constraint_name}")
            return True
        except Exception as e:
            if "already exists" in str(e).lower():
                self.logger.debug(f"Constraint already exists: {constraint_name}")
            else:
                self.logger.error(f"Failed to create constraint {constraint_name}: {e}")
            return False
    
    def create_index(self, index_name: str, query: str) -> bool:
        """Create a database index"""
        try:
            self.execute_query(query)
            self.logger.info(f"Created index: {index_name}")
            return True
        except Exception as e:
            if "already exists" in str(e).lower():
                self.logger.debug(f"Index already exists: {index_name}")
            else:
                self.logger.error(f"Failed to create index {index_name}: {e}")
            return False
    
    def count_nodes(self, label: str) -> int:
        """Count nodes with a specific label"""
        query = f"MATCH (n:{label}) RETURN count(n) as count"
        result = self.execute_query(query)
        return result[0]['count'] if result else 0
    
    def count_relationships(self, rel_type: Optional[str] = None) -> int:
        """Count relationships of a specific type"""
        if rel_type:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
        else:
            query = "MATCH ()-[r]->() RETURN count(r) as count"
        
        result = self.execute_query(query)
        return result[0]['count'] if result else 0
    
    @abstractmethod
    def load(self) -> Any:
        """Abstract method to be implemented by subclasses"""
        pass
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            self.logger.info(f"Execution time: {duration:.2f} seconds")
        
        self.disconnect()