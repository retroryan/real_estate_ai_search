"""
Elasticsearch writer for Property entities.

This module provides a writer for outputting property DataFrames to Elasticsearch
with property-specific mappings and optimizations.
"""

import logging
from typing import Any, Dict, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, concat_ws, struct, when, coalesce, lit

from data_pipeline.config.models import ElasticsearchConfig
from data_pipeline.writers.base import DataWriter

logger = logging.getLogger(__name__)


class PropertyElasticsearchWriter(DataWriter):
    """
    Elasticsearch writer for Property entities.
    
    Writes property DataFrames to Elasticsearch with optimized mappings
    for real estate search and analytics.
    """
    
    INDEX_NAME = "properties"
    
    def __init__(self, config: ElasticsearchConfig, spark: SparkSession):
        """
        Initialize the property Elasticsearch writer.
        
        Args:
            config: Elasticsearch writer configuration
            spark: SparkSession instance
        """
        super().__init__(config)
        self.config = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
        self.index_name = f"{config.index_prefix}_{self.INDEX_NAME}"
        
        # Build connection options
        self._build_connection_options()
    
    def _build_connection_options(self) -> None:
        """Build connection options for Elasticsearch."""
        self.base_options = {
            "es.nodes": ",".join(self.config.hosts),
            "es.batch.size.entries": str(self.config.bulk_size),
            "es.write.operation": "index",
            "es.index.auto.create": "true",
            "es.mapping.id": "listing_id"  # Use listing_id as document ID
        }
        
        # Add authentication if provided
        if self.config.username:
            self.base_options["es.net.http.auth.user"] = self.config.username
        
        password = self.config.get_password()
        if password:
            self.base_options["es.net.http.auth.pass"] = password
    
    def validate_connection(self) -> bool:
        """
        Validate the connection to Elasticsearch.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Create minimal test DataFrame
            test_df = self.spark.createDataFrame(
                [("test_prop_1", "test", 100000.0)], 
                ["listing_id", "property_type", "price"]
            )
            
            # Attempt write to temporary test index
            test_options = self.base_options.copy()
            test_options["es.resource"] = "_test_property_connection/doc"
            
            test_df.write \
                .format("org.elasticsearch.spark.sql") \
                .mode("overwrite") \
                .options(**test_options) \
                .save()
            
            self.logger.info(f"Validated property Elasticsearch connection to {','.join(self.config.hosts)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Property Elasticsearch connection validation failed: {e}")
            return False
    
    def write(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write property DataFrame to Elasticsearch.
        
        Args:
            df: Property DataFrame to write
            metadata: Metadata about the data being written
            
        Returns:
            True if write was successful, False otherwise
        """
        try:
            record_count = df.count()
            self.logger.info(f"Writing {record_count} property records to Elasticsearch index {self.index_name}")
            
            # Transform property data for Elasticsearch
            transformed_df = self._transform_for_elasticsearch(df)
            
            # Clear index if configured (demo mode)
            if self.config.clear_before_write:
                self._clear_index()
            
            # Build write options
            write_options = self.base_options.copy()
            write_options["es.resource"] = f"{self.index_name}/doc"
            
            # Write to Elasticsearch
            transformed_df.write \
                .format("org.elasticsearch.spark.sql") \
                .mode("append") \
                .options(**write_options) \
                .save()
            
            self.logger.info(f"Successfully wrote {record_count} property records to index {self.index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write properties to Elasticsearch: {e}")
            return False
    
    def _transform_for_elasticsearch(self, df: DataFrame) -> DataFrame:
        """
        Transform property DataFrame for Elasticsearch indexing.
        
        Args:
            df: Input property DataFrame
            
        Returns:
            Transformed DataFrame optimized for Elasticsearch
        """
        # Create geo_point structure for location queries
        df_transformed = df
        
        # Add location field as geo_point if coordinates exist
        if "latitude" in df.columns and "longitude" in df.columns:
            df_transformed = df_transformed.withColumn(
                "location",
                when(
                    col("latitude").isNotNull() & col("longitude").isNotNull(),
                    struct(
                        col("latitude").alias("lat"),
                        col("longitude").alias("lon")
                    )
                ).otherwise(lit(None))
            )
        
        # Create property search text for full-text search
        text_fields = []
        
        # Build search text from available fields
        if "street" in df.columns:
            text_fields.append(col("street"))
        if "city" in df.columns:
            text_fields.append(col("city"))
        if "state" in df.columns:
            text_fields.append(col("state"))
        if "description" in df.columns:
            text_fields.append(col("description"))
        if "property_type" in df.columns:
            text_fields.append(col("property_type"))
        
        if text_fields:
            df_transformed = df_transformed.withColumn(
                "search_text",
                concat_ws(" ", *text_fields)
            )
        
        # Ensure price is numeric (scaled_float in ES)
        if "price" in df.columns:
            df_transformed = df_transformed.withColumn(
                "price",
                col("price").cast("double")
            )
        
        # Ensure numeric fields are properly typed
        numeric_fields = ["bedrooms", "bathrooms", "square_feet", "year_built"]
        for field in numeric_fields:
            if field in df.columns:
                df_transformed = df_transformed.withColumn(
                    field,
                    col(field).cast("integer")
                )
        
        # Add created/updated timestamps if not present
        from pyspark.sql.functions import current_timestamp
        if "created_at" not in df.columns:
            df_transformed = df_transformed.withColumn(
                "created_at",
                current_timestamp()
            )
        if "updated_at" not in df.columns:
            df_transformed = df_transformed.withColumn(
                "updated_at", 
                current_timestamp()
            )
        
        return df_transformed
    
    def _clear_index(self) -> None:
        """Clear the property index by deleting and recreating it."""
        try:
            self.logger.info(f"Clearing property index {self.index_name} (demo mode)")
            
            # Create empty DataFrame to trigger index deletion
            empty_df = self.spark.createDataFrame([], "listing_id: string")
            
            clear_options = self.base_options.copy()
            clear_options["es.resource"] = f"{self.index_name}/doc"
            clear_options["es.index.auto.create"] = "true"
            
            empty_df.write \
                .format("org.elasticsearch.spark.sql") \
                .mode("overwrite") \
                .options(**clear_options) \
                .save()
                
        except Exception as e:
            self.logger.debug(f"Could not clear property index {self.index_name}: {e}")
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "elasticsearch_properties"
    
    @staticmethod
    def get_mapping() -> Dict[str, Any]:
        """
        Get the Elasticsearch mapping for property index.
        
        Returns:
            Dictionary containing the mapping configuration
        """
        return {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "1s",
                "analysis": {
                    "analyzer": {
                        "property_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "stop", "snowball"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    # Identifiers
                    "listing_id": {"type": "keyword"},
                    "correlation_id": {"type": "keyword"},
                    
                    # Property details
                    "property_type": {"type": "keyword"},
                    "price": {"type": "scaled_float", "scaling_factor": 100},
                    "bedrooms": {"type": "integer"},
                    "bathrooms": {"type": "float"},
                    "square_feet": {"type": "integer"},
                    "year_built": {"type": "integer"},
                    "price_per_sqft": {"type": "scaled_float", "scaling_factor": 100},
                    
                    # Location
                    "location": {"type": "geo_point"},
                    "latitude": {"type": "float"},
                    "longitude": {"type": "float"},
                    
                    # Address fields
                    "street": {"type": "text", "analyzer": "property_analyzer"},
                    "city": {"type": "keyword"},
                    "state": {"type": "keyword"},
                    "zip": {"type": "keyword"},
                    "city_normalized": {"type": "keyword"},
                    "state_normalized": {"type": "keyword"},
                    
                    # Text fields
                    "description": {"type": "text", "analyzer": "property_analyzer"},
                    "search_text": {"type": "text", "analyzer": "property_analyzer"},
                    "embedding_text": {"type": "text"},
                    
                    # Arrays
                    "features": {"type": "keyword"},
                    "amenities": {"type": "keyword"},
                    
                    # Embeddings (if present)
                    "embeddings": {"type": "dense_vector", "dims": 768, "index": False},
                    
                    # Quality and metadata
                    "data_quality_score": {"type": "float"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"}
                }
            }
        }