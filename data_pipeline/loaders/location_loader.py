"""
Location data loader using Spark's native JSON capabilities.

This module provides a clean, focused loader specifically for location reference data,
following the same patterns as other entity loaders for consistency and
using Pydantic for type safety.
"""

import logging
from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, 
    current_timestamp, 
    lit,
    when,
    concat_ws,
    trim,
    upper
)
from pyspark.sql.types import (
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from data_pipeline.schemas.location_schema import get_location_spark_schema

logger = logging.getLogger(__name__)


class LocationLoader:
    """Loads location reference data from JSON files into Spark DataFrames."""
    
    def __init__(self, spark: SparkSession):
        """
        Initialize the location loader.
        
        Args:
            spark: Active SparkSession
        """
        self.spark = spark
        self.schema = self._define_location_input_schema()
    
    def _define_location_input_schema(self) -> StructType:
        """
        Define the expected input schema for location JSON files.
        
        Returns:
            StructType defining location input data schema
        """
        return StructType([
            StructField("state", StringType(), True),
            StructField("county", StringType(), True),
            StructField("city", StringType(), True),
            StructField("neighborhood", StringType(), True),
        ])
    
    def load(self, path: str) -> DataFrame:
        """
        Load location data from JSON file.
        
        Args:
            path: Path to JSON file containing location data
            
        Returns:
            DataFrame with location-specific schema
        """
        logger.info(f"Loading location data from: {path}")
        
        # Verify path exists
        if not Path(path).exists():
            raise FileNotFoundError(f"Location data file not found: {path}")
        
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
                logger.warning(f"Found {corrupt_count} corrupt records in location data")
        
        # Transform to location-specific schema
        location_df = self._transform_to_location_schema(raw_df, path)
        
        record_count = location_df.count()
        logger.info(f"Successfully loaded {record_count} location records")
        
        return location_df
    
    def _transform_to_location_schema(self, df: DataFrame, source_path: str) -> DataFrame:
        """
        Transform raw location data to location-specific schema with derived fields.
        
        Args:
            df: Raw location DataFrame
            source_path: Source file path for tracking
            
        Returns:
            DataFrame conforming to location-specific schema
        """
        return df.select(
            # Core location fields - normalize to title case and trim
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
            ).alias("full_hierarchy"),
            
            # Metadata
            lit(source_path).alias("source_file"),
            current_timestamp().alias("ingested_at")
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