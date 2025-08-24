"""
Parquet writer implementation.

This module provides a writer for outputting DataFrames to Parquet files,
maintaining backward compatibility with the existing pipeline.
"""

import logging
from pathlib import Path
from typing import Any, Dict

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col

from data_pipeline.config.models import ParquetWriterConfig
from data_pipeline.writers.base import DataWriter

logger = logging.getLogger(__name__)


class ParquetWriter(DataWriter):
    """
    Parquet file writer.
    
    Writes DataFrames to Parquet files with optional partitioning.
    This maintains backward compatibility with the existing pipeline output.
    """
    
    def __init__(self, config: ParquetWriterConfig, spark: SparkSession):
        """
        Initialize the Parquet writer.
        
        Args:
            config: Parquet writer configuration
            spark: SparkSession instance
        """
        super().__init__(config)
        self.config = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
    
    def validate_connection(self) -> bool:
        """
        Validate the output path is accessible.
        
        Returns:
            True if path is valid, False otherwise
        """
        try:
            # Check if we can create the output directory
            output_path = Path(self.config.path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Validated Parquet output path: {self.config.path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate output path: {e}")
            return False
    
    def write(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write DataFrame to Parquet files.
        
        Args:
            df: DataFrame to write
            metadata: Metadata about the data being written
            
        Returns:
            True if write was successful, False otherwise
        """
        try:
            record_count = df.count()
            self.logger.info(f"Writing {record_count} records to Parquet at {self.config.path}")
            
            # Build the write operation
            writer = df.write.mode(self.config.mode)
            
            # Add partitioning if configured
            if self.config.partitioning_columns:
                writer = writer.partitionBy(*self.config.partitioning_columns)
            
            # Set compression
            writer = writer.option("compression", self.config.compression)
            
            # Write to Parquet
            writer.parquet(self.config.path)
            
            self.logger.info(f"Successfully wrote {record_count} records to {self.config.path}")
            
            # Log partition information if applicable
            if self.config.partitioning_columns:
                self._log_partition_info(df)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write Parquet files: {e}")
            return False
    
    def _log_partition_info(self, df: DataFrame) -> None:
        """
        Log information about the partitions created.
        
        Args:
            df: DataFrame that was written
        """
        try:
            for col_name in self.config.partitioning_columns:
                if col_name in df.columns:
                    unique_values = df.select(col(col_name)).distinct().count()
                    self.logger.info(f"Created {unique_values} partitions for column '{col_name}'")
        except Exception as e:
            self.logger.debug(f"Could not log partition info: {e}")
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "parquet"