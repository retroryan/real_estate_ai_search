"""
Property data loader using Spark's native JSON capabilities.

This module provides a clean, focused loader specifically for property data,
leveraging Spark's built-in DataFrameReader for optimal performance and
using common property_finder_models for validation.
"""

import logging
from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import array, col, current_timestamp, lit, struct, to_json
from pyspark.sql.types import (
    ArrayType,
    DecimalType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

# Import shared models from common package
from common.property_finder_models.entities import EnrichedProperty
from common.property_finder_models.geographic import EnrichedAddress

logger = logging.getLogger(__name__)


class PropertyLoader:
    """Loads property data from JSON files into Spark DataFrames."""
    
    def __init__(self, spark: SparkSession):
        """
        Initialize the property loader.
        
        Args:
            spark: Active SparkSession
        """
        self.spark = spark
        self.schema = self._define_property_schema()
    
    def _define_property_schema(self) -> StructType:
        """
        Define the expected schema for property JSON files.
        
        Returns:
            StructType defining property data schema
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
            StructField("description", StringType(), True),
            StructField("address", StructType([
                StructField("street", StringType(), True),
                StructField("city", StringType(), True),
                StructField("state", StringType(), True),
                StructField("zip_code", StringType(), True),
            ]), True),
        ])
    
    def load(self, path: str) -> DataFrame:
        """
        Load property data from JSON file(s).
        
        Args:
            path: Path to JSON file(s), supports wildcards
            
        Returns:
            DataFrame with property data in unified schema
        """
        logger.info(f"Loading property data from: {path}")
        
        # Verify path exists
        if not Path(path).exists() and "*" not in path:
            raise FileNotFoundError(f"Property data file not found: {path}")
        
        # Load JSON with native Spark reader
        raw_df = self.spark.read \
            .schema(self.schema) \
            .option("multiLine", True) \
            .option("mode", "PERMISSIVE") \
            .option("columnNameOfCorruptRecord", "_corrupt_record") \
            .json(path)
        
        # Check for corrupt records
        if "_corrupt_record" in raw_df.columns:
            corrupt_count = raw_df.filter(col("_corrupt_record").isNotNull()).count()
            if corrupt_count > 0:
                logger.warning(f"Found {corrupt_count} corrupt records in property data")
        
        # Transform to unified schema
        unified_df = self._transform_to_unified(raw_df, path)
        
        record_count = unified_df.count()
        logger.info(f"Successfully loaded {record_count} property records")
        
        return unified_df
    
    def _transform_to_unified(self, df: DataFrame, source_path: str) -> DataFrame:
        """
        Transform raw property data to unified schema.
        
        Args:
            df: Raw property DataFrame
            source_path: Source file path for tracking
            
        Returns:
            DataFrame conforming to unified schema
        """
        return df.select(
            # Core entity fields
            col("listing_id").alias("entity_id"),
            lit("PROPERTY").alias("entity_type"),
            lit(None).cast("string").alias("correlation_uuid"),
            
            # Location fields
            col("address.city").alias("city"),
            col("address.state").alias("state"),
            lit(None).cast("string").alias("city_normalized"),
            lit(None).cast("string").alias("state_normalized"),
            lit(None).cast("double").alias("latitude"),
            lit(None).cast("double").alias("longitude"),
            
            # Property-specific fields
            col("property_type"),
            col("price"),
            col("bedrooms"),
            col("bathrooms"),
            col("square_feet"),
            lit(None).cast("decimal(10,4)").alias("price_per_sqft"),
            col("year_built"),
            col("lot_size"),
            
            # Content and features
            lit(None).cast("string").alias("title"),
            col("description"),
            col("features"),
            array().cast(ArrayType(StringType())).alias("features_normalized"),
            lit(None).cast("string").alias("content"),
            lit(None).cast("string").alias("summary"),
            lit(None).cast("string").alias("key_topics"),
            
            # Embedding fields (populated later in pipeline)
            lit(None).cast("string").alias("embedding_text"),
            lit(None).alias("embedding"),
            lit(None).cast("string").alias("embedding_model"),
            lit(None).cast("int").alias("embedding_dimension"),
            lit(None).cast("long").alias("chunk_index"),
            
            # Quality and metadata
            lit(None).cast("string").alias("content_hash"),
            lit(None).cast("double").alias("data_quality_score"),
            lit("pending").alias("validation_status"),
            lit(None).cast("double").alias("confidence_score"),
            
            # Source tracking
            to_json(struct("*")).alias("raw_data"),
            lit(source_path).alias("source_file"),
            lit("JSON").alias("source_type"),
            lit(None).cast("string").alias("url"),
            
            # Processing timestamps
            current_timestamp().alias("ingested_at"),
            lit(None).cast("timestamp").alias("processed_at"),
            lit(None).cast("timestamp").alias("embedding_generated_at"),
        )
    
    def validate(self, df: DataFrame) -> bool:
        """
        Validate loaded property data.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if data is valid
        """
        # Check for required fields
        null_ids = df.filter(col("entity_id").isNull()).count()
        if null_ids > 0:
            logger.error(f"Found {null_ids} properties with null listing_id")
            return False
        
        # Check for duplicate IDs
        total = df.count()
        unique = df.select("entity_id").distinct().count()
        if total != unique:
            logger.warning(f"Found duplicate listing IDs: {total - unique} duplicates")
        
        return True