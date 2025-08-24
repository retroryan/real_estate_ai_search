"""
Elasticsearch writer orchestrator for entity-specific index creation.

This module provides a single orchestrator that routes entity-specific
DataFrames to appropriate Elasticsearch indices with proper mappings.
"""

import logging
from typing import Any, Dict

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col

from data_pipeline.config.models import ElasticsearchConfig
from data_pipeline.writers.base import DataWriter

logger = logging.getLogger(__name__)


class ElasticsearchOrchestrator(DataWriter):
    """
    Orchestrator for entity-specific Elasticsearch writing.
    
    Routes each entity type to its dedicated index with proper mappings.
    """
    
    def __init__(self, config: ElasticsearchConfig, spark: SparkSession):
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
        
        # Elasticsearch format for Spark
        self.format_string = "org.elasticsearch.spark.sql"
        
        # Build connection string
        self.es_nodes = ",".join(self.config.hosts)
    
    def validate_connection(self) -> bool:
        """
        Validate the connection to Elasticsearch.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Create a simple test DataFrame
            test_df = self.spark.createDataFrame([{"test": 1}])
            
            # Try to write to a test index
            test_index = f"{self.config.index_prefix}_test"
            
            (test_df.write
             .format(self.format_string)
             .mode("overwrite")
             .option("es.nodes", self.es_nodes)
             .option("es.resource", test_index)
             .option("es.write.operation", "index")
             .save())
            
            # Clean up test index
            self._delete_index(test_index)
            
            self.logger.info(f"Successfully validated Elasticsearch connection to {self.es_nodes}")
            return True
            
        except Exception as e:
            self.logger.error(f"Elasticsearch connection validation failed: {e}")
            return False
    
    def write(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write entity-specific DataFrame to Elasticsearch.
        
        Args:
            df: DataFrame to write
            metadata: Metadata including entity_type
            
        Returns:
            True if write was successful, False otherwise
        """
        entity_type = metadata.get("entity_type", "").lower()
        
        if entity_type == "property":
            return self._write_properties(df, metadata)
        elif entity_type == "neighborhood":
            return self._write_neighborhoods(df, metadata)
        elif entity_type == "wikipedia":
            return self._write_wikipedia(df, metadata)
        else:
            self.logger.error(f"Unknown entity type: {entity_type}")
            return False
    
    def _write_properties(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write property data to Elasticsearch with proper mappings.
        
        Args:
            df: Property DataFrame
            metadata: Write metadata
            
        Returns:
            True if successful
        """
        try:
            index_name = f"{self.config.index_prefix}_properties"
            
            # Clear index if configured
            if self.config.clear_before_write:
                self._delete_index(index_name)
            
            record_count = df.count()
            self.logger.info(f"Writing {record_count} property documents to {index_name}")
            
            # Prepare DataFrame for Elasticsearch
            es_df = df.select(
                col("listing_id").alias("id"),
                col("street"),
                col("city"),
                col("state"),
                col("zip_code"),
                col("latitude"),
                col("longitude"),
                col("property_type"),
                col("price"),
                col("bedrooms"),
                col("bathrooms"),
                col("square_feet"),
                col("year_built"),
                col("lot_size"),
                col("description"),
                col("features"),
                col("data_quality_score")
            )
            
            # Write to Elasticsearch
            (es_df.write
             .format(self.format_string)
             .mode("append")
             .option("es.nodes", self.es_nodes)
             .option("es.resource", index_name)
             .option("es.mapping.id", "id")
             .option("es.write.operation", "index")
             .option("es.batch.size.entries", str(self.config.bulk_size))
             .save())
            
            self.logger.info(f"Successfully wrote {record_count} property documents")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write properties to Elasticsearch: {e}")
            return False
    
    def _write_neighborhoods(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write neighborhood data to Elasticsearch with proper mappings.
        
        Args:
            df: Neighborhood DataFrame
            metadata: Write metadata
            
        Returns:
            True if successful
        """
        try:
            index_name = f"{self.config.index_prefix}_neighborhoods"
            
            # Clear index if configured
            if self.config.clear_before_write:
                self._delete_index(index_name)
            
            record_count = df.count()
            self.logger.info(f"Writing {record_count} neighborhood documents to {index_name}")
            
            # Prepare DataFrame for Elasticsearch
            es_df = df.select(
                col("neighborhood_id").alias("id"),
                col("name"),
                col("city"),
                col("state"),
                col("latitude"),
                col("longitude"),
                col("population"),
                col("median_income"),
                col("median_age"),
                col("description"),
                col("amenities"),
                col("points_of_interest"),
                col("data_quality_score")
            )
            
            # Write to Elasticsearch
            (es_df.write
             .format(self.format_string)
             .mode("append")
             .option("es.nodes", self.es_nodes)
             .option("es.resource", index_name)
             .option("es.mapping.id", "id")
             .option("es.write.operation", "index")
             .option("es.batch.size.entries", str(self.config.bulk_size))
             .save())
            
            self.logger.info(f"Successfully wrote {record_count} neighborhood documents")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write neighborhoods to Elasticsearch: {e}")
            return False
    
    def _write_wikipedia(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write Wikipedia article data to Elasticsearch with proper mappings.
        
        Args:
            df: Wikipedia DataFrame
            metadata: Write metadata
            
        Returns:
            True if successful
        """
        try:
            index_name = f"{self.config.index_prefix}_wikipedia"
            
            # Clear index if configured
            if self.config.clear_before_write:
                self._delete_index(index_name)
            
            record_count = df.count()
            self.logger.info(f"Writing {record_count} Wikipedia documents to {index_name}")
            
            # Prepare DataFrame for Elasticsearch
            es_df = df.select(
                col("page_id").cast("string").alias("id"),
                col("title"),
                col("url"),
                col("best_city"),
                col("best_state"),
                col("latitude"),
                col("longitude"),
                col("short_summary"),
                col("long_summary"),
                col("key_topics"),
                col("relevance_score"),
                col("confidence_score")
            )
            
            # Write to Elasticsearch
            (es_df.write
             .format(self.format_string)
             .mode("append")
             .option("es.nodes", self.es_nodes)
             .option("es.resource", index_name)
             .option("es.mapping.id", "id")
             .option("es.write.operation", "index")
             .option("es.batch.size.entries", str(self.config.bulk_size))
             .save())
            
            self.logger.info(f"Successfully wrote {record_count} Wikipedia documents")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write Wikipedia to Elasticsearch: {e}")
            return False
    
    def _delete_index(self, index_name: str) -> None:
        """
        Delete an Elasticsearch index if it exists.
        
        Args:
            index_name: Name of the index to delete
        """
        try:
            # Use Spark to check and delete index
            # Note: This is a workaround since we're using Spark connector
            empty_df = self.spark.createDataFrame([], schema="id STRING")
            
            (empty_df.write
             .format(self.format_string)
             .mode("overwrite")
             .option("es.nodes", self.es_nodes)
             .option("es.resource", index_name)
             .option("es.write.operation", "delete")
             .save())
            
            self.logger.info(f"Cleared index: {index_name}")
            
        except Exception as e:
            # Index might not exist, which is fine
            self.logger.debug(f"Could not delete index {index_name}: {e}")
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "elasticsearch"