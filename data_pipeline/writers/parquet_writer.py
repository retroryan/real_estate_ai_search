"""
Entity-specific Parquet writer implementation.

This module provides entity-specific writers for outputting DataFrames to 
Parquet files with proper partitioning and organization.
"""

import logging
from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col

from data_pipeline.config.pipeline_config import PipelineConfig
from data_pipeline.writers.base import EntityWriter

logger = logging.getLogger(__name__)


class ParquetWriter(EntityWriter):
    """
    Simple Parquet file writer for demo purposes.
    
    Writes DataFrames to entity-specific Parquet files without complex
    partitioning or optimization.
    """
    
    def __init__(self, config: PipelineConfig, spark: SparkSession):
        """
        Initialize the Parquet writer.
        
        Args:
            config: Pipeline configuration
            spark: SparkSession instance
        """
        # Create a WriterConfig from PipelineConfig for base class
        from .base import WriterConfig
        writer_config = WriterConfig(enabled=True)
        super().__init__(writer_config)
        
        # Store pipeline config separately to avoid overwriting base class config
        self.pipeline_config = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
        
        # Create base path
        self.base_path = Path(self.pipeline_config.base_path)
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
            
            # Create entity directories
            for entity_dir in ["properties", "neighborhoods", "wikipedia"]:
                entity_path = self.base_path / entity_dir
                entity_path.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Validated Parquet output paths under: {self.base_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate output paths: {e}")
            return False
    
    def write_properties(self, df: DataFrame) -> bool:
        """
        Write property data to Parquet.
        
        Args:
            df: Property DataFrame
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = self.base_path / "properties"
            
            self.logger.info(f"Writing property records to {output_path}")
            
            # Validate schema has required fields
            required_cols = {"listing_id", "city", "state"}
            if not required_cols.issubset(df.columns):
                missing = required_cols - set(df.columns)
                self.logger.error(f"Missing required property columns: {missing}")
                return False
            
            # Write to Parquet with simple overwrite mode
            df.write.mode("overwrite").parquet(str(output_path))
            
            self.logger.info("✓ Successfully wrote property records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write property data: {e}")
            return False
    
    def write_neighborhoods(self, df: DataFrame) -> bool:
        """
        Write neighborhood data to Parquet.
        
        Args:
            df: Neighborhood DataFrame
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = self.base_path / "neighborhoods"
            
            self.logger.info(f"Writing neighborhood records to {output_path}")
            
            # Validate schema has required fields
            required_cols = {"neighborhood_id", "name", "city", "state"}
            if not required_cols.issubset(df.columns):
                missing = required_cols - set(df.columns)
                self.logger.error(f"Missing required neighborhood columns: {missing}")
                return False
            
            # Write to Parquet with simple overwrite mode
            df.write.mode("overwrite").parquet(str(output_path))
            
            self.logger.info("✓ Successfully wrote neighborhood records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write neighborhood data: {e}")
            return False
    
    def write_wikipedia(self, df: DataFrame) -> bool:
        """
        Write Wikipedia article data to Parquet.
        
        Args:
            df: Wikipedia DataFrame
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = self.base_path / "wikipedia"
            
            self.logger.info(f"Writing Wikipedia records to {output_path}")
            
            # Validate schema has required fields
            required_cols = {"page_id", "title", "short_summary", "long_summary"}
            if not required_cols.issubset(df.columns):
                missing = required_cols - set(df.columns)
                self.logger.error(f"Missing required Wikipedia columns: {missing}")
                return False
            
            # Handle articles without best_state by adding a default
            if "best_state" not in df.columns:
                self.logger.warning("best_state column missing, adding default 'unknown'")
                df = df.withColumn("best_state", col("best_state").cast("string"))
            
            # Replace nulls with "unknown" for consistency
            df = df.fillna({"best_state": "unknown"})
            
            # Write to Parquet with simple overwrite mode
            df.write.mode("overwrite").parquet(str(output_path))
            
            self.logger.info("✓ Successfully wrote Wikipedia records")
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
        
        # Normalize entity type names
        if entity_type == "property":
            entity_type = "properties"
        elif entity_type == "neighborhood":
            entity_type = "neighborhoods"
        
        if entity_type in ["properties", "neighborhoods", "wikipedia"]:
            return self.base_path / entity_type
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