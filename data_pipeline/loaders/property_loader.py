"""
Property data loader using Spark's native JSON capabilities.

This module provides a clean, focused loader specifically for property data,
leveraging Spark's built-in DataFrameReader for optimal performance and
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


class PropertyLoader(BaseLoader):
    """Loads property data from JSON files into Spark DataFrames."""
    
    def _define_schema(self) -> StructType:
        """
        Define the expected schema for property JSON files.
        
        Returns:
            StructType defining property data schema
        """
        return StructType([
            StructField("listing_id", StringType(), False),
            StructField("neighborhood_id", StringType(), True),  # Add neighborhood_id to schema
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
    
    
    def _transform_to_entity_schema(self, df: DataFrame, source_path: str) -> DataFrame:
        """
        Transform raw property data to property-specific schema.
        
        Args:
            df: Raw property DataFrame
            source_path: Source file path for tracking
            
        Returns:
            DataFrame conforming to property-specific schema
        """
        return df.select(
            # Core property fields
            col("listing_id"),
            col("neighborhood_id"),  # Include neighborhood_id for relationship building
            col("property_type"),
            col("price"),
            col("bedrooms"),
            col("bathrooms"),
            col("square_feet"),
            col("year_built"),
            col("lot_size"),
            col("features"),
            col("description"),
            col("address")
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
        null_ids = df.filter(col("listing_id").isNull()).count()
        if null_ids > 0:
            logger.error(f"Found {null_ids} properties with null listing_id")
            return False
        
        # Check for duplicate IDs
        total = df.count()
        unique = df.select("listing_id").distinct().count()
        if total != unique:
            logger.warning(f"Found duplicate listing IDs: {total - unique} duplicates")
        
        return True