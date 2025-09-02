"""Base interface for Bronze layer ingestion."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import PipelineLogger, log_execution_time
from squack_pipeline_v2.core.settings import PipelineSettings


class BronzeMetadata(BaseModel):
    """Metadata for Bronze layer processing."""
    
    model_config = ConfigDict(frozen=True)
    
    table_name: str = Field(description="Name of the created table")
    record_count: int = Field(ge=0, description="Number of records loaded")
    source_path: Path = Field(description="Path to source data file")
    entity_type: str = Field(description="Type of entity (property, neighborhood, wikipedia)")


class BronzeIngester(ABC):
    """Base class for Bronze layer data ingestion."""
    
    def __init__(self, settings: PipelineSettings, connection_manager: DuckDBConnectionManager):
        """Initialize the Bronze ingester.
        
        Args:
            settings: Pipeline configuration settings
            connection_manager: DuckDB connection manager
        """
        self.settings = settings
        self.connection_manager = connection_manager
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.records_ingested = 0
    
    @log_execution_time
    def ingest(self, source_path: Path, table_name: str, sample_size: Optional[int] = None) -> BronzeMetadata:
        """Load raw data from source file into Bronze table.
        
        Args:
            source_path: Path to source data file
            table_name: Name for the Bronze table
            sample_size: Optional number of records to load
            
        Returns:
            Metadata about the ingested data
        """
        # Validate source file
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Drop existing table if it exists
        self.connection_manager.drop_table(table_name)
        
        # Load data based on file type
        if source_path.suffix == ".json":
            self._load_json(source_path, table_name, sample_size)
        elif source_path.suffix == ".csv":
            self._load_csv(source_path, table_name, sample_size)
        else:
            raise ValueError(f"Unsupported file type: {source_path.suffix}")
        
        # Get record count
        record_count = self.connection_manager.count_records(table_name)
        self.records_ingested = record_count
        
        # Create metadata
        metadata = BronzeMetadata(
            table_name=table_name,
            record_count=record_count,
            source_path=source_path,
            entity_type=self._get_entity_type()
        )
        
        self.logger.info(f"Ingested {record_count} records into {table_name}")
        
        return metadata
    
    def _load_json(self, path: Path, table_name: str, sample_size: Optional[int]) -> None:
        """Load data from JSON file using Relation API.
        
        Args:
            path: Path to JSON file
            table_name: Target table name
            sample_size: Optional sample size
        """
        conn = self.connection_manager.get_connection()
        
        # Use Relation API to read JSON
        relation = conn.read_json_auto(str(path))
        
        # Apply sample limit if needed
        if sample_size:
            relation = relation.limit(sample_size)
        
        # Create table from relation - Relation API handles safety
        relation.create(table_name)
    
    def _load_csv(self, path: Path, table_name: str, sample_size: Optional[int]) -> None:
        """Load data from CSV file using Relation API.
        
        Args:
            path: Path to CSV file
            table_name: Target table name
            sample_size: Optional sample size
        """
        conn = self.connection_manager.get_connection()
        
        # Use Relation API to read CSV
        relation = conn.read_csv_auto(str(path))
        
        # Apply sample limit if needed
        if sample_size:
            relation = relation.limit(sample_size)
        
        # Create table from relation - Relation API handles safety
        relation.create(table_name)
    
    @abstractmethod
    def _get_entity_type(self) -> str:
        """Get the entity type for this ingester.
        
        Returns:
            Entity type string
        """
        pass
    
    def validate(self, table_name: str) -> bool:
        """Validate the ingested data.
        
        Args:
            table_name: Name of table to validate
            
        Returns:
            True if validation passes
        """
        # Check table exists
        if not self.connection_manager.table_exists(table_name):
            self.logger.error(f"Table {table_name} does not exist")
            return False
        
        # Check has records
        count = self.connection_manager.count_records(table_name)
        if count == 0:
            self.logger.warning(f"Table {table_name} has no records")
            return True  # Zero records might be valid
        
        # Check schema
        schema = self.connection_manager.get_table_schema(table_name)
        if not schema:
            self.logger.error(f"Table {table_name} has no schema")
            return False
        
        self.logger.info(f"Validation passed for {table_name}: {count} records")
        return True