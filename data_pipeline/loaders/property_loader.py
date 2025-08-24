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
            StructField("neighborhood_id", StringType(), True),
            StructField("address", StructType([
                StructField("street", StringType(), True),
                StructField("city", StringType(), True),
                StructField("county", StringType(), True),
                StructField("state", StringType(), True),
                StructField("zip", StringType(), True),  # Note: source uses 'zip' not 'zip_code'
            ]), True),
            StructField("coordinates", StructType([
                StructField("latitude", DoubleType(), True),
                StructField("longitude", DoubleType(), True),
            ]), True),
            StructField("property_details", StructType([
                StructField("square_feet", IntegerType(), True),
                StructField("bedrooms", IntegerType(), True),
                StructField("bathrooms", DoubleType(), True),
                StructField("property_type", StringType(), True),
                StructField("year_built", IntegerType(), True),
                StructField("lot_size", DoubleType(), True),
                StructField("stories", IntegerType(), True),
                StructField("garage_spaces", IntegerType(), True),
            ]), True),
            StructField("listing_price", DecimalType(12, 2), True),
            StructField("price_per_sqft", IntegerType(), True),
            StructField("description", StringType(), True),
            StructField("features", ArrayType(StringType()), True),
            StructField("listing_date", StringType(), True),
            StructField("days_on_market", IntegerType(), True),
            StructField("virtual_tour_url", StringType(), True),
            StructField("images", ArrayType(StringType()), True),
            StructField("price_history", ArrayType(StructType([
                StructField("date", StringType(), True),
                StructField("price", DecimalType(12, 2), True),
                StructField("event", StringType(), True),
            ])), True),
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

        # Return all the nested structures - the enricher will handle flattening
        return df.select(
            # Core property fields
            col("listing_id"),
            col("neighborhood_id"),
            col("address"),
            col("coordinates"),
            col("property_details"),
            col("listing_price"),
            col("price_per_sqft"),
            col("description"),
            col("features"),
            col("listing_date"),
            col("days_on_market"),
            col("virtual_tour_url"),
            col("images"),
            col("price_history")
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