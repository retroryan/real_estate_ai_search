"""
Neighborhood data loader using Spark's native JSON capabilities.

This module provides a clean, focused loader specifically for neighborhood data,
following the same patterns as the property loader for consistency and
using common property_finder_models for validation.
"""

import logging

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col
from pyspark.sql.types import (
    ArrayType,
    DecimalType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

from .base_loader import BaseLoader

logger = logging.getLogger(__name__)


class NeighborhoodLoader(BaseLoader):
    """Loads neighborhood data from JSON files into Spark DataFrames."""
    
    def _define_schema(self) -> StructType:
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
    
    
    def _transform_to_entity_schema(self, df: DataFrame, source_path: str) -> DataFrame:
        """
        Transform raw neighborhood data to neighborhood-specific schema.
        
        Args:
            df: Raw neighborhood DataFrame
            source_path: Source file path for tracking
            
        Returns:
            DataFrame conforming to neighborhood-specific schema
        """
        return df.select(
            # Core neighborhood fields
            col("neighborhood_id"),
            col("name"),
            col("city"),
            col("state"),
            col("description"),
            col("amenities"),
            
            # Extract demographics from nested structure
            col("demographics.population").alias("population"),
            col("demographics.median_income").alias("median_income"), 
            col("demographics.median_age").alias("median_age")
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
        null_ids = df.filter(col("neighborhood_id").isNull()).count()
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