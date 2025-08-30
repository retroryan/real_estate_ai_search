"""Base interface for Silver layer transformation."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import PipelineLogger, log_execution_time
from squack_pipeline_v2.core.settings import PipelineSettings


class SilverMetadata(BaseModel):
    """Metadata for Silver layer processing."""
    
    model_config = ConfigDict(frozen=True)
    
    input_table: str = Field(description="Name of the Bronze input table")
    output_table: str = Field(description="Name of the Silver output table")
    input_count: int = Field(ge=0, description="Number of input records")
    output_count: int = Field(ge=0, description="Number of output records")
    dropped_count: int = Field(ge=0, description="Number of dropped records")
    entity_type: str = Field(description="Type of entity")


class SilverTransformer:
    """Base class for Silver layer data transformation."""
    
    def __init__(self, settings: PipelineSettings, connection_manager: DuckDBConnectionManager):
        """Initialize the Silver transformer.
        
        Args:
            settings: Pipeline configuration settings
            connection_manager: DuckDB connection manager
        """
        self.settings = settings
        self.connection_manager = connection_manager
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
        # Validate input
        if not self.connection_manager.table_exists(input_table):
            raise ValueError(f"Input table {input_table} does not exist")
        
        input_count = self.connection_manager.count_records(input_table)
        
        # Drop output table if exists
        self.connection_manager.drop_table(output_table)
        
        # Apply transformations
        self._apply_transformations(input_table, output_table)
        
        # Get output count
        output_count = self.connection_manager.count_records(output_table)
        dropped_count = input_count - output_count
        
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
    
    def _apply_transformations(self, input_table: str, output_table: str) -> None:
        """Apply standardization transformations.
        
        Args:
            input_table: Name of input table
            output_table: Name of output table
        """
        # Default implementation - override in subclasses
        # This is a simple passthrough
        query = f"CREATE TABLE {output_table} AS SELECT * FROM {input_table}"
        self.connection_manager.execute(query)
    
    def _get_entity_type(self) -> str:
        """Get the entity type for this transformer.
        
        Returns:
            Entity type string
        """
        # Default implementation - override in subclasses
        return "unknown"
    
    def standardize_nulls(self, table_name: str, columns: list[str]) -> None:
        """Standardize null values in specified columns.
        
        Args:
            table_name: Table to update
            columns: Columns to standardize
        """
        for column in columns:
            query = f"""
            UPDATE {table_name}
            SET {column} = NULL
            WHERE {column} = '' OR {column} = 'null' OR {column} = 'NULL'
            """
            self.connection_manager.execute(query)
    
    def remove_duplicates(self, input_table: str, output_table: str, key_columns: list[str]) -> None:
        """Remove duplicate records based on key columns.
        
        Args:
            input_table: Input table name
            output_table: Output table name
            key_columns: Columns that define uniqueness
        """
        key_cols = ", ".join(key_columns)
        query = f"""
        CREATE TABLE {output_table} AS
        SELECT DISTINCT ON ({key_cols}) *
        FROM {input_table}
        ORDER BY {key_cols}
        """
        self.connection_manager.execute(query)
    
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