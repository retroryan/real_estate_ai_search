"""
Neo4j writer implementation using the Neo4j Spark Connector.

This module provides a writer that uses the official Neo4j Spark Connector
to write DataFrames to a Neo4j graph database.
"""

import logging
from typing import Any, Dict

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col

from data_pipeline.config.models import Neo4jConfig
from data_pipeline.writers.base import DataWriter

logger = logging.getLogger(__name__)


class Neo4jWriter(DataWriter):
    """
    Neo4j graph database writer using the official Spark connector.
    
    This writer uses the Neo4j Spark Connector to write DataFrames
    as nodes to a Neo4j database. It supports clearing the database
    before writing (for demo purposes) and handles different entity types.
    """
    
    def __init__(self, config: Neo4jConfig, spark: SparkSession):
        """
        Initialize the Neo4j writer.
        
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
    
    def validate_connection(self) -> bool:
        """
        Validate the connection to Neo4j.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Test connection with a simple read query
            test_df = (self.spark.read
                      .format(self.format_string)
                      .option("url", self.config.uri)
                      .option("authentication.basic.username", self.config.username)
                      .option("authentication.basic.password", self.config.get_password() or "")
                      .option("database", self.config.database)
                      .option("query", "RETURN 1 as test")
                      .load())
            
            # Force evaluation to test connection
            test_df.collect()
            
            self.logger.info(f"Successfully validated Neo4j connection to {self.config.uri}")
            return True
            
        except Exception as e:
            self.logger.error(f"Neo4j connection validation failed: {e}")
            return False
    
    def write(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write DataFrame to Neo4j as nodes.
        
        Args:
            df: DataFrame to write
            metadata: Metadata about the data being written
            
        Returns:
            True if write was successful, False otherwise
        """
        try:
            # Clear database if configured
            if self.config.clear_before_write:
                self._clear_database()
            
            # Write each entity type as nodes with appropriate labels
            entity_types = [
                ("property", "Property"),
                ("neighborhood", "Neighborhood"),
                ("wikipedia", "WikipediaArticle")
            ]
            
            for entity_type, label in entity_types:
                entity_df = df.filter(col("entity_type") == entity_type)
                count = entity_df.count()
                
                if count > 0:
                    self.logger.info(f"Writing {count} {entity_type} nodes to Neo4j...")
                    self._write_nodes(entity_df, label)
                    self.logger.info(f"Successfully wrote {count} {entity_type} nodes")
            
            self.logger.info("Neo4j write completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write to Neo4j: {e}")
            return False
    
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
    
    def _write_nodes(self, df: DataFrame, label: str) -> None:
        """
        Write DataFrame as nodes with the specified label.
        
        Args:
            df: DataFrame to write
            label: Node label to apply
        """
        # Prepare DataFrame for Neo4j by removing entity_type column
        neo4j_df = df.drop("entity_type") if "entity_type" in df.columns else df
        
        # Write nodes using the Neo4j Spark connector
        (neo4j_df.write
         .format(self.format_string)
         .mode("append")  # Always append since we clear first if needed
         .option("url", self.config.uri)
         .option("authentication.basic.username", self.config.username)
         .option("authentication.basic.password", self.config.get_password() or "")
         .option("database", self.config.database)
         .option("labels", f":{label}")
         .option("batch.size", str(self.config.transaction_size))
         .save())
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "neo4j"