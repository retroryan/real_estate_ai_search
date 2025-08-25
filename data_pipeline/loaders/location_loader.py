"""
Location data loader using Spark's native JSON capabilities.

This module provides a clean, focused loader specifically for location reference data,
following the same patterns as other entity loaders for consistency and
using Pydantic for type safety.
"""

import logging

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    concat_ws,
    lit,
    trim,
    when
)

from data_pipeline.models.spark_models import Location
from .base_loader import BaseLoader

logger = logging.getLogger(__name__)


class LocationLoader(BaseLoader):
    """Loads location reference data from JSON files into Spark DataFrames."""
    
    def _define_schema(self):
        """
        Define the expected input schema for location JSON files.
        
        Returns:
            Spark schema generated from Location SparkModel
        """
        return Location.spark_schema()
    
    
    def _transform_to_entity_schema(self, df: DataFrame, source_path: str) -> DataFrame:
        """
        Transform raw location data to location-specific schema with derived fields.
        
        Args:
            df: Raw location DataFrame
            source_path: Source file path for tracking
            
        Returns:
            DataFrame conforming to location-specific schema
        """
        return df.select(
            # Core location fields - normalize and trim
            trim(col("state")).alias("state"),
            trim(col("county")).alias("county"), 
            trim(col("city")).alias("city"),
            trim(col("neighborhood")).alias("neighborhood"),
            
            # Determine location type based on which fields are present
            when(col("neighborhood").isNotNull(), lit("neighborhood"))
            .when(col("city").isNotNull(), lit("city"))
            .when(col("county").isNotNull(), lit("county"))
            .when(col("state").isNotNull(), lit("state"))
            .otherwise(lit("unknown")).alias("location_type"),
            
            # Create full hierarchy path
            concat_ws(" > ",
                trim(col("neighborhood")),
                trim(col("city")),
                trim(col("county")),
                trim(col("state"))
            ).alias("full_hierarchy")
        )
    
    def validate(self, df: DataFrame) -> bool:
        """
        Validate loaded location data.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if data is valid
        """
        # Check that at least state is present for all records
        missing_state = df.filter(col("state").isNull()).count()
        if missing_state > 0:
            logger.error(f"Found {missing_state} location records without state information")
            return False
        
        # Check for neighborhoods without cities (invalid hierarchy)
        orphaned_neighborhoods = df.filter(
            col("neighborhood").isNotNull() & col("city").isNull()
        ).count()
        if orphaned_neighborhoods > 0:
            logger.warning(f"Found {orphaned_neighborhoods} neighborhoods without parent cities")
        
        logger.info("Location data validation completed successfully")
        return True