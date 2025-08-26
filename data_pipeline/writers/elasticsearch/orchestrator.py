"""
Refactored Elasticsearch writer orchestrator using Pydantic models.

This module provides a clean, modular implementation that is easy to test
and maintain, with proper type safety and separation of concerns.
"""

import logging
from typing import Dict, List

from pyspark.sql import DataFrame, SparkSession

from data_pipeline.config.models import ElasticsearchOutputConfig
from data_pipeline.writers.base import EntityWriter
from data_pipeline.writers.elasticsearch.models import (
    EntityType,
    ElasticsearchWriterSettings,
    SchemaTransformation,
    WriteOperation,
    WriteResult,
)
from data_pipeline.writers.elasticsearch.transformations import DataFrameTransformer

logger = logging.getLogger(__name__)


class ElasticsearchOrchestrator(EntityWriter):
    """
    Clean, modular Elasticsearch writer using Pydantic models.
    
    This implementation separates concerns clearly:
    - Configuration handling via Pydantic models
    - DataFrame transformation via dedicated transformer
    - Entity-specific operations via clean methods
    """
    
    def __init__(self, config: ElasticsearchOutputConfig, spark: SparkSession):
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
        
        # Create writer settings from config
        self.settings = ElasticsearchWriterSettings(
            index_prefix=config.index_prefix,
            batch_size=config.bulk_size,
        )
        
        # Initialize transformer
        self.transformer = DataFrameTransformer(spark)
        
        # Spark format
        self.format_string = "es"
    
    def validate_connection(self) -> bool:
        """
        Validate the connection to Elasticsearch.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Verify Elasticsearch config exists in SparkSession
            spark_conf = self.spark.sparkContext.getConf()
            if not spark_conf.get("es.nodes", None):
                self.logger.error("Elasticsearch configuration not found in SparkSession")
                return False
            
            # Create test write operation
            test_index = f"{self.settings.index_prefix}_validation_test"
            test_df = self.spark.createDataFrame([{"id": "test", "validation": True}])
            
            # Perform test write
            test_df.write \
                .format(self.format_string) \
                .mode("overwrite") \
                .option("es.resource", test_index) \
                .option("es.mapping.id", "id") \
                .save()
            
            self.logger.info("Elasticsearch connection validation successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Elasticsearch connection validation failed: {e}")
            return False
    
    def write_properties(self, df: DataFrame) -> bool:
        """
        Write property data to Elasticsearch.
        
        Args:
            df: Property DataFrame
            
        Returns:
            True if successful
        """
        operation = self._create_write_operation(EntityType.PROPERTIES, df.count())
        result = self._execute_write_operation(df, operation)
        
        if result.is_success():
            self.logger.info(f"Successfully wrote {result.record_count} properties to {result.index_name}")
            return True
        else:
            self.logger.error(f"Property write failed: {result.error_message}")
            return False
    
    def write_neighborhoods(self, df: DataFrame) -> bool:
        """
        Write neighborhood data to Elasticsearch.
        
        Args:
            df: Neighborhood DataFrame
            
        Returns:
            True if successful
        """
        operation = self._create_write_operation(EntityType.NEIGHBORHOODS, df.count())
        result = self._execute_write_operation(df, operation)
        
        if result.is_success():
            self.logger.info(f"Successfully wrote {result.record_count} neighborhoods to {result.index_name}")
            return True
        else:
            self.logger.error(f"Neighborhood write failed: {result.error_message}")
            return False
    
    def write_wikipedia(self, df: DataFrame) -> bool:
        """
        Write Wikipedia data to Elasticsearch.
        
        Args:
            df: Wikipedia DataFrame
            
        Returns:
            True if successful
        """
        operation = self._create_write_operation(EntityType.WIKIPEDIA, df.count())
        result = self._execute_write_operation(df, operation)
        
        if result.is_success():
            self.logger.info(f"Successfully wrote {result.record_count} Wikipedia articles to {result.index_name}")
            return True
        else:
            self.logger.error(f"Wikipedia write failed: {result.error_message}")
            return False
    
    def get_writer_name(self) -> str:
        """Get the name of this writer."""
        return "elasticsearch"
    
    def _create_write_operation(self, entity_type: EntityType, record_count: int) -> WriteOperation:
        """
        Create a write operation configuration for an entity type.
        
        Args:
            entity_type: Type of entity to write
            record_count: Number of records to write
            
        Returns:
            Configured write operation
        """
        index_settings = self.settings.create_index_settings(entity_type)
        
        # Configure schema transformation
        transform_config = SchemaTransformation(
            convert_decimals=True,
            add_geo_point=index_settings.enable_geo_point,
        )
        
        return WriteOperation(
            index_settings=index_settings,
            schema_transform=transform_config,
            record_count=record_count,
        )
    
    def _execute_write_operation(self, df: DataFrame, operation: WriteOperation) -> WriteResult:
        """
        Execute a write operation to Elasticsearch.
        
        Args:
            df: DataFrame to write
            operation: Write operation configuration
            
        Returns:
            Write operation result
        """
        try:
            # Validate non-empty DataFrame
            actual_count = df.count()
            if actual_count == 0:
                return WriteResult(
                    success=True,
                    index_name=operation.index_settings.name,
                    entity_type=operation.index_settings.entity_type,
                    record_count=0,
                    fields_written=[],
                    transformation_applied=False,
                )
            
            self.logger.info(f"Starting write operation: {actual_count} records to {operation.index_settings.name}")
            
            # Apply DataFrame transformations
            transformed_df = self.transformer.transform_for_elasticsearch(
                df,
                operation.schema_transform,
                operation.index_settings.id_field
            )
            
            # Special handling for Wikipedia page_id (cast to string)
            if operation.index_settings.entity_type == EntityType.WIKIPEDIA:
                if "page_id" in transformed_df.columns:
                    from pyspark.sql.functions import col
                    transformed_df = transformed_df.withColumn("id", col("page_id").cast("string"))
            
            # Get Spark write options
            spark_options = operation.get_spark_options()
            
            # Execute the write
            writer = transformed_df.write \
                .format(self.format_string) \
                .mode(operation.index_settings.write_mode.value)
            
            for key, value in spark_options.items():
                writer = writer.option(key, value)
            
            writer.save()
            
            # Create success result
            return WriteResult(
                success=True,
                index_name=operation.index_settings.name,
                entity_type=operation.index_settings.entity_type,
                record_count=actual_count,
                fields_written=transformed_df.columns,
                transformation_applied=True,
            )
            
        except Exception as e:
            self.logger.error(f"Write operation failed: {str(e)}")
            return WriteResult(
                success=False,
                index_name=operation.index_settings.name,
                entity_type=operation.index_settings.entity_type,
                record_count=0,
                fields_written=[],
                error_message=str(e),
                transformation_applied=False,
            )
    
    def get_write_results(self) -> List[WriteResult]:
        """
        Get results of recent write operations.
        
        This could be enhanced to store operation history.
        
        Returns:
            List of write results
        """
        # For now, return empty list
        # This could be enhanced to store operation results
        return []
    
    def clear_all_indices(self) -> bool:
        """
        Clear all indices managed by this orchestrator.
        
        This is useful for development and testing.
        
        Returns:
            True if successful
        """
        try:
            for entity_type in EntityType:
                index_settings = self.settings.create_index_settings(entity_type)
                
                # Create empty DataFrame with proper schema and overwrite
                empty_df = self.spark.createDataFrame([], "id STRING")
                
                empty_df.write \
                    .format(self.format_string) \
                    .mode("overwrite") \
                    .option("es.resource", index_settings.name) \
                    .option("es.mapping.id", "id") \
                    .save()
                
                self.logger.info(f"Cleared index: {index_settings.name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear indices: {e}")
            return False