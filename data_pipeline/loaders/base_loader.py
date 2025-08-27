"""
Base loader class for common data loading functionality.

Provides shared functionality for all entity-specific loaders to reduce
code duplication and ensure consistent patterns.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, current_timestamp, lit

logger = logging.getLogger(__name__)


class BaseLoader(ABC):
    """
    Abstract base class for entity-specific data loaders.
    
    Provides common functionality like path validation, corrupt record checking,
    and logging patterns.
    """
    
    def __init__(self, spark: SparkSession):
        """
        Initialize the base loader.
        
        Args:
            spark: Active SparkSession
        """
        self.spark = spark
        self.schema = self._define_schema()
    
    @abstractmethod
    def _define_schema(self):
        """
        Define the expected schema for the entity's data files.
        
        Returns:
            Spark schema generated from SparkModel.as_spark_schema()
        """
        pass
    
    @abstractmethod
    def _transform_to_entity_schema(self, df: DataFrame, source_path: str) -> DataFrame:
        """
        Transform raw data to entity-specific schema.
        
        Args:
            df: Raw DataFrame
            source_path: Source file path for tracking
            
        Returns:
            DataFrame conforming to entity-specific schema
        """
        pass
    
    def load(self, path: str, sample_size: Optional[int] = None) -> DataFrame:
        """
        Load data from JSON file(s) with optional sampling.
        
        Args:
            path: Path to JSON file(s), supports wildcards
            sample_size: Optional number of records to sample
            
        Returns:
            DataFrame with entity-specific schema, optionally sampled
        """
        entity_name = self.__class__.__name__.replace("Loader", "").lower()
        logger.info(f"Loading {entity_name} data from: {path}")
        
        # Verify path exists
        if not self._validate_path(path):
            raise FileNotFoundError(f"{entity_name.capitalize()} data file not found: {path}")
        
        # Load JSON with native Spark reader
        raw_df = self._load_json(path)
        
        # Check for corrupt records
        self._check_corrupt_records(raw_df, entity_name)
        
        # Transform to entity-specific schema
        entity_df = self._transform_to_entity_schema(raw_df, path)
        
        # Add common metadata
        entity_df = self._add_metadata(entity_df, path)
        
        # Apply sampling if requested
        if sample_size is not None and sample_size > 0:
            entity_df = entity_df.limit(sample_size)
            logger.info(f"Applied sampling: limited to {sample_size} {entity_name} records")
        
        return entity_df
    
    def _validate_path(self, path: str) -> bool:
        """
        Validate that the data path exists.
        
        Args:
            path: Path to validate
            
        Returns:
            True if path exists or contains wildcards
        """
        return Path(path).exists() or "*" in path
    
    def _load_json(self, path: str) -> DataFrame:
        """
        Load JSON data with consistent settings.
        
        Args:
            path: Path to JSON file(s)
            
        Returns:
            Raw DataFrame from JSON
        """
        return self.spark.read \
            .schema(self.schema) \
            .option("multiLine", True) \
            .option("mode", "PERMISSIVE") \
            .option("columnNameOfCorruptRecord", "_corrupt_record") \
            .json(path)
    
    def _check_corrupt_records(self, df: DataFrame, entity_name: str):
        """
        Check for and log corrupt records.
        
        Args:
            df: DataFrame to check
            entity_name: Name of entity for logging
        """
        if "_corrupt_record" in df.columns:
            # Just log that corrupt record column exists, avoid count() action
            logger.warning(f"Corrupt record column detected in {entity_name} data")
    
    def _add_metadata(self, df: DataFrame, source_path: str) -> DataFrame:
        """
        Add common metadata fields.
        
        Args:
            df: DataFrame to add metadata to
            source_path: Source file path
            
        Returns:
            DataFrame with metadata fields
        """
        # Only add if not already present
        if "ingested_at" not in df.columns:
            df = df.withColumn("ingested_at", current_timestamp())
        
        if "source_file" not in df.columns:
            df = df.withColumn("source_file", lit(source_path))
        
        return df
    
    def validate(self, df: DataFrame) -> bool:
        """
        Validate loaded data with basic checks.
        
        Subclasses should override for entity-specific validation.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if data is valid
        """
        if df.count() == 0:
            logger.warning(f"No records found in {self.__class__.__name__} data")
            return False
        
        return True