"""
Entity-specific Parquet writer implementation.

This module provides entity-specific writers for outputting DataFrames to 
Parquet files with proper partitioning and organization.
"""

import logging
from pathlib import Path
from typing import Optional, Set

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col

from data_pipeline.config.models import ParquetOutputConfig
from data_pipeline.writers.base import EntityWriter

logger = logging.getLogger(__name__)


class ParquetWriter(EntityWriter):
    """
    Simple Parquet file writer for demo purposes.
    
    Writes DataFrames to entity-specific Parquet files without complex
    partitioning or optimization.
    """
    
    def __init__(self, config: ParquetOutputConfig, spark: SparkSession):
        """
        Initialize the Parquet writer.
        
        Args:
            config: Parquet output configuration
            spark: SparkSession instance
        """
        # Create a WriterConfig for base class
        from .base import WriterConfig
        writer_config = WriterConfig(enabled=True)
        super().__init__(writer_config)
        
        # Store parquet config
        self.parquet_config = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
        
        # Create base path
        self.base_path = Path(self.parquet_config.base_path)
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
            
            # Create entity directories for all entity types
            entity_dirs = [
                "properties", "neighborhoods", "wikipedia", 
                "features", "property_types", "price_ranges",
                "counties", "cities", "states", "topic_clusters"
            ]
            for entity_dir in entity_dirs:
                entity_path = self.base_path / entity_dir
                entity_path.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Validated Parquet output paths under: {self.base_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate output paths: {e}")
            return False
    
    def _write_entity_to_parquet(
        self,
        df: DataFrame,
        entity_name: str,
        entity_display_name: str,
        required_columns: Optional[Set[str]] = None
    ) -> bool:
        """
        Generic method to write any entity DataFrame to Parquet.
        
        Args:
            df: DataFrame to write
            entity_name: Directory name for the entity
            entity_display_name: Display name for logging
            required_columns: Set of required column names for validation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = self.base_path / entity_name
            
            self.logger.info(f"Writing {entity_display_name} records to {output_path}")
            
            # Validate required columns if specified
            if required_columns:
                if not required_columns.issubset(df.columns):
                    missing = required_columns - set(df.columns)
                    self.logger.error(f"Missing required {entity_display_name} columns: {missing}")
                    return False
            
            # Write to Parquet with overwrite mode
            df.write.mode("overwrite").parquet(str(output_path))
            
            self.logger.info(f"✓ Successfully wrote {entity_display_name} records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write {entity_display_name} data: {e}")
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
    
    def write_features(self, df: DataFrame) -> bool:
        """
        Write feature data to Parquet.
        
        Args:
            df: Feature DataFrame
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = self.base_path / "features"
            
            # Write to Parquet with simple overwrite mode
            df.write.mode("overwrite").parquet(str(output_path))
            
            self.logger.info("✓ Successfully wrote Feature records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write Feature data: {e}")
            return False
    
    def write_property_types(self, df: DataFrame) -> bool:
        """
        Write property type data to Parquet.
        
        Args:
            df: PropertyType DataFrame
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = self.base_path / "property_types"
            
            # Write to Parquet with simple overwrite mode
            df.write.mode("overwrite").parquet(str(output_path))
            
            self.logger.info("✓ Successfully wrote PropertyType records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write PropertyType data: {e}")
            return False
    
    def write_price_ranges(self, df: DataFrame) -> bool:
        """
        Write price range data to Parquet.
        
        Args:
            df: PriceRange DataFrame
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = self.base_path / "price_ranges"
            
            # Write to Parquet with simple overwrite mode
            df.write.mode("overwrite").parquet(str(output_path))
            
            self.logger.info("✓ Successfully wrote PriceRange records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write PriceRange data: {e}")
            return False
    
    def write_counties(self, df: DataFrame) -> bool:
        """
        Write county data to Parquet.
        
        Args:
            df: County DataFrame
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = self.base_path / "counties"
            
            # Write to Parquet with simple overwrite mode
            df.write.mode("overwrite").parquet(str(output_path))
            
            self.logger.info("✓ Successfully wrote County records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write County data: {e}")
            return False
    
    def write_cities(self, df: DataFrame) -> bool:
        """
        Write city data to Parquet.
        
        Args:
            df: City DataFrame
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = self.base_path / "cities"
            
            # Write to Parquet with simple overwrite mode
            df.write.mode("overwrite").parquet(str(output_path))
            
            self.logger.info("✓ Successfully wrote City records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write City data: {e}")
            return False
    
    def write_states(self, df: DataFrame) -> bool:
        """
        Write state data to Parquet.
        
        Args:
            df: State DataFrame
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = self.base_path / "states"
            
            # Write to Parquet with simple overwrite mode
            df.write.mode("overwrite").parquet(str(output_path))
            
            self.logger.info("✓ Successfully wrote State records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write State data: {e}")
            return False
    
    def write_topic_clusters(self, df: DataFrame) -> bool:
        """
        Write topic cluster data to Parquet.
        
        Args:
            df: TopicCluster DataFrame
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = self.base_path / "topic_clusters"
            
            # Write to Parquet with simple overwrite mode
            df.write.mode("overwrite").parquet(str(output_path))
            
            self.logger.info("✓ Successfully wrote TopicCluster records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write TopicCluster data: {e}")
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