"""
Property data loader using Spark's native JSON capabilities.

This module provides a clean, focused loader specifically for property data,
leveraging Spark's built-in DataFrameReader for optimal performance and
using common property_finder_models for validation.
"""

import logging

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col

from data_pipeline.models.spark_models import Property
from .base_loader import BaseLoader

logger = logging.getLogger(__name__)


class PropertyLoader(BaseLoader):
    """Loads property data from JSON files into Spark DataFrames."""
    
    def _define_schema(self):
        """
        Define the expected schema for property JSON files.
        
        Returns:
            Spark schema generated from Property SparkModel
        """
        return Property.spark_schema()
    
    
    def _transform_to_entity_schema(self, df: DataFrame, source_path: str) -> DataFrame:
        """
        Transform raw property data to flattened property schema.
        
        Flattens nested structures (address, coordinates, property_details) into top-level columns.
        
        Args:
            df: Raw property DataFrame
            source_path: Source file path for tracking
            
        Returns:
            DataFrame with flattened structure conforming to property entity schema
        """
        # Flatten nested structures into top-level columns
        return df.select(
            # Core fields
            col("listing_id"),
            col("neighborhood_id"),
            
            # Flatten address struct
            col("address.street").alias("street"),
            col("address.city").alias("city"),
            col("address.county").alias("county"),
            col("address.state").alias("state"),
            col("address.zip").alias("zip_code"),
            
            # Flatten coordinates struct
            col("coordinates.latitude").alias("latitude"),
            col("coordinates.longitude").alias("longitude"),
            
            # Flatten property_details struct
            col("property_details.square_feet").alias("square_feet"),
            col("property_details.bedrooms").alias("bedrooms"),
            col("property_details.bathrooms").alias("bathrooms"),
            col("property_details.property_type").alias("property_type"),
            col("property_details.year_built").alias("year_built"),
            col("property_details.lot_size").alias("lot_size"),
            col("property_details.stories").alias("stories"),
            col("property_details.garage_spaces").alias("garage_spaces"),
            
            # Direct fields
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