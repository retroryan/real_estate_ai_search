"""
Neo4j writer orchestrator.

This module coordinates entity-specific Neo4j writers to create the complete
graph structure with proper dependencies between entity types.
"""

import logging
from typing import Any, Dict

from pyspark.sql import DataFrame, SparkSession

from data_pipeline.config.models import Neo4jConfig
from data_pipeline.writers.base import DataWriter
from data_pipeline.writers.neo4j.neo4j_properties import PropertyNeo4jWriter
from data_pipeline.writers.neo4j.neo4j_neighborhoods import NeighborhoodNeo4jWriter
from data_pipeline.writers.neo4j.neo4j_wikipedia import WikipediaNeo4jWriter

logger = logging.getLogger(__name__)


class Neo4jOrchestrator(DataWriter):
    """
    Orchestrator for entity-specific Neo4j writers.
    
    This writer coordinates the entity-specific writers to create the complete
    graph structure with proper write ordering and dependencies.
    """
    
    def __init__(self, config: Neo4jConfig, spark: SparkSession):
        """
        Initialize the Neo4j orchestrator.
        
        Args:
            config: Neo4j configuration
            spark: SparkSession instance
        """
        super().__init__(config)
        self.config = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
        
        # Neo4j Spark connector format
        self.format_string = "org.neo4j.spark.DataSource"
        
        # Initialize entity-specific writers
        self.property_writer = PropertyNeo4jWriter(config, spark)
        self.neighborhood_writer = NeighborhoodNeo4jWriter(config, spark)
        self.wikipedia_writer = WikipediaNeo4jWriter(config, spark)
    
    def validate_connection(self) -> bool:
        """
        Validate the connection to Neo4j.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            test_df = (self.spark.read
                      .format(self.format_string)
                      .option("url", self.config.uri)
                      .option("authentication.basic.username", self.config.username)
                      .option("authentication.basic.password", self.config.get_password() or "")
                      .option("database", self.config.database)
                      .option("query", "RETURN 1 as test")
                      .load())
            
            test_df.collect()
            self.logger.info(f"Successfully validated Neo4j connection to {self.config.uri}")
            return True
            
        except Exception as e:
            self.logger.error(f"Neo4j connection validation failed: {e}")
            return False
    
    def write(self, data: Dict[str, DataFrame], metadata: Dict[str, Any]) -> bool:
        """
        Write complete graph structure to Neo4j using entity-specific writers.
        
        Args:
            data: Dictionary with keys 'properties', 'neighborhoods', 'wikipedia' mapped to DataFrames
            metadata: Metadata about the data being written
            
        Returns:
            True if write was successful, False otherwise
        """
        try:
            # Clear database if configured
            if self.config.clear_before_write:
                self._clear_database()
            
            return self._write_entities(data, metadata)
            
        except Exception as e:
            self.logger.error(f"Failed to write graph to Neo4j: {e}")
            return False
    
    def _write_entities(self, data: Dict[str, DataFrame], metadata: Dict[str, Any]) -> bool:
        """
        Write entities in proper dependency order.
        
        Args:
            data: Dictionary with entity DataFrames
            metadata: Metadata about the data
            
        Returns:
            True if all writes successful
        """
        success = True
        
        # Write neighborhoods first (creates City and State nodes)
        if "neighborhoods" in data:
            self.logger.info("Writing neighborhoods to Neo4j...")
            if not self.neighborhood_writer.write(data["neighborhoods"], metadata):
                self.logger.error("Failed to write neighborhoods")
                success = False
        
        # Write properties (depends on neighborhoods for relationships)
        if "properties" in data:
            self.logger.info("Writing properties to Neo4j...")
            if not self.property_writer.write(data["properties"], metadata):
                self.logger.error("Failed to write properties")
                success = False
        
        # Write Wikipedia articles (can reference cities created by neighborhoods)
        if "wikipedia" in data:
            self.logger.info("Writing Wikipedia articles to Neo4j...")
            if not self.wikipedia_writer.write(data["wikipedia"], metadata):
                self.logger.error("Failed to write Wikipedia articles")
                success = False
        
        if success:
            self.logger.info("Neo4j graph write completed successfully")
        return success
    
    def _clear_database(self) -> None:
        """
        Clear all nodes and relationships from the database.
        
        This is for demo purposes to ensure a clean state.
        """
        try:
            self.logger.info("Clearing Neo4j database...")
            
            # Use a dummy DataFrame to execute the delete query
            dummy_df = self.spark.createDataFrame([(1,)], ["dummy"])
            
            (dummy_df.write
             .format(self.format_string)
             .mode("overwrite")
             .option("url", self.config.uri)
             .option("authentication.basic.username", self.config.username)
             .option("authentication.basic.password", self.config.get_password() or "")
             .option("database", self.config.database)
             .option("query", "MATCH (n) DETACH DELETE n")
             .save())
            
            self.logger.info("Neo4j database cleared")
            
        except Exception as e:
            self.logger.warning(f"Failed to clear database (may be empty): {e}")
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "neo4j_orchestrator"