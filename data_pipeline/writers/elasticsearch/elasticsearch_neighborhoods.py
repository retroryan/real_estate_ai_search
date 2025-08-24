"""
Neighborhood-specific Elasticsearch writer.

This module provides a writer for outputting neighborhood DataFrames to Elasticsearch
with neighborhood-specific mappings and optimizations.
"""

import logging
from typing import Any, Dict, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, concat_ws, struct, when, collect_list, lit

from data_pipeline.config.models import ElasticsearchConfig
from data_pipeline.writers.base import DataWriter

logger = logging.getLogger(__name__)


class NeighborhoodElasticsearchWriter(DataWriter):
    """
    Neighborhood-specific Elasticsearch writer.
    
    Writes neighborhood DataFrames to Elasticsearch with optimized mappings
    for geographic and demographic analytics.
    """
    
    INDEX_NAME = "neighborhoods"
    
    def __init__(self, config: ElasticsearchConfig, spark: SparkSession):
        """
        Initialize the neighborhood Elasticsearch writer.
        
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
            "es.mapping.id": "neighborhood_id"  # Use neighborhood_id as document ID
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
                [("test_neighborhood_1", "Test Neighborhood", "San Francisco", "CA")], 
                ["neighborhood_id", "name", "city", "state"]
            )
            
            # Attempt write to temporary test index
            test_options = self.base_options.copy()
            test_options["es.resource"] = "_test_neighborhood_connection/doc"
            
            test_df.write \
                .format("org.elasticsearch.spark.sql") \
                .mode("overwrite") \
                .options(**test_options) \
                .save()
            
            self.logger.info(f"Validated neighborhood Elasticsearch connection to {','.join(self.config.hosts)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Neighborhood Elasticsearch connection validation failed: {e}")
            return False
    
    def write(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write neighborhood DataFrame to Elasticsearch.
        
        Args:
            df: Neighborhood DataFrame to write
            metadata: Metadata about the data being written
            
        Returns:
            True if write was successful, False otherwise
        """
        try:
            record_count = df.count()
            self.logger.info(f"Writing {record_count} neighborhood records to Elasticsearch index {self.index_name}")
            
            # Transform neighborhood data for Elasticsearch
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
            
            self.logger.info(f"Successfully wrote {record_count} neighborhood records to index {self.index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write neighborhoods to Elasticsearch: {e}")
            return False
    
    def _transform_for_elasticsearch(self, df: DataFrame) -> DataFrame:
        """
        Transform neighborhood DataFrame for Elasticsearch indexing.
        
        Args:
            df: Input neighborhood DataFrame
            
        Returns:
            Transformed DataFrame optimized for Elasticsearch
        """
        df_transformed = df
        
        # Create center point as geo_point if coordinates exist
        if "latitude" in df.columns and "longitude" in df.columns:
            df_transformed = df_transformed.withColumn(
                "center_location",
                when(
                    col("latitude").isNotNull() & col("longitude").isNotNull(),
                    struct(
                        col("latitude").alias("lat"),
                        col("longitude").alias("lon")
                    )
                ).otherwise(lit(None))
            )
        
        # Create neighborhood search text for full-text search
        text_fields = []
        
        # Build search text from available fields
        if "name" in df.columns:
            text_fields.append(col("name"))
        if "city" in df.columns:
            text_fields.append(col("city"))
        if "state" in df.columns:
            text_fields.append(col("state"))
        if "description" in df.columns:
            text_fields.append(col("description"))
        
        if text_fields:
            df_transformed = df_transformed.withColumn(
                "search_text",
                concat_ws(" ", *text_fields)
            )
        
        # Structure demographics data as nested object if present
        demographic_fields = [
            "population", "median_income", "median_age",
            "households", "median_home_value"
        ]
        
        demographic_cols = [f for f in demographic_fields if f in df.columns]
        if demographic_cols:
            df_transformed = df_transformed.withColumn(
                "demographics",
                struct(*[col(f).alias(f) for f in demographic_cols])
            )
        
        # Ensure numeric fields are properly typed
        numeric_fields = [
            "walkability_score", "transit_score", "bike_score",
            "school_rating", "crime_rate", "population",
            "median_income", "median_age", "households",
            "median_home_value"
        ]
        
        for field in numeric_fields:
            if field in df.columns:
                if field in ["population", "households", "median_age"]:
                    df_transformed = df_transformed.withColumn(
                        field,
                        col(field).cast("integer")
                    )
                else:
                    df_transformed = df_transformed.withColumn(
                        field,
                        col(field).cast("double")
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
        """Clear the neighborhood index by deleting and recreating it."""
        try:
            self.logger.info(f"Clearing neighborhood index {self.index_name} (demo mode)")
            
            # Create empty DataFrame to trigger index deletion
            empty_df = self.spark.createDataFrame([], "neighborhood_id: string")
            
            clear_options = self.base_options.copy()
            clear_options["es.resource"] = f"{self.index_name}/doc"
            clear_options["es.index.auto.create"] = "true"
            
            empty_df.write \
                .format("org.elasticsearch.spark.sql") \
                .mode("overwrite") \
                .options(**clear_options) \
                .save()
                
        except Exception as e:
            self.logger.debug(f"Could not clear neighborhood index {self.index_name}: {e}")
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "elasticsearch_neighborhoods"
    
    @staticmethod
    def get_mapping() -> Dict[str, Any]:
        """
        Get the Elasticsearch mapping for neighborhood index.
        
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
                        "amenity_analyzer": {
                            "type": "custom",
                            "tokenizer": "keyword",
                            "filter": ["lowercase", "asciifolding"]
                        },
                        "neighborhood_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "stop"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    # Identifiers
                    "neighborhood_id": {"type": "keyword"},
                    "correlation_id": {"type": "keyword"},
                    
                    # Basic info
                    "name": {"type": "text", "analyzer": "neighborhood_analyzer"},
                    "city": {"type": "keyword"},
                    "state": {"type": "keyword"},
                    "city_normalized": {"type": "keyword"},
                    "state_normalized": {"type": "keyword"},
                    
                    # Geographic data
                    "center_location": {"type": "geo_point"},
                    "latitude": {"type": "float"},
                    "longitude": {"type": "float"},
                    "boundary": {"type": "geo_shape"},  # For polygon boundaries if available
                    
                    # Scores and ratings
                    "walkability_score": {"type": "integer"},
                    "transit_score": {"type": "integer"},
                    "bike_score": {"type": "integer"},
                    "school_rating": {"type": "float"},
                    "crime_rate": {"type": "float"},
                    
                    # Demographics (nested object)
                    "demographics": {
                        "type": "object",
                        "properties": {
                            "population": {"type": "integer"},
                            "median_income": {"type": "scaled_float", "scaling_factor": 100},
                            "median_age": {"type": "integer"},
                            "households": {"type": "integer"},
                            "median_home_value": {"type": "scaled_float", "scaling_factor": 100}
                        }
                    },
                    
                    # Text fields
                    "description": {"type": "text", "analyzer": "neighborhood_analyzer"},
                    "search_text": {"type": "text", "analyzer": "neighborhood_analyzer"},
                    "embedding_text": {"type": "text"},
                    
                    # Arrays
                    "amenities": {"type": "keyword", "normalizer": "lowercase"},
                    "attractions": {"type": "keyword"},
                    "schools": {"type": "keyword"},
                    "parks": {"type": "keyword"},
                    
                    # Embeddings (if present)
                    "embeddings": {"type": "dense_vector", "dims": 768, "index": False},
                    
                    # Quality and metadata
                    "data_quality_score": {"type": "float"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"}
                }
            }
        }