"""
Neighborhood data loader using Spark's native JSON capabilities.

This module provides a clean, focused loader specifically for neighborhood data,
following the same patterns as the property loader for consistency and
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
from common.property_finder_models.entities import EnrichedNeighborhood
from common.property_finder_models.geographic import GeoPolygon

logger = logging.getLogger(__name__)


class NeighborhoodLoader:
    """Loads neighborhood data from JSON files into Spark DataFrames."""
    
    def __init__(self, spark: SparkSession):
        """
        Initialize the neighborhood loader.
        
        Args:
            spark: Active SparkSession
        """
        self.spark = spark
        self.schema = self._define_neighborhood_schema()
    
    def _define_neighborhood_schema(self) -> StructType:
        """
        Define the expected schema for neighborhood JSON files.
        
        Returns:
            StructType defining neighborhood data schema
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
    
    def load(self, path: str) -> DataFrame:
        """
        Load neighborhood data from JSON file(s).
        
        Args:
            path: Path to JSON file(s), supports wildcards
            
        Returns:
            DataFrame with neighborhood data in unified schema
        """
        logger.info(f"Loading neighborhood data from: {path}")
        
        # Verify path exists
        if not Path(path).exists() and "*" not in path:
            raise FileNotFoundError(f"Neighborhood data file not found: {path}")
        
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
                logger.warning(f"Found {corrupt_count} corrupt records in neighborhood data")
        
        # Transform to unified schema
        unified_df = self._transform_to_unified(raw_df, path)
        
        record_count = unified_df.count()
        logger.info(f"Successfully loaded {record_count} neighborhood records")
        
        return unified_df
    
    def _transform_to_unified(self, df: DataFrame, source_path: str) -> DataFrame:
        """
        Transform raw neighborhood data to unified schema.
        
        Args:
            df: Raw neighborhood DataFrame
            source_path: Source file path for tracking
            
        Returns:
            DataFrame conforming to unified schema
        """
        return df.select(
            # Core entity fields
            col("neighborhood_id").alias("entity_id"),
            lit("NEIGHBORHOOD").alias("entity_type"),
            lit(None).cast("string").alias("correlation_uuid"),
            
            # Location fields
            col("city"),
            col("state"),
            lit(None).cast("string").alias("city_normalized"),
            lit(None).cast("string").alias("state_normalized"),
            lit(None).cast("double").alias("latitude"),
            lit(None).cast("double").alias("longitude"),
            
            # Property fields (not applicable for neighborhoods)
            lit(None).cast("string").alias("property_type"),
            lit(None).cast("decimal(12,2)").alias("price"),
            lit(None).cast("int").alias("bedrooms"),
            lit(None).cast("double").alias("bathrooms"),
            lit(None).cast("int").alias("square_feet"),
            lit(None).cast("decimal(10,4)").alias("price_per_sqft"),
            lit(None).cast("int").alias("year_built"),
            lit(None).cast("int").alias("lot_size"),
            
            # Content and features
            col("name").alias("title"),
            col("description"),
            col("amenities").alias("features"),
            array().cast(ArrayType(StringType())).alias("features_normalized"),
            lit(None).cast("string").alias("content"),
            lit(None).cast("string").alias("summary"),
            lit(None).cast("string").alias("key_topics"),
            
            # Embedding fields (populated later in pipeline)
            lit(None).cast("string").alias("embedding_text"),
            array().cast(ArrayType(DoubleType())).alias("embedding"),
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
        Validate loaded neighborhood data.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if data is valid
        """
        # Check for required fields
        null_ids = df.filter(col("entity_id").isNull()).count()
        if null_ids > 0:
            logger.error(f"Found {null_ids} neighborhoods with null neighborhood_id")
            return False
        
        # Check for missing city/state
        missing_location = df.filter(
            col("city").isNull() | col("state").isNull()
        ).count()
        if missing_location > 0:
            logger.warning(f"Found {missing_location} neighborhoods with missing city/state")
        
        return True