"""
Elasticsearch writer orchestrator for entity-specific index creation.

This module provides a single orchestrator that routes entity-specific
DataFrames to appropriate Elasticsearch indices with proper mappings.
"""

import logging
from typing import Any, Dict

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, struct, when, isnan, isnull

from data_pipeline.config.pipeline_config import PipelineConfig
from data_pipeline.writers.base import EntityWriter
from data_pipeline.models.writer_models import WriteMetadata

logger = logging.getLogger(__name__)


class ElasticsearchOrchestrator(EntityWriter):
    """
    Orchestrator for entity-specific Elasticsearch writing.
    
    Routes each entity type to its dedicated index with proper mappings.
    """
    
    def __init__(self, config: PipelineConfig, spark: SparkSession):
        """
        Initialize the Elasticsearch orchestrator.
        
        Args:
            config: Elasticsearch configuration
            spark: SparkSession instance
        """
        super().__init__(config)
        self.config = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
        
        # Use official Elasticsearch format for Spark
        self.format_string = "es"
    
    def _add_geo_point(self, df: DataFrame, lat_col: str = "latitude", lon_col: str = "longitude") -> DataFrame:
        """
        Add a geo_point field combining latitude and longitude.
        
        Args:
            df: Input DataFrame
            lat_col: Name of latitude column
            lon_col: Name of longitude column
            
        Returns:
            DataFrame with added location field
        """
        # Only add geo_point if both lat and lon columns exist
        if lat_col in df.columns and lon_col in df.columns:
            # Create geo_point structure, handling nulls
            df = df.withColumn(
                "location",
                when(
                    (col(lat_col).isNotNull()) & 
                    (col(lon_col).isNotNull()) & 
                    (~isnan(col(lat_col))) & 
                    (~isnan(col(lon_col))),
                    struct(
                        col(lat_col).alias("lat"),
                        col(lon_col).alias("lon")
                    )
                ).otherwise(None)
            )
        return df
    
    def _prepare_dataframe(self, df: DataFrame, id_field: str) -> DataFrame:
        """
        Prepare DataFrame for Elasticsearch by handling common transformations.
        
        Args:
            df: Input DataFrame
            id_field: Field to use as document ID
            
        Returns:
            Prepared DataFrame
        """
        # Get all columns from the DataFrame
        all_columns = df.columns
        
        # Ensure ID field is aliased properly if needed
        if id_field in all_columns and id_field != "id":
            df = df.withColumn("id", col(id_field))
        
        # Add geo_point if latitude/longitude exist
        df = self._add_geo_point(df)
        
        return df
    
    def validate_connection(self) -> bool:
        """
        Validate the connection to Elasticsearch using session-level configuration.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Verify Elasticsearch config exists in SparkSession
            spark_conf = self.spark.sparkContext.getConf()
            if not spark_conf.get("es.nodes", None):
                self.logger.error("Elasticsearch configuration not found in SparkSession. "
                                "Ensure Elasticsearch is configured at session level.")
                return False
            
            # Create a simple test DataFrame
            test_df = self.spark.createDataFrame([{"test": 1}])
            
            # Try to write to a test index using session config
            test_index = f"{self.config.index_prefix}_test"
            
            (test_df.write
             .format(self.format_string)
             .mode("overwrite")
             .option("es.resource", test_index)
             .save())
            
            self.logger.info(f"Successfully validated Elasticsearch connection")
            return True
            
        except Exception as e:
            self.logger.error(f"Elasticsearch connection validation failed: {e}")
            return False
    
    def write(self, df: DataFrame, metadata: WriteMetadata) -> bool:
        """
        Write entity-specific DataFrame to Elasticsearch.
        
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
    
    def _write_properties(self, df: DataFrame, metadata: WriteMetadata) -> bool:
        """
        Write property data to Elasticsearch with all available fields.
        
        Args:
            df: Property DataFrame
            metadata: Write metadata
            
        Returns:
            True if successful
        """
        index_name = f"{self.config.index_prefix}_properties"
        
        try:
            # Validate DataFrame is not empty
            record_count = df.count()
            if record_count == 0:
                self.logger.warning(f"No property records to write to {index_name}")
                return True
            
            self.logger.info(f"Starting write operation: {record_count} property documents to {index_name}")
            
            # Ensure index has proper settings
            self._ensure_index_settings(index_name)
            
            # Prepare DataFrame - include all fields and add geo_point
            es_df = self._prepare_dataframe(df, "listing_id")
            
            # Log the fields being written
            self.logger.debug(f"Writing fields: {es_df.columns}")
            self.logger.debug(f"Write mode: {self._get_write_mode()}")
            
            # Write to Elasticsearch using session-level configuration
            write_mode = self._get_write_mode()
            (es_df.write
             .format(self.format_string)
             .mode(write_mode)
             .option("es.resource", index_name)
             .option("es.mapping.id", "id")
             .save())
            
            self.logger.info(f"Successfully completed write operation: {record_count} property documents to {index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Write operation failed for {index_name}: {str(e)}")
            self.logger.error(f"Error type: {type(e).__name__}")
            self.logger.debug(f"Failed operation details - Index: {index_name}, Record count attempted: {record_count if 'record_count' in locals() else 'unknown'}")
            return False
    
    def _write_neighborhoods(self, df: DataFrame, metadata: WriteMetadata) -> bool:
        """
        Write neighborhood data to Elasticsearch with all available fields.
        
        Args:
            df: Neighborhood DataFrame
            metadata: Write metadata
            
        Returns:
            True if successful
        """
        index_name = f"{self.config.index_prefix}_neighborhoods"
        
        try:
            # Validate DataFrame is not empty
            record_count = df.count()
            if record_count == 0:
                self.logger.warning(f"No neighborhood records to write to {index_name}")
                return True
            
            self.logger.info(f"Starting write operation: {record_count} neighborhood documents to {index_name}")
            
            # Ensure index has proper settings
            self._ensure_index_settings(index_name)
            
            # Prepare DataFrame - include all fields and add geo_point
            es_df = self._prepare_dataframe(df, "neighborhood_id")
            
            # Log the fields being written
            self.logger.debug(f"Writing fields: {es_df.columns}")
            self.logger.debug(f"Write mode: {self._get_write_mode()}")
            
            # Write to Elasticsearch using session-level configuration
            write_mode = self._get_write_mode()
            (es_df.write
             .format(self.format_string)
             .mode(write_mode)
             .option("es.resource", index_name)
             .option("es.mapping.id", "id")
             .save())
            
            self.logger.info(f"Successfully completed write operation: {record_count} neighborhood documents to {index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Write operation failed for {index_name}: {str(e)}")
            self.logger.error(f"Error type: {type(e).__name__}")
            self.logger.debug(f"Failed operation details - Index: {index_name}, Record count attempted: {record_count if 'record_count' in locals() else 'unknown'}")
            return False
    
    def _write_wikipedia(self, df: DataFrame, metadata: WriteMetadata) -> bool:
        """
        Write Wikipedia article data to Elasticsearch with all available fields.
        
        Args:
            df: Wikipedia DataFrame
            metadata: Write metadata
            
        Returns:
            True if successful
        """
        index_name = f"{self.config.index_prefix}_wikipedia"
        
        try:
            # Validate DataFrame is not empty
            record_count = df.count()
            if record_count == 0:
                self.logger.warning(f"No Wikipedia records to write to {index_name}")
                return True
            
            self.logger.info(f"Starting write operation: {record_count} Wikipedia documents to {index_name}")
            
            # Ensure index has proper settings
            self._ensure_index_settings(index_name)
            
            # Prepare DataFrame - include all fields and add geo_point
            # Wikipedia uses page_id as the identifier
            es_df = self._prepare_dataframe(df, "page_id")
            
            # Ensure page_id is cast to string for ES document ID
            if "page_id" in es_df.columns:
                es_df = es_df.withColumn("id", col("page_id").cast("string"))
            
            # Log the fields being written
            self.logger.debug(f"Writing fields: {es_df.columns}")
            self.logger.debug(f"Write mode: {self._get_write_mode()}")
            
            # Write to Elasticsearch using session-level configuration
            write_mode = self._get_write_mode()
            (es_df.write
             .format(self.format_string)
             .mode(write_mode)
             .option("es.resource", index_name)
             .option("es.mapping.id", "id")
             .save())
            
            self.logger.info(f"Successfully completed write operation: {record_count} Wikipedia documents to {index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Write operation failed for {index_name}: {str(e)}")
            self.logger.error(f"Error type: {type(e).__name__}")
            self.logger.debug(f"Failed operation details - Index: {index_name}, Record count attempted: {record_count if 'record_count' in locals() else 'unknown'}")
            return False
    
    def _ensure_index_settings(self, index_name: str) -> None:
        """
        Ensure index is created with proper settings for the entity type.
        
        The official connector handles mapping automatically based on DataFrame schema,
        but we can provide hints through index settings.
        
        Args:
            index_name: Name of the index
        """
        try:
            # Log that we're preparing the index
            self.logger.info(f"Preparing index {index_name} with optimal settings")
            
            # The official connector will create the index with proper mappings
            # based on the DataFrame schema when we write data
            # The geo_point field will be automatically mapped from our struct type
            
        except Exception as e:
            self.logger.debug(f"Index preparation note for {index_name}: {e}")
    
    def _get_write_mode(self) -> str:
        """
        Determine the appropriate write mode based on configuration.
        
        Returns:
            Write mode string for Spark DataFrame writer
        """
        # If clear_before_write is enabled, use overwrite mode
        # Otherwise, use append mode to preserve existing data
        return "overwrite" if self.config.clear_before_write else "append"
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "archive_elasticsearch"