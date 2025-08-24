"""
Neo4j writer orchestrator for entity-specific graph creation.

This module coordinates entity-specific Neo4j writers to create the complete
graph structure with proper dependencies between entity types.
"""

import logging
import time
from typing import Dict

from pyspark.sql import DataFrame, SparkSession

from data_pipeline.config.models import Neo4jConfig
from data_pipeline.writers.base import DataWriter
from data_pipeline.models.writer_models import WriteMetadata

logger = logging.getLogger(__name__)


class Neo4jOrchestrator(DataWriter):
    """
    Orchestrator for entity-specific Neo4j writers.
    
    Routes each entity type to its dedicated Neo4j writer.
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
        
        # FAIL FAST - Check for required session-level configuration
        spark_conf = spark.sparkContext.getConf()
        if not spark_conf.contains("neo4j.url"):
            raise ValueError(
                "Neo4j configuration not found in SparkSession. "
                "Neo4j must be configured at session level for proper connection pooling. "
                "Ensure neo4j.* configs are set when creating SparkSession."
            )
        
        # Neo4j Spark connector format
        self.format_string = "org.neo4j.spark.DataSource"
    
    def validate_connection(self) -> bool:
        """
        Validate the connection to Neo4j.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Connection config comes from SparkSession, only need query
            test_df = (self.spark.read
                      .format(self.format_string)
                      .option("query", "RETURN 1 as test")
                      .load())
            
            test_df.collect()
            self.logger.info(f"Successfully validated Neo4j connection")
            return True
            
        except Exception as e:
            self.logger.error(f"Neo4j connection validation failed: {e}")
            return False
    
    def write(self, df: DataFrame, metadata: WriteMetadata) -> bool:
        """
        Write entity-specific DataFrame to Neo4j.
        
        Args:
            df: DataFrame to write
            metadata: WriteMetadata with entity type and other information
            
        Returns:
            True if write was successful, False otherwise
        """
        entity_type = metadata.entity_type.value.lower()
        
        if entity_type == "property":
            return self._write_properties(df, metadata)
        elif entity_type == "neighborhood":
            return self._write_neighborhoods(df, metadata)
        elif entity_type == "wikipedia":
            return self._write_wikipedia(df, metadata)
        else:
            self.logger.error(f"Unknown entity type: {entity_type}")
            return False
    
    def _write_nodes(self, df: DataFrame, label: str, key_field: str) -> bool:
        """
        Generic node writer with common logic and progress tracking.
        
        Args:
            df: DataFrame to write
            label: Node label
            key_field: Primary key field
            
        Returns:
            True if successful
        """
        try:
            record_count = df.count()
            self.logger.info(f"📊 Starting write of {record_count:,} {label} nodes to Neo4j")
            
            # Log sample records for verification
            if record_count > 0:
                self.logger.debug(f"   Sample {label} fields: {df.columns[:5]}")
            
            # Track start time for performance metrics
            start_time = time.time()
            
            # Connection config comes from SparkSession
            writer = df.write.format(self.format_string).mode("append")
            
            # Only set data-specific options
            writer = writer.option("labels", f":{label}")
            writer = writer.option("node.keys", key_field)
            
            # Use coalesce for better batch control if large dataset
            if record_count > 10000:
                self.logger.info(f"   Large dataset detected, optimizing partitions...")
                df = df.coalesce(10)
                writer = df.write.format(self.format_string).mode("append")
                writer = writer.option("labels", f":{label}")
                writer = writer.option("node.keys", key_field)
            
            writer.save()
            
            # Calculate and log performance metrics
            elapsed_time = time.time() - start_time
            records_per_second = record_count / elapsed_time if elapsed_time > 0 else 0
            
            self.logger.info(
                f"✅ Successfully wrote {record_count:,} {label} nodes in {elapsed_time:.2f}s "
                f"({records_per_second:.0f} records/sec)"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to write {label} nodes: {e}")
            return False
    
    def _write_properties(self, df: DataFrame, metadata: WriteMetadata) -> bool:
        """
        Write property nodes to Neo4j.
        
        Args:
            df: Property DataFrame
            metadata: Write metadata
            
        Returns:
            True if successful
        """
        if self.config.clear_before_write:
            self._clear_entity("Property")
        
        return self._write_nodes(df, "Property", "listing_id")
    
    def _write_neighborhoods(self, df: DataFrame, metadata: WriteMetadata) -> bool:
        """
        Write neighborhood nodes to Neo4j.
        
        Args:
            df: Neighborhood DataFrame
            metadata: Write metadata
            
        Returns:
            True if successful
        """
        if self.config.clear_before_write:
            self._clear_entity("Neighborhood")
        
        return self._write_nodes(df, "Neighborhood", "neighborhood_id")
    
    def _write_wikipedia(self, df: DataFrame, metadata: WriteMetadata) -> bool:
        """
        Write Wikipedia article nodes to Neo4j.
        
        Args:
            df: Wikipedia DataFrame
            metadata: Write metadata
            
        Returns:
            True if successful
        """
        if self.config.clear_before_write:
            self._clear_entity("WikipediaArticle")
        
        return self._write_nodes(df, "WikipediaArticle", "page_id")
    
    def write_relationships(self, relationships_df: DataFrame, relationship_type: str) -> bool:
        """
        Write relationship DataFrame to Neo4j with progress tracking and error handling.
        
        Args:
            relationships_df: DataFrame containing relationship data
            relationship_type: Type of relationship (LOCATED_IN, DESCRIBES, etc.)
            
        Returns:
            True if successful
        """
        try:
            if relationships_df is None or relationships_df.count() == 0:
                self.logger.warning(f"⚠️ No {relationship_type} relationships to write")
                return True
            
            record_count = relationships_df.count()
            self.logger.info(f"🔗 Starting write of {record_count:,} {relationship_type} relationships")
            
            # Track start time
            start_time = time.time()
            
            # Get relationship configuration
            relationship_config = self._get_relationship_config(relationship_type)
            
            if not relationship_config:
                self.logger.error(f"❌ Unknown relationship type: {relationship_type}")
                return False
            
            # Validate that source and target nodes exist (sample check)
            if record_count > 0:
                sample = relationships_df.limit(1).collect()[0]
                self.logger.debug(
                    f"   Sample relationship: {sample.get('from_id', 'N/A')} -> "
                    f"{sample.get('to_id', 'N/A')}"
                )
            
            # Connection config comes from SparkSession
            writer = relationships_df.write.format(self.format_string).mode("append")
            
            # Only set relationship-specific options
            writer = (writer
                .option("relationship", relationship_type)
                .option("relationship.save.strategy", "keys")
                .option("relationship.source.labels", relationship_config["source_labels"])
                .option("relationship.source.save.mode", "Match")
                .option("relationship.source.node.keys", relationship_config["source_keys"])
                .option("relationship.target.labels", relationship_config["target_labels"])
                .option("relationship.target.save.mode", "Match")
                .option("relationship.target.node.keys", relationship_config["target_keys"]))
            
            writer.save()
            
            # Calculate performance metrics
            elapsed_time = time.time() - start_time
            relationships_per_second = record_count / elapsed_time if elapsed_time > 0 else 0
            
            self.logger.info(
                f"✅ Successfully wrote {record_count:,} {relationship_type} relationships "
                f"in {elapsed_time:.2f}s ({relationships_per_second:.0f} relationships/sec)"
            )
            return True
            
        except Exception as e:
            # Provide more context about the error
            error_msg = str(e)
            if "node" in error_msg.lower() and "not found" in error_msg.lower():
                self.logger.error(
                    f"❌ Failed to write {relationship_type} relationships - "
                    f"Some referenced nodes may not exist. Ensure all nodes are written first."
                )
                self.logger.debug(f"   Full error: {e}")
            else:
                self.logger.error(f"❌ Failed to write {relationship_type} relationships: {e}")
            return False
    
    def _get_relationship_config(self, relationship_type: str) -> Dict[str, str]:
        """
        Get configuration for different relationship types.
        
        Args:
            relationship_type: Type of relationship
            
        Returns:
            Configuration dictionary with labels and keys
        """
        configs = {
            "LOCATED_IN": {
                "source_labels": ":Property",
                "source_keys": "from_id:listing_id",
                "target_labels": ":Neighborhood",
                "target_keys": "to_id:neighborhood_id"
            },
            "PART_OF": {
                "source_labels": "",  # Can be Neighborhood, City, or County
                "source_keys": "from_id",
                "target_labels": "",  # Can be City, County, or State
                "target_keys": "to_id"
            },
            "DESCRIBES": {
                "source_labels": ":WikipediaArticle",
                "source_keys": "from_id:page_id",
                "target_labels": "",  # Can be Neighborhood or City
                "target_keys": "to_id"
            },
            "SIMILAR_TO": {
                "source_labels": "",  # Can be Property or Neighborhood
                "source_keys": "from_id",
                "target_labels": "",  # Same as source
                "target_keys": "to_id"
            },
            "NEAR": {
                "source_labels": ":Property",
                "source_keys": "from_id:listing_id",
                "target_labels": ":Amenity",
                "target_keys": "to_id:amenity_id"
            }
        }
        
        return configs.get(relationship_type)
    
    def write_all_relationships(self, relationships: Dict[str, DataFrame]) -> bool:
        """
        Write all relationship DataFrames to Neo4j.
        
        Args:
            relationships: Dictionary of relationship DataFrames by type
            
        Returns:
            True if all writes were successful
        """
        success = True
        
        for rel_name, rel_df in relationships.items():
            if rel_df is None or rel_df.count() == 0:
                self.logger.info(f"Skipping {rel_name} - no relationships to write")
                continue
            
            # Extract relationship type from DataFrame if present
            if "relationship_type" in rel_df.columns:
                # Get the first relationship type (should be consistent)
                rel_type = rel_df.select("relationship_type").first()[0]
            else:
                # Infer from name
                rel_type = rel_name.upper().replace("_", " ")
                if "LOCATED" in rel_type:
                    rel_type = "LOCATED_IN"
                elif "SIMILAR" in rel_type:
                    rel_type = "SIMILAR_TO"
                elif "DESCRIBE" in rel_type:
                    rel_type = "DESCRIBES"
                elif "PART" in rel_type:
                    rel_type = "PART_OF"
            
            if not self.write_relationships(rel_df, rel_type):
                success = False
                self.logger.error(f"Failed to write {rel_name} relationships")
        
        return success
    
    def _clear_entity(self, label: str) -> None:
        """
        Clear all nodes of a specific type.
        
        Args:
            label: Node label to clear
        """
        try:
            query_df = self.spark.createDataFrame([{"query": f"MATCH (n:{label}) DETACH DELETE n"}])
            
            # Connection config comes from SparkSession
            (query_df.write
             .format(self.format_string)
             .mode("append")
             .option("query", f"MATCH (n:{label}) DETACH DELETE n")
             .save())
            
            self.logger.info(f"Cleared all {label} nodes")
            
        except Exception as e:
            self.logger.warning(f"Failed to clear {label} nodes: {e}")
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "neo4j"
    
    def supports_relationships(self) -> bool:
        """
        Neo4j supports relationship storage.
        
        Returns:
            True, as Neo4j is a graph database
        """
        return True
    
    def write_relationships(self, relationships: Dict[str, DataFrame]) -> bool:
        """
        Write relationship DataFrames to Neo4j.
        
        Args:
            relationships: Dictionary of relationship name to DataFrame
            
        Returns:
            True if all writes were successful, False otherwise
        """
        return self.write_all_relationships(relationships)