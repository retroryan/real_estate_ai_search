"""Neo4j connection management with singleton pattern and proper lifecycle"""
import atexit
import logging
from typing import Optional
from neo4j import GraphDatabase
from config.settings import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jConnection:
    """Singleton Neo4j driver manager with proper lifecycle management"""
    
    _instance: Optional['Neo4jConnection'] = None
    _driver: Optional[GraphDatabase.driver] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._driver is None:
            self._initialize_driver()
    
    def _initialize_driver(self):
        """Initialize driver with proper configuration"""
        settings = get_settings()
        db_config = settings.database
        
        try:
            self._driver = GraphDatabase.driver(
                db_config.uri,
                auth=(db_config.user, db_config.password),
                max_connection_lifetime=3600,  # 1 hour
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,
                connection_timeout=30,
                keep_alive=True
            )
            
            # Register cleanup
            atexit.register(self.close)
            
            # Verify connection
            with self._driver.session(database=db_config.database) as session:
                session.run("RETURN 1")
                logger.info("Neo4j connection verified")
            
            logger.info(f"Neo4j driver initialized successfully to {db_config.uri}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self._driver = None
            raise
    
    @property
    def driver(self):
        """Get the driver instance"""
        if self._driver is None:
            self._initialize_driver()
        return self._driver
    
    def close(self):
        """Close the driver connection"""
        if self._driver:
            try:
                self._driver.close()
                logger.info("Neo4j driver closed successfully")
            except Exception as e:
                logger.error(f"Error closing Neo4j driver: {e}")
            finally:
                self._driver = None
    
    def reset(self):
        """Reset the connection (close and reinitialize)"""
        self.close()
        self._initialize_driver()


# Global connection instance
_connection = Neo4jConnection()


def get_driver():
    """Get the Neo4j driver instance"""
    return _connection.driver


def get_neo4j_driver():
    """Get the Neo4j driver instance (alias for compatibility)"""
    return get_driver()


def close_driver():
    """Close the Neo4j driver"""
    _connection.close()


def close_neo4j_driver():
    """Close the Neo4j driver (alias for compatibility)"""
    close_driver()


def reset_connection():
    """Reset the Neo4j connection"""
    _connection.reset()