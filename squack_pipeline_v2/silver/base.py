"""Base interface for Silver layer transformation using DuckDB Relation API."""

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
import duckdb
from datetime import datetime

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import PipelineLogger, log_execution_time
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.embeddings.providers import EmbeddingProvider


class SilverMetadata(BaseModel):
    """Metadata for Silver layer processing."""
    
    model_config = ConfigDict(frozen=True)
    
    input_table: str = Field(description="Name of the Bronze input table")
    output_table: str = Field(description="Name of the Silver output table")
    input_count: int = Field(ge=0, description="Number of input records")
    output_count: int = Field(ge=0, description="Number of output records")
    dropped_count: int = Field(ge=0, description="Number of dropped records")
    entity_type: str = Field(description="Type of entity")


class SilverTransformer(ABC):
    """Base class for Silver layer data transformation."""
    
    def __init__(self, settings: PipelineSettings, connection_manager: DuckDBConnectionManager, embedding_provider: Optional[EmbeddingProvider] = None):
        """Initialize the Silver transformer.
        
        Args:
            settings: Pipeline configuration settings
            connection_manager: DuckDB connection manager
            embedding_provider: Optional embedding provider for generating vectors
        """
        self.settings = settings
        self.connection_manager = connection_manager
        self.embedding_provider = embedding_provider
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
    
    @log_execution_time
    def transform(self, input_table: str, output_table: str) -> SilverMetadata:
        """Transform Bronze data to Silver standard.
        
        Args:
            input_table: Name of Bronze input table
            output_table: Name for Silver output table
            
        Returns:
            Metadata about the transformation
        """
        # Validate table names at boundary (DuckDB best practice)
        input_table = self._validate_table_name(input_table)
        output_table = self._validate_table_name(output_table)
        
        # Validate input exists
        if not self.connection_manager.table_exists(input_table):
            raise ValueError(f"Input table {input_table} does not exist")
        
        input_count = self.connection_manager.count_records(input_table)
        
        # Drop output table if exists
        self.connection_manager.drop_table(output_table)
        
        # Apply transformations with embeddings in single operation
        self._apply_transformations(input_table, output_table)
        
        # Get output count
        output_count = self.connection_manager.count_records(output_table)
        # Handle case where Silver layer might add records (through joins)
        dropped_count = max(0, input_count - output_count)
        
        # Create metadata
        metadata = SilverMetadata(
            input_table=input_table,
            output_table=output_table,
            input_count=input_count,
            output_count=output_count,
            dropped_count=dropped_count,
            entity_type=self._get_entity_type()
        )
        
        self.logger.info(
            f"Transformed {input_count} records -> {output_count} records "
            f"(dropped {dropped_count})"
        )
        
        return metadata
    
    def _validate_table_name(self, name: str) -> str:
        """Validate table name at boundary (DuckDB best practice).
        
        Args:
            name: Table name to validate
            
        Returns:
            Validated table name
            
        Raises:
            ValueError: If table name is invalid
        """
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{0,63}$', name):
            raise ValueError(f"Invalid table name: {name}")
        return name
    
    @abstractmethod
    def _apply_transformations(self, input_table: str, output_table: str) -> None:
        """Apply standardization transformations using DuckDB Relation API.
        
        Args:
            input_table: Name of input table
            output_table: Name of output table
        """
        pass
    
    @abstractmethod
    def _get_entity_type(self) -> str:
        """Get the entity type for this transformer.
        
        Returns:
            Entity type string
        """
        pass
    
    def standardize_nulls(self, table_name: str, columns: list[str]) -> None:
        """Standardize null values in specified columns.
        
        Args:
            table_name: Table to update
            columns: Columns to standardize
        """
        # UPDATE operations require SQL - Relation API is for SELECT/transformations
        conn = self.connection_manager.get_connection()
        
        for column in columns:
            # Use proper identifier quoting
            safe_table = DuckDBConnectionManager.safe_identifier(table_name)
            safe_column = DuckDBConnectionManager.safe_identifier(column)
            
            # Build UPDATE with properly quoted identifiers
            update_sql = f"""
            UPDATE {safe_table}
            SET {safe_column} = NULL
            WHERE {safe_column} IN ('', 'null', 'NULL')
            """
            conn.execute(update_sql)
    
    def remove_duplicates(self, input_table: str, output_table: str, key_columns: list[str]) -> None:
        """Remove duplicate records based on key columns.
        
        Args:
            input_table: Input table name
            output_table: Output table name
            key_columns: Columns that define uniqueness
        """
        conn = self.connection_manager.get_connection()
        
        # Quote all identifiers properly
        safe_input = DuckDBConnectionManager.safe_identifier(input_table)
        safe_columns = [DuckDBConnectionManager.safe_identifier(col) for col in key_columns]
        partition_by = ", ".join(safe_columns)
        
        # Build deduplication query with properly quoted identifiers
        dedup_sql = f"""
        SELECT * EXCLUDE (_rn) FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY {partition_by} ORDER BY rowid) as _rn
            FROM {safe_input}
        ) WHERE _rn = 1
        """
        
        # Use Relation API to execute and create table
        result = conn.sql(dedup_sql)
        result.create(output_table)
    
    def validate(self, table_name: str) -> bool:
        """Validate the transformed data.
        
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
            self.logger.warning(f"Table {table_name} has no records after transformation")
            # This might be valid if all records were filtered
            return True
        
        self.logger.info(f"Validation passed for {table_name}: {count} records")
        return True