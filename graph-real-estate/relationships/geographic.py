"""
Geographic relationship builders for Neo4j.
"""

import logging
import time
from typing import Optional
from neo4j import Driver

from ..utils.database import run_query
from .config import RelationshipConfig, RelationshipResult

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
    
    def _execute_relationship_query(self, relationship_type: str, query: str, description: str = "") -> RelationshipResult:
        """
        Execute a relationship query with monitoring and error handling.
        
        Args:
            relationship_type: Type of relationship being created
            query: Cypher query to execute
            description: Optional description for logging
            
        Returns:
            RelationshipResult with execution details
        """
        start_time = time.time()
        
        try:
            if self.config.verbose:
                logger.debug(f"Executing {relationship_type}: {description}")
            
            result = run_query(self.driver, query)
            count = result[0]["count"] if result else 0
            execution_time = time.time() - start_time
            
            if self.config.enable_performance_monitoring:
                logger.info(f"✓ {relationship_type}: {count:,} relationships in {execution_time:.2f}s")
            
            return RelationshipResult(
                relationship_type=relationship_type,
                count=count,
                success=True,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Failed to create {relationship_type} relationships: {str(e)}"
            logger.error(error_msg)
            
            return RelationshipResult(
                relationship_type=relationship_type,
                count=0,
                success=False,
                error_message=error_msg,
                execution_time=execution_time
            )
    
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
        
        result = self._execute_relationship_query(
            "LOCATED_IN", 
            query, 
            "Properties -> Neighborhoods"
        )
        return result.count
    
    def create_in_zip_code(self) -> int:
        """
        Create IN_ZIP_CODE relationships between Properties and ZipCodes.
        
        Returns:
            Number of relationships created
        """
        query = """
        MATCH (p:Property)
        WHERE p.zip_code IS NOT NULL
        MATCH (z:ZipCode {id: p.zip_code})
        MERGE (p)-[:IN_ZIP_CODE]->(z)
        RETURN count(*) as count
        """
        
        result = self._execute_relationship_query(
            "IN_ZIP_CODE", 
            query, 
            "Properties -> ZipCodes"
        )
        return result.count
    
    def create_neighborhood_in_zip(self) -> int:
        """
        Create IN_ZIP_CODE relationships between Neighborhoods and ZipCodes.
        Uses Properties as intermediary to determine neighborhood -> zipcode mapping.
        
        Returns:
            Number of relationships created
        """
        query = """
        MATCH (n:Neighborhood)
        WHERE n.neighborhood_id IS NOT NULL
        MATCH (p:Property {neighborhood_id: n.neighborhood_id})
        WHERE p.zip_code IS NOT NULL
        MATCH (z:ZipCode {id: p.zip_code})
        WITH n, z
        MERGE (n)-[:IN_ZIP_CODE]->(z)
        RETURN count(DISTINCT z) as count
        """
        
        result = self._execute_relationship_query(
            "IN_ZIP_CODE", 
            query, 
            "Neighborhoods -> ZipCodes"
        )
        return result.count
    
    def create_zip_in_city(self) -> int:
        """
        Create IN_CITY relationships between ZipCodes and Cities.
        Uses Properties to determine zipcode -> city mapping.
        
        Returns:
            Number of relationships created
        """
        query = """
        MATCH (z:ZipCode)
        MATCH (p:Property)
        WHERE (p.city_normalized IS NOT NULL OR p.city_standardized IS NOT NULL) 
          AND p.state_standardized IS NOT NULL
        MATCH (c:City)
        WHERE (c.name = p.city_normalized OR c.name = p.city_standardized)
          AND c.state = p.state_standardized
        WITH z, c
        MERGE (z)-[:IN_CITY]->(c)
        RETURN count(DISTINCT c) as count
        """
        
        result = self._execute_relationship_query(
            "IN_CITY", 
            query, 
            "ZipCodes -> Cities"
        )
        return result.count
    
    def create_city_in_county(self) -> int:
        """
        Create IN_COUNTY relationships between Cities and Counties.
        Uses Properties to determine city -> county mapping.
        
        Returns:
            Number of relationships created
        """
        query = """
        MATCH (c:City)
        MATCH (p:Property)
        WHERE (p.city_normalized = c.name OR p.city_standardized = c.name)
          AND p.state_standardized = c.state
          AND p.county IS NOT NULL
        MATCH (co:County {name: p.county, state: c.state})
        WITH c, co
        MERGE (c)-[:IN_COUNTY]->(co)
        RETURN count(DISTINCT co) as count
        """
        
        result = self._execute_relationship_query(
            "IN_COUNTY", 
            query, 
            "Cities -> Counties"
        )
        return result.count
    
    def create_county_in_state(self) -> int:
        """
        Create IN_STATE relationships between Counties and States.
        
        Returns:
            Number of relationships created
        """
        query = """
        MATCH (co:County)
        WHERE co.state IS NOT NULL
        MATCH (s:State {abbreviation: co.state})
        MERGE (co)-[:IN_STATE]->(s)
        RETURN count(*) as count
        """
        
        result = self._execute_relationship_query(
            "IN_STATE", 
            query, 
            "Counties -> States"
        )
        return result.count
    
    def create_near(self) -> int:
        """
        Create NEAR relationships between Neighborhoods in the same city.
        Uses the new geographic hierarchy through ZIP codes.
        
        Returns:
            Number of relationships created
        """
        # Create bidirectional NEAR relationships between neighborhoods in same city
        query = """
        MATCH (n1:Neighborhood)-[:IN_ZIP_CODE]->(:ZipCode)-[:IN_CITY]->(c:City)
        MATCH (n2:Neighborhood)-[:IN_ZIP_CODE]->(:ZipCode)-[:IN_CITY]->(c)
        WHERE n1.neighborhood_id < n2.neighborhood_id
        MERGE (n1)-[:NEAR]->(n2)
        MERGE (n2)-[:NEAR]->(n1)
        RETURN count(*) * 2 as count
        """
        
        result = self._execute_relationship_query(
            "NEAR", 
            query, 
            "Neighborhoods <-> Neighborhoods (bidirectional)"
        )
        return result.count