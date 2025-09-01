"""
Geographic relationship builders for Neo4j.

This module only handles complex geographic relationships not covered by the pipeline.
Basic relationships (LOCATED_IN, IN_ZIP_CODE, IN_CITY, IN_COUNTY, IN_STATE) are 
created by squack_pipeline_v2.
"""

import logging
import time
from typing import Optional
from neo4j import Driver

from graph_real_estate.utils.database import run_query
from graph_real_estate.relationships.config import RelationshipConfig, RelationshipResult

logger = logging.getLogger(__name__)


class GeographicRelationshipBuilder:
    """Handles creation of complex geographic relationships."""
    
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
    
    def create_near(self) -> int:
        """
        Create NEAR relationships between Neighborhoods in the same city.
        
        This creates bidirectional NEAR relationships between neighborhoods
        that share the same city through the geographic hierarchy.
        
        Returns:
            Number of relationships created
        """
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