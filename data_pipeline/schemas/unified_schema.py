"""
Unified schema definitions for the data pipeline.

This module defines the standardized DataFrame schema that all data sources
must conform to, ensuring consistency across the pipeline.
"""

from typing import List

from pyspark.sql.types import (
    ArrayType,
    DecimalType,
    DoubleType,
    FloatType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


class UnifiedDataSchema:
    """Defines the unified schema for all processed data."""
    
    @staticmethod
    def get_schema() -> StructType:
        """
        Get the complete unified schema.
        
        Returns:
            StructType defining the unified schema
        """
        return StructType([
            # Core entity fields
            StructField("entity_id", StringType(), False),
            StructField("entity_type", StringType(), False),  # PROPERTY | NEIGHBORHOOD | WIKIPEDIA_ARTICLE
            StructField("correlation_uuid", StringType(), True),
            
            # Location fields
            StructField("city", StringType(), True),
            StructField("state", StringType(), True),
            StructField("city_normalized", StringType(), True),
            StructField("state_normalized", StringType(), True),
            StructField("latitude", DoubleType(), True),
            StructField("longitude", DoubleType(), True),
            
            # Property-specific fields
            StructField("property_type", StringType(), True),
            StructField("price", DecimalType(12, 2), True),
            StructField("bedrooms", IntegerType(), True),
            StructField("bathrooms", DoubleType(), True),
            StructField("square_feet", IntegerType(), True),
            StructField("price_per_sqft", DecimalType(10, 4), True),
            StructField("year_built", IntegerType(), True),
            StructField("lot_size", IntegerType(), True),
            
            # Content and features
            StructField("title", StringType(), True),
            StructField("description", StringType(), True),
            StructField("features", ArrayType(StringType()), True),
            StructField("features_normalized", ArrayType(StringType()), True),
            StructField("content", StringType(), True),
            StructField("summary", StringType(), True),
            StructField("key_topics", StringType(), True),
            
            # Embeddings and ML fields
            StructField("embedding_text", StringType(), True),
            StructField("embedding", ArrayType(FloatType()), True),
            StructField("embedding_model", StringType(), True),
            StructField("embedding_dimension", IntegerType(), True),
            StructField("chunk_index", LongType(), True),
            
            # Quality and metadata
            StructField("content_hash", StringType(), True),
            StructField("data_quality_score", DoubleType(), True),
            StructField("validation_status", StringType(), True),
            StructField("confidence_score", DoubleType(), True),
            
            # Source tracking
            StructField("raw_data", StringType(), True),  # Original JSON
            StructField("source_file", StringType(), True),
            StructField("source_type", StringType(), True),
            StructField("url", StringType(), True),
            
            # Processing timestamps
            StructField("ingested_at", TimestampType(), False),
            StructField("processed_at", TimestampType(), True),
            StructField("embedding_generated_at", TimestampType(), True),
        ])
    
    @staticmethod
    def get_minimal_schema() -> StructType:
        """
        Get minimal required schema for initial data loading.
        
        Returns:
            StructType with minimal required fields
        """
        return StructType([
            StructField("entity_id", StringType(), False),
            StructField("entity_type", StringType(), False),
            StructField("city", StringType(), True),
            StructField("state", StringType(), True),
            StructField("raw_data", StringType(), True),
            StructField("ingested_at", TimestampType(), False),
        ])
    
    @staticmethod
    def get_partitioning_columns() -> List[str]:
        """
        Get columns for efficient partitioning.
        
        Returns:
            List of column names for partitioning
        """
        return ["entity_type", "state", "city_normalized"]
    
    @staticmethod
    def get_indexing_columns() -> List[str]:
        """
        Get columns that should be indexed for fast queries.
        
        Returns:
            List of column names for indexing
        """
        return ["entity_id", "correlation_uuid", "entity_type", "city", "state"]
    
    @staticmethod
    def get_entity_types() -> List[str]:
        """
        Get valid entity type values.
        
        Returns:
            List of valid entity types
        """
        return ["PROPERTY", "NEIGHBORHOOD", "WIKIPEDIA_ARTICLE"]
    
    @staticmethod
    def get_property_schema() -> StructType:
        """
        Get schema specific to property entities.
        
        Returns:
            StructType for property data
        """
        return StructType([
            StructField("listing_id", StringType(), False),
            StructField("property_type", StringType(), True),
            StructField("price", DecimalType(12, 2), True),
            StructField("bedrooms", IntegerType(), True),
            StructField("bathrooms", DoubleType(), True),
            StructField("square_feet", IntegerType(), True),
            StructField("year_built", IntegerType(), True),
            StructField("lot_size", IntegerType(), True),
            StructField("features", ArrayType(StringType()), True),
            StructField("address", StructType([
                StructField("street", StringType(), True),
                StructField("city", StringType(), True),
                StructField("state", StringType(), True),
                StructField("zip_code", StringType(), True),
            ]), True),
        ])
    
    @staticmethod
    def get_neighborhood_schema() -> StructType:
        """
        Get schema specific to neighborhood entities.
        
        Returns:
            StructType for neighborhood data
        """
        return StructType([
            StructField("neighborhood_id", StringType(), False),
            StructField("name", StringType(), True),
            StructField("city", StringType(), True),
            StructField("state", StringType(), True),
            StructField("description", StringType(), True),
            StructField("amenities", ArrayType(StringType()), True),
            StructField("demographics", StructType([
                StructField("population", IntegerType(), True),
                StructField("median_income", DecimalType(10, 2), True),
                StructField("median_age", DoubleType(), True),
            ]), True),
        ])
    
    @staticmethod
    def get_wikipedia_schema() -> StructType:
        """
        Get schema specific to Wikipedia article entities.
        
        Returns:
            StructType for Wikipedia data
        """
        return StructType([
            StructField("page_id", IntegerType(), False),
            StructField("title", StringType(), True),
            StructField("url", StringType(), True),
            StructField("full_text", StringType(), True),
            StructField("summary", StringType(), True),
            StructField("key_topics", StringType(), True),
            StructField("best_city", StringType(), True),
            StructField("best_state", StringType(), True),
            StructField("relevance_score", DoubleType(), True),
            StructField("overall_confidence", DoubleType(), True),
            StructField("latitude", DoubleType(), True),
            StructField("longitude", DoubleType(), True),
        ])