"""Neo4j connection management with singleton pattern and proper lifecycle"""
import os
import atexit
import logging
from typing import Optional
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env', override=True)

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
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        username = os.getenv('NEO4J_USERNAME', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'password')
        
        try:
            self._driver = GraphDatabase.driver(
                uri,
                auth=(username, password),
                max_connection_lifetime=3600,  # 1 hour
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,
                connection_timeout=30,
                keep_alive=True
            )
            
            # Register cleanup
            atexit.register(self.close)
            
            # Verify connectivity
            self.verify_connectivity()
            
            logger.info(f"Neo4j driver initialized successfully to {uri}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {e}")
            raise
    
    def verify_connectivity(self):
        """Verify database connectivity"""
        try:
            with self._driver.session() as session:
                result = session.run("RETURN 1 as test").single()
                if result['test'] != 1:
                    raise Exception("Connectivity test failed")
            logger.info("Neo4j connection verified")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def get_driver(self):
        """Get the driver instance"""
        if self._driver is None:
            self._initialize_driver()
        return self._driver
    
    def close(self):
        """Close the driver connection"""
        if self._driver:
            try:
                self._driver.close()
                self._driver = None
                logger.info("Neo4j driver closed successfully")
            except Exception as e:
                logger.error(f"Error closing Neo4j driver: {e}")
    
    def health_check(self) -> bool:
        """Check if the connection is healthy"""
        try:
            with self._driver.session() as session:
                session.run("RETURN 1").single()
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def get_database_info(self) -> dict:
        """Get database server information"""
        try:
            with self._driver.session() as session:
                result = session.run("""
                    CALL dbms.components() 
                    YIELD name, versions, edition
                    RETURN name, versions[0] as version, edition
                """).single()
                
                return {
                    'name': result['name'],
                    'version': result['version'],
                    'edition': result['edition']
                }
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {}


# Global connection instance
neo4j_connection = Neo4jConnection()


def get_neo4j_driver():
    """Get Neo4j driver instance (backwards compatibility)"""
    return neo4j_connection.get_driver()


def close_neo4j_driver(driver=None):
    """Close Neo4j driver connection (backwards compatibility)"""
    neo4j_connection.close()


def verify_neo4j_health() -> bool:
    """Verify Neo4j connection health"""
    return neo4j_connection.health_check()