"""
Neighborhood data loader using Spark's native JSON capabilities.

This module provides a clean, focused loader specifically for neighborhood data,
following the same patterns as the property loader for consistency and
using common property_finder_models for validation.
"""

import logging

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, when, lit

from data_pipeline.models.spark_models import Neighborhood, WikipediaCorrelations
from .base_loader import BaseLoader

logger = logging.getLogger(__name__)


class NeighborhoodLoader(BaseLoader):
    """Loads neighborhood data from JSON files into Spark DataFrames."""
    
    def _define_schema(self):
        """
        Define the expected schema for neighborhood JSON files.
        
        Returns:
            Spark schema generated from Neighborhood SparkModel
        """
        return Neighborhood.spark_schema()
    
    
    def _transform_to_entity_schema(self, df: DataFrame, source_path: str) -> DataFrame:
        """
        Transform raw neighborhood data to neighborhood-specific schema.
        Preserves Wikipedia correlations from wikipedia_correlations field.
        
        Args:
            df: Raw neighborhood DataFrame
            source_path: Source file path for tracking
            
        Returns:
            DataFrame conforming to neighborhood-specific schema
        """
        # Check if wikipedia_correlations exists
        has_wikipedia_correlations = "wikipedia_correlations" in df.columns
        
        # Build list of columns to select
        select_columns = [
            col("neighborhood_id"),
            col("name"),
            col("city"),
            col("state"),
            col("description"),
            col("amenities"),
            col("demographics"),  # Keep demographics as nested structure
        ]
        
        if has_wikipedia_correlations:
            # Add wikipedia_correlations column
            select_columns.append(col("wikipedia_correlations"))
        
        # Select all fields
        return df.select(*select_columns)
    
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