"""Base writer interface for data output operations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.utils.logging import PipelineLogger


class BaseWriter(ABC):
    """Abstract base class for all data writers."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize the writer with pipeline settings."""
        self.settings = settings
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.connection: Optional[duckdb.DuckDBPyConnection] = None
        self.written_files: List[Path] = []
    
    def set_connection(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Set the DuckDB connection for the writer."""
        self.connection = connection
        self.logger.debug("DuckDB connection established")
    
    @abstractmethod
    def write(self, table_name: str, output_path: Path) -> Path:
        """Write data from table to output path.
        
        Args:
            table_name: Name of the table to write
            output_path: Path where the data should be written
            
        Returns:
            Path to the written file
        """
        pass
    
    @abstractmethod
    def validate_output(self, output_path: Path) -> bool:
        """Validate written output meets requirements.
        
        Args:
            output_path: Path to the output file
            
        Returns:
            True if validation passes, False otherwise
        """
        pass
    
    @abstractmethod
    def get_output_schema(self) -> Dict[str, str]:
        """Get the expected output schema.
        
        Returns:
            Dictionary mapping column names to types
        """
        pass
    
    def get_written_files(self) -> List[Path]:
        """Get list of all files written by this writer."""
        return self.written_files
    
    def get_total_size(self) -> int:
        """Get total size of all written files in bytes."""
        total_size = 0
        for file_path in self.written_files:
            if file_path.exists():
                total_size += file_path.stat().st_size
        return total_size
    
    def cleanup(self) -> None:
        """Clean up temporary resources."""
        # Override in subclasses if needed
        pass


class PartitionedWriter(BaseWriter):
    """Base class for writers that support partitioned output."""
    
    @abstractmethod
    def get_partition_columns(self) -> List[str]:
        """Get columns to use for partitioning.
        
        Returns:
            List of column names for partitioning
        """
        pass
    
    def write_partitioned(
        self,
        table_name: str,
        output_dir: Path,
        partition_columns: Optional[List[str]] = None
    ) -> List[Path]:
        """Write data with partitioning.
        
        Args:
            table_name: Name of the table to write
            output_dir: Directory where partitioned data should be written
            partition_columns: Columns to partition by (uses default if None)
            
        Returns:
            List of paths to written partition files
        """
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        # Use default partition columns if not provided
        if partition_columns is None:
            partition_columns = self.get_partition_columns()
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate partition query
        partition_clause = ", ".join(partition_columns) if partition_columns else ""
        
        # Write partitioned data (implementation depends on specific format)
        # This is a template - override in specific implementations
        self.logger.info(
            f"Writing partitioned data from {table_name} to {output_dir} "
            f"with partitions: {partition_columns}"
        )
        
        return []  # Return list of written files


class BatchWriter(BaseWriter):
    """Base class for writers that support batch writing."""
    
    def __init__(self, settings: PipelineSettings, batch_size: int = 10000):
        """Initialize batch writer with batch size."""
        super().__init__(settings)
        self.batch_size = batch_size
        self.current_batch: List[Dict[str, Any]] = []
        self.batch_count = 0
    
    @abstractmethod
    def write_batch(self, batch: List[Dict[str, Any]], output_path: Path) -> None:
        """Write a batch of records to output.
        
        Args:
            batch: List of records to write
            output_path: Path where the batch should be written
        """
        pass
    
    def add_record(self, record: Dict[str, Any]) -> None:
        """Add a record to the current batch."""
        self.current_batch.append(record)
        
        if len(self.current_batch) >= self.batch_size:
            self.flush_batch()
    
    def flush_batch(self, output_path: Optional[Path] = None) -> None:
        """Flush the current batch to output."""
        if not self.current_batch:
            return
        
        if output_path is None:
            output_path = self.settings.data.output_path / f"batch_{self.batch_count}.parquet"
        
        self.write_batch(self.current_batch, output_path)
        self.written_files.append(output_path)
        self.batch_count += 1
        self.current_batch = []
        
        self.logger.debug(f"Flushed batch {self.batch_count} to {output_path}")