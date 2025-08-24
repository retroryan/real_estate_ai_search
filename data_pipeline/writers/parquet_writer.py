"""
Entity-specific Parquet writer implementation.

This module provides entity-specific writers for outputting DataFrames to 
Parquet files with proper partitioning and organization.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col

from data_pipeline.config.models import EntityOutputConfig, ParquetWriterConfig
from data_pipeline.schemas.entity_schemas import (
    NeighborhoodSchema,
    PropertySchema,
    WikipediaArticleSchema,
)
from data_pipeline.writers.base import DataWriter
from data_pipeline.models.writer_models import WriteMetadata

logger = logging.getLogger(__name__)


class ParquetWriter(DataWriter):
    """
    Entity-specific Parquet file writer.
    
    Writes DataFrames to entity-specific Parquet files with proper partitioning
    and directory organization. Each entity type has its own write method with
    specific handling.
    """
    
    def __init__(self, config: ParquetWriterConfig, spark: SparkSession):
        """
        Initialize the Parquet writer.
        
        Args:
            config: Parquet writer configuration with entity-specific settings
            spark: SparkSession instance
        """
        super().__init__(config)
        self.config = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
        
        # Create base path
        self.base_path = Path(self.config.base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def validate_connection(self) -> bool:
        """
        Validate that output paths are accessible.
        
        Returns:
            True if paths are valid, False otherwise
        """
        try:
            # Validate base path
            if not self.base_path.exists():
                self.base_path.mkdir(parents=True, exist_ok=True)
            
            # Validate entity-specific paths
            for entity_name in ["properties", "neighborhoods", "wikipedia"]:
                entity_config = getattr(self.config, entity_name)
                entity_path = self.base_path / entity_config.path
                entity_path.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Validated Parquet output paths under: {self.base_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate output paths: {e}")
            return False
    
    def write(self, df: DataFrame, metadata: WriteMetadata) -> bool:
        """
        Route DataFrame to appropriate entity-specific writer.
        
        Args:
            df: DataFrame to write
            metadata: WriteMetadata with entity type and other information
            
        Returns:
            True if write was successful, False otherwise
        """
        entity_type = metadata.entity_type.value.lower()
        
        if entity_type == "property":
            return self.write_properties(df)
        elif entity_type == "neighborhood":
            return self.write_neighborhoods(df)
        elif entity_type == "wikipedia":
            return self.write_wikipedia(df)
        else:
            self.logger.error(f"Unknown entity type: {entity_type}")
            return False
    
    def write_properties(self, df: DataFrame) -> bool:
        """
        Write property data with specific partitioning and validation.
        
        Properties are partitioned by state and city for efficient querying
        of local real estate markets.
        
        Args:
            df: Property DataFrame
            
        Returns:
            True if successful, False otherwise
        """
        try:
            record_count = df.count()
            output_path = self.base_path / self.config.properties.path
            
            self.logger.info(f"Writing {record_count} property records to {output_path}")
            
            # Validate schema has required fields
            required_cols = {"listing_id", "city", "state"}
            if not required_cols.issubset(df.columns):
                missing = required_cols - set(df.columns)
                self.logger.error(f"Missing required property columns: {missing}")
                return False
            
            # Prepare writer with property-specific settings
            writer = df.write.mode(self.config.mode)
            writer = writer.option("compression", self.config.compression)
            
            # Apply coalescing if configured
            if self.config.properties.coalesce_partitions:
                df = df.coalesce(self.config.properties.coalesce_partitions)
            
            # Partition by state and city for property data
            if self.config.properties.partition_by:
                writer = writer.partitionBy(*self.config.properties.partition_by)
            
            # Write to Parquet
            writer.parquet(str(output_path))
            
            self.logger.info(f"Successfully wrote {record_count} property records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write property data: {e}")
            return False
    
    def write_neighborhoods(self, df: DataFrame) -> bool:
        """
        Write neighborhood data with specific partitioning and validation.
        
        Neighborhoods are partitioned by state for regional analysis.
        
        Args:
            df: Neighborhood DataFrame
            
        Returns:
            True if successful, False otherwise
        """
        try:
            record_count = df.count()
            output_path = self.base_path / self.config.neighborhoods.path
            
            self.logger.info(f"Writing {record_count} neighborhood records to {output_path}")
            
            # Validate schema has required fields
            required_cols = {"neighborhood_id", "name", "city", "state"}
            if not required_cols.issubset(df.columns):
                missing = required_cols - set(df.columns)
                self.logger.error(f"Missing required neighborhood columns: {missing}")
                return False
            
            # Prepare writer with neighborhood-specific settings
            writer = df.write.mode(self.config.mode)
            writer = writer.option("compression", self.config.compression)
            
            # Apply coalescing if configured
            if self.config.neighborhoods.coalesce_partitions:
                df = df.coalesce(self.config.neighborhoods.coalesce_partitions)
            
            # Partition by state for neighborhood data
            if self.config.neighborhoods.partition_by:
                writer = writer.partitionBy(*self.config.neighborhoods.partition_by)
            
            # Write to Parquet
            writer.parquet(str(output_path))
            
            self.logger.info(f"Successfully wrote {record_count} neighborhood records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write neighborhood data: {e}")
            return False
    
    def write_wikipedia(self, df: DataFrame) -> bool:
        """
        Write Wikipedia article data with specific partitioning and validation.
        
        Wikipedia articles are partitioned by best_state for location-based
        content discovery.
        
        Args:
            df: Wikipedia DataFrame
            
        Returns:
            True if successful, False otherwise
        """
        try:
            record_count = df.count()
            output_path = self.base_path / self.config.wikipedia.path
            
            self.logger.info(f"Writing {record_count} Wikipedia records to {output_path}")
            
            # Validate schema has required fields
            required_cols = {"page_id", "title", "short_summary", "long_summary"}
            if not required_cols.issubset(df.columns):
                missing = required_cols - set(df.columns)
                self.logger.error(f"Missing required Wikipedia columns: {missing}")
                return False
            
            # Handle articles without best_state by adding a default
            if "best_state" in self.config.wikipedia.partition_by:
                if "best_state" not in df.columns:
                    self.logger.warning("best_state column missing, adding default")
                    df = df.withColumn("best_state", col("best_state").cast("string"))
                
                # Replace nulls with "unknown" for partitioning
                df = df.fillna({"best_state": "unknown"})
            
            # Prepare writer with Wikipedia-specific settings
            writer = df.write.mode(self.config.mode)
            writer = writer.option("compression", self.config.compression)
            
            # Apply coalescing if configured
            if self.config.wikipedia.coalesce_partitions:
                df = df.coalesce(self.config.wikipedia.coalesce_partitions)
            
            # Partition by best_state for Wikipedia data
            if self.config.wikipedia.partition_by:
                # Filter to only partition by columns that exist
                partition_cols = [col for col in self.config.wikipedia.partition_by 
                                 if col in df.columns]
                if partition_cols:
                    writer = writer.partitionBy(*partition_cols)
            
            # Write to Parquet
            writer.parquet(str(output_path))
            
            self.logger.info(f"Successfully wrote {record_count} Wikipedia records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write Wikipedia data: {e}")
            return False
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "parquet"
    
    def get_entity_path(self, entity_type: str) -> Optional[Path]:
        """
        Get the output path for a specific entity type.
        
        Args:
            entity_type: Type of entity (property, neighborhood, wikipedia)
            
        Returns:
            Path object for the entity output directory, or None if invalid
        """
        entity_type = entity_type.lower()
        
        if entity_type == "property":
            return self.base_path / self.config.properties.path
        elif entity_type == "neighborhood":
            return self.base_path / self.config.neighborhoods.path
        elif entity_type == "wikipedia":
            return self.base_path / self.config.wikipedia.path
        else:
            return None
    
    def clear_entity_data(self, entity_type: str) -> bool:
        """
        Clear existing data for a specific entity type.
        
        Args:
            entity_type: Type of entity to clear
            
        Returns:
            True if successful, False otherwise
        """
        try:
            entity_path = self.get_entity_path(entity_type)
            if entity_path and entity_path.exists():
                import shutil
                shutil.rmtree(entity_path)
                self.logger.info(f"Cleared existing {entity_type} data at {entity_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear {entity_type} data: {e}")
            return False