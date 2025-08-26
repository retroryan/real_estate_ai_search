"""
Neo4j writer orchestrator for entity-specific graph creation.

This module coordinates entity-specific Neo4j writers to create the complete
graph structure with proper dependencies between entity types.
"""

import logging
import time
from typing import Dict, Optional, List

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType, DoubleType, ArrayType, StringType, FloatType

from data_pipeline.config.models import Neo4jOutputConfig
from data_pipeline.writers.base import EntityWriter
from data_pipeline.models.writer_models import (
    WriteMetadata, EntityType, RelationshipConfig, 
    RelationshipType, Neo4jEntityConfig
)

logger = logging.getLogger(__name__)


class Neo4jOrchestrator(EntityWriter):
    """
    Orchestrator for entity-specific Neo4j writers.
    
    Routes each entity type to its dedicated Neo4j writer.
    """
    
    def __init__(self, config: Neo4jOutputConfig, spark: SparkSession):
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
    
    def _get_entity_configs(self) -> Dict[EntityType, Neo4jEntityConfig]:
        """Get Pydantic-based entity configurations."""
        return {
            EntityType.PROPERTY: Neo4jEntityConfig(label="Property", key_field="listing_id"),
            EntityType.NEIGHBORHOOD: Neo4jEntityConfig(label="Neighborhood", key_field="neighborhood_id"),
            EntityType.WIKIPEDIA: Neo4jEntityConfig(label="WikipediaArticle", key_field="page_id"),
            EntityType.FEATURE: Neo4jEntityConfig(label="Feature", key_field="id"),
            EntityType.PROPERTY_TYPE: Neo4jEntityConfig(label="PropertyType", key_field="id"),
            EntityType.PRICE_RANGE: Neo4jEntityConfig(label="PriceRange", key_field="id"),
            EntityType.ZIP_CODE: Neo4jEntityConfig(label="ZipCode", key_field="id"),
            EntityType.COUNTY: Neo4jEntityConfig(label="County", key_field="id"),
            EntityType.CITY: Neo4jEntityConfig(label="City", key_field="id"),
            EntityType.STATE: Neo4jEntityConfig(label="State", key_field="id"),
            EntityType.TOPIC_CLUSTER: Neo4jEntityConfig(label="TopicCluster", key_field="id")
        }
    
    def write(self, df: DataFrame, metadata: WriteMetadata) -> bool:
        """
        Write entity-specific DataFrame to Neo4j with complete node data.
        
        Args:
            df: DataFrame to write
            metadata: WriteMetadata with entity type and other information
            
        Returns:
            True if write was successful, False otherwise
        """
        entity_configs = self._get_entity_configs()
        
        # Get the configuration for this entity type
        if metadata.entity_type in entity_configs:
            config = entity_configs[metadata.entity_type]
            
            # Create nodes with complete data for relationship creation
            # Denormalized field cleanup will happen after relationships are established
            self.logger.info(f"Writing {metadata.entity_type} nodes with complete data for relationship creation")
            
            return self._write_nodes(df, config.label, config.key_field)
        else:
            self.logger.error(f"Unknown entity type: {metadata.entity_type}")
            return False
    
    
    def _convert_decimal_columns(self, df: DataFrame) -> DataFrame:
        """
        Convert Decimal type columns to Double for Neo4j compatibility.
        
        Neo4j Spark connector cannot handle Spark's DecimalType directly and will throw:
        "Unable to convert org.apache.spark.sql.types.Decimal to Neo4j Value"
        This method converts all Decimal columns to Double type which Neo4j can handle.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with Decimal columns converted to Double
        """
        for field in df.schema.fields:
            if isinstance(field.dataType, DecimalType):
                df = df.withColumn(field.name, F.col(field.name).cast(DoubleType()))
                self.logger.debug(f"Converted Decimal column {field.name} to Double for Neo4j compatibility")
            elif isinstance(field.dataType, ArrayType):
                # Check if this is an embedding array (contains float/double values)
                if field.name in ['embedding', 'embedding_vector', 'embeddings'] or 'embedding' in field.name.lower():
                    # Keep embeddings as arrays - Neo4j can handle float arrays
                    if isinstance(field.dataType.elementType, (FloatType, DoubleType)):
                        # Already numeric array, keep as-is
                        self.logger.debug(f"Keeping embedding column {field.name} as numeric array")
                    else:
                        # Convert to double array
                        df = df.withColumn(field.name, F.col(field.name).cast(ArrayType(DoubleType())))
                        self.logger.debug(f"Converted embedding column {field.name} to Double array for Neo4j compatibility")
                else:
                    # Keep string arrays as-is for Neo4j (features, images, etc.)
                    if isinstance(field.dataType.elementType, StringType):
                        # Neo4j can handle string arrays natively
                        self.logger.debug(f"Keeping string array column {field.name} as-is for Neo4j")
                    else:
                        # Convert other array types to string representation
                        df = df.withColumn(field.name, F.col(field.name).cast(StringType()))
                        self.logger.debug(f"Converted Array column {field.name} to String for Neo4j compatibility")
        return df
    
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
            # Convert Decimal columns to Double for Neo4j compatibility
            df = self._convert_decimal_columns(df)
            
            record_count = df.count()
            self.logger.info(f"📊 Starting write of {record_count:,} {label} nodes to Neo4j")
            
            # Log sample records for verification
            if record_count > 0:
                self.logger.debug(f"   Sample {label} fields: {df.columns[:5]}")
            
            # Track start time for performance metrics
            start_time = time.time()
            
            # Connection config comes from SparkSession - use overwrite mode to handle duplicates
            writer = df.write.format(self.format_string).mode("overwrite")
            
            # Only set data-specific options
            writer = writer.option("labels", f":{label}")
            writer = writer.option("node.keys", key_field)
            
            # Use coalesce for better batch control if large dataset
            if record_count > 10000:
                self.logger.info(f"   Large dataset detected, optimizing partitions...")
                df = df.coalesce(10)
                writer = df.write.format(self.format_string).mode("overwrite")
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
        return self._write_nodes(df, "WikipediaArticle", "page_id")
    
    def _write_relationship_batch(self, relationships_df: DataFrame, relationship_type: str) -> bool:
        """
        Write a single relationship type DataFrame to Neo4j with progress tracking and error handling.
        
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
                from_id = sample['from_id'] if 'from_id' in sample else 'N/A'
                to_id = sample['to_id'] if 'to_id' in sample else 'N/A'
                self.logger.debug(f"   Sample relationship: {from_id} -> {to_id}")
            
            # Convert Decimal columns to Double for Neo4j compatibility
            relationships_df = self._convert_decimal_columns(relationships_df)
            
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
    
    def _get_relationship_configs(self) -> Dict[str, RelationshipConfig]:
        """Get Pydantic-based relationship configurations."""
        return {
            RelationshipType.LOCATED_IN.value: RelationshipConfig(
                source_labels=":Property",
                source_keys="from_id:listing_id",
                target_labels=":Neighborhood",
                target_keys="to_id:neighborhood_id"
            ),
            RelationshipType.PART_OF.value: RelationshipConfig(
                source_labels=":Neighborhood",
                source_keys="from_id:neighborhood_id",
                target_labels=":City",
                target_keys="to_id:city_id"
            ),
            RelationshipType.DESCRIBES.value: RelationshipConfig(
                source_labels=":WikipediaArticle",
                source_keys="from_id:page_id",
                target_labels=":Neighborhood",
                target_keys="to_id:neighborhood_id"
            ),
            RelationshipType.SIMILAR_TO.value: RelationshipConfig(
                source_labels="",  # Can be Property or Neighborhood
                source_keys="from_id",
                target_labels="",  # Same as source
                target_keys="to_id"
            ),
            RelationshipType.NEAR.value: RelationshipConfig(
                source_labels=":Property",
                source_keys="from_id:listing_id",
                target_labels=":Property",
                target_keys="to_id:listing_id"
            ),
            RelationshipType.HAS_FEATURE.value: RelationshipConfig(
                source_labels=":Property",
                source_keys="from_id:listing_id",
                target_labels=":Feature",
                target_keys="to_id:id"
            ),
            RelationshipType.OF_TYPE.value: RelationshipConfig(
                source_labels=":Property",
                source_keys="from_id:listing_id",
                target_labels=":PropertyType",
                target_keys="to_id:id"
            ),
            RelationshipType.IN_PRICE_RANGE.value: RelationshipConfig(
                source_labels=":Property",
                source_keys="from_id:listing_id",
                target_labels=":PriceRange",
                target_keys="to_id:id"
            ),
            RelationshipType.IN_COUNTY.value: RelationshipConfig(
                source_labels="",  # Can be Neighborhood or City
                source_keys="from_id",
                target_labels=":County",
                target_keys="to_id:id"
            ),
            RelationshipType.IN_TOPIC_CLUSTER.value: RelationshipConfig(
                source_labels="",  # Can be various entities
                source_keys="from_id",
                target_labels=":TopicCluster",
                target_keys="to_id:id"
            )
        }
    
    def _get_relationship_config(self, relationship_type: str) -> Optional[Dict[str, str]]:
        """
        Get configuration for different relationship types.
        
        Args:
            relationship_type: Type of relationship
            
        Returns:
            Configuration dictionary with labels and keys, or None if not found
        """
        configs = self._get_relationship_configs()
        
        if relationship_type in configs:
            config = configs[relationship_type]
            return {
                "source_labels": config.source_labels,
                "source_keys": config.source_keys,
                "target_labels": config.target_labels,
                "target_keys": config.target_keys
            }
        
        return None
    
    def _write_all_relationship_types(self, relationships: Dict[str, DataFrame]) -> bool:
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
            
            if not self._write_relationship_batch(rel_df, rel_type):
                success = False
                self.logger.error(f"Failed to write {rel_name} relationships")
        
        return success
    
    def write_properties(self, df: DataFrame) -> bool:
        """
        Write property data using the generic write method.
        
        Args:
            df: Property DataFrame
            
        Returns:
            True if successful
        """
        metadata = WriteMetadata(
            entity_type=EntityType.PROPERTY,
            record_count=df.count() if df else 0,
            columns=list(df.columns) if df else [],
            pipeline_name="real_estate_data_pipeline",
            pipeline_version="1.0.0"
        )
        return self.write(df, metadata)
    
    def write_neighborhoods(self, df: DataFrame) -> bool:
        """
        Write neighborhood data using the generic write method.
        
        Args:
            df: Neighborhood DataFrame
            
        Returns:
            True if successful
        """
        metadata = WriteMetadata(
            entity_type=EntityType.NEIGHBORHOOD,
            record_count=df.count() if df else 0,
            columns=list(df.columns) if df else [],
            pipeline_name="real_estate_data_pipeline",
            pipeline_version="1.0.0"
        )
        return self.write(df, metadata)
    
    def write_wikipedia(self, df: DataFrame) -> bool:
        """
        Write Wikipedia data using the generic write method.
        
        Args:
            df: Wikipedia DataFrame
            
        Returns:
            True if successful
        """
        metadata = WriteMetadata(
            entity_type=EntityType.WIKIPEDIA,
            record_count=df.count() if df else 0,
            columns=list(df.columns) if df else [],
            pipeline_name="real_estate_data_pipeline",
            pipeline_version="1.0.0"
        )
        return self.write(df, metadata)
    
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
        return self._write_all_relationship_types(relationships)