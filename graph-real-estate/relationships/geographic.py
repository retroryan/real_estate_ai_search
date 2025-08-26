"""
Geographic relationship builders for Neo4j.
"""

import logging
from typing import Optional
from neo4j import Driver

from utils.database import run_query
from relationships.config import RelationshipConfig

logger = logging.getLogger(__name__)


class GeographicRelationshipBuilder:
    """Handles creation of geographic relationships."""
    
    def __init__(self, driver: Driver, config: Optional[RelationshipConfig] = None):
        """
        Initialize the geographic relationship builder.
        
        Args:
            driver: Neo4j driver instance
            config: Relationship configuration
        """
        self.driver = driver
        self.config = config or RelationshipConfig()
    
    def create_located_in(self) -> int:
        """
        Create LOCATED_IN relationships between Properties and Neighborhoods.
        
        Returns:
            Number of relationships created
        """
        query = """
        MATCH (p:Property)
        WHERE p.neighborhood_id IS NOT NULL
        MATCH (n:Neighborhood {neighborhood_id: p.neighborhood_id})
        MERGE (p)-[:LOCATED_IN]->(n)
        RETURN count(*) as count
        """
        
        if self.config.verbose:
            logger.debug("Creating LOCATED_IN relationships...")
        
        result = run_query(self.driver, query)
        return result[0]["count"] if result else 0
    
    def create_in_city(self) -> int:
        """
        Create IN_CITY relationships between Neighborhoods and Cities.
        
        Returns:
            Number of relationships created
        """
        query = """
        MATCH (n:Neighborhood)
        WHERE n.city IS NOT NULL
        MATCH (c:City {name: n.city})
        MERGE (n)-[:IN_CITY]->(c)
        RETURN count(*) as count
        """
        
        if self.config.verbose:
            logger.debug("Creating IN_CITY relationships...")
        
        result = run_query(self.driver, query)
        return result[0]["count"] if result else 0
    
    def create_in_county(self) -> int:
        """
        Create IN_COUNTY relationships between Cities and Counties.
        
        Returns:
            Number of relationships created
        """
        query = """
        MATCH (c:City)
        WHERE c.county IS NOT NULL
        MATCH (co:County {name: c.county})
        MERGE (c)-[:IN_COUNTY]->(co)
        RETURN count(*) as count
        """
        
        if self.config.verbose:
            logger.debug("Creating IN_COUNTY relationships...")
        
        result = run_query(self.driver, query)
        return result[0]["count"] if result else 0
    
    def create_near(self) -> int:
        """
        Create NEAR relationships between Neighborhoods in the same city.
        
        Returns:
            Number of relationships created
        """
        # Create bidirectional NEAR relationships between neighborhoods in same city
        query = """
        MATCH (n1:Neighborhood)-[:IN_CITY]->(c:City)<-[:IN_CITY]-(n2:Neighborhood)
        WHERE n1.neighborhood_id < n2.neighborhood_id
        MERGE (n1)-[:NEAR]->(n2)
        MERGE (n2)-[:NEAR]->(n1)
        RETURN count(*) * 2 as count
        """
        
        if self.config.verbose:
            logger.debug("Creating NEAR relationships...")
        
        result = run_query(self.driver, query)
        return result[0]["count"] if result else 0