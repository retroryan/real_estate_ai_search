"""Base processor interface for data processing operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import duckdb

from squack_pipeline.config.schemas import MedallionTier
from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.models.duckdb_models import TableIdentifier
from squack_pipeline.utils.logging import PipelineLogger


class BaseProcessor(ABC):
    """Abstract base class for all data processors."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize the processor with pipeline settings."""
        self.settings = settings
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.connection: Optional[duckdb.DuckDBPyConnection] = None
        self.tier: Optional[MedallionTier] = None
    
    def set_connection(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Set the DuckDB connection for the processor."""
        self.connection = connection
        self.logger.debug("DuckDB connection established")
    
    def set_tier(self, tier: MedallionTier) -> None:
        """Set the medallion architecture tier for this processor."""
        self.tier = tier
        self.logger.info(f"Processing tier set to {tier.value}")
    
    @abstractmethod
    def process(self, input_table: str) -> str:
        """Process data from input table to output table.
        
        Args:
            input_table: Name of the input table
            
        Returns:
            Name of the output table
        """
        pass
    
    @abstractmethod
    def validate_input(self, table_name: str) -> bool:
        """Validate input data meets processing requirements.
        
        Args:
            table_name: Name of the table to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_output(self, table_name: str) -> bool:
        """Validate output data meets quality requirements.
        
        Args:
            table_name: Name of the table to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics.
        
        Returns:
            Dictionary of processing metrics
        """
        pass
    
    def execute_sql(self, sql: str, params: Optional[tuple] = None) -> Any:
        """Execute SQL query on the DuckDB connection."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        if params:
            return self.connection.execute(sql, params)
        else:
            return self.connection.execute(sql)
    
    def create_table_from_query(self, table_name: str, query: str) -> str:
        """Create a new table from a SQL query safely."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        # Validate table name
        table = TableIdentifier(name=table_name)
        
        # Drop table if exists
        self.execute_sql(f"DROP TABLE IF EXISTS {table.qualified_name}")
        
        # Create new table
        self.execute_sql(f"CREATE TABLE {table.qualified_name} AS {query}")
        
        # Log table creation
        count = self.count_records(table.name)
        self.logger.debug(f"Created table {table.name} with {count} records")
        
        return table.name
    
    def count_records(self, table_name: str) -> int:
        """Count records in a table safely."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        table = TableIdentifier(name=table_name)
        result = self.execute_sql(f"SELECT COUNT(*) FROM {table.qualified_name}").fetchone()
        return result[0] if result else 0
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists safely."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        result = self.execute_sql(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            (table_name,)
        ).fetchone()
        
        return result[0] > 0 if result else False
    
    def drop_table(self, table_name: str, if_exists: bool = True) -> None:
        """Drop a table safely."""
        table = TableIdentifier(name=table_name)
        if_exists_clause = "IF EXISTS" if if_exists else ""
        self.execute_sql(f"DROP TABLE {if_exists_clause} {table.qualified_name}")
    
    def get_column_names(self, table_name: str) -> list[str]:
        """Get column names for a table."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        table = TableIdentifier(name=table_name)
        result = self.execute_sql(f"DESCRIBE {table.qualified_name}").fetchall()
        return [row[0] for row in result] if result else []
    
    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """Get schema (column names and types) for a table."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        table = TableIdentifier(name=table_name)
        result = self.execute_sql(f"DESCRIBE {table.qualified_name}").fetchall()
        return {row[0]: row[1] for row in result} if result else {}


class TransformationProcessor(BaseProcessor):
    """Processor that performs SQL transformations between medallion tiers."""
    
    @abstractmethod
    def get_transformation_query(self, input_table: str) -> str:
        """Get SQL transformation query for this processor.
        
        Args:
            input_table: Name of the input table
            
        Returns:
            SQL query string for transformation
        """
        pass
    
    def process(self, input_table: str) -> str:
        """Process data from input table using transformation query.
        
        Args:
            input_table: Name of the input table
            
        Returns:
            Name of the output table
        """
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        # Generate output table name
        import time
        timestamp = int(time.time())
        output_table = f"{self.tier.value}_{timestamp}"
        
        # Get transformation query
        transformation_query = self.get_transformation_query(input_table)
        
        # Create output table from transformation
        self.create_table_from_query(output_table, transformation_query)
        
        # Update metrics
        input_count = self.count_records(input_table)
        output_count = self.count_records(output_table)
        
        self.logger.info(
            f"Transformed {input_count} records to {output_count} records "
            f"in {output_table}"
        )
        
        return output_table
    
    def validate_input(self, table_name: str) -> bool:
        """Validate input data meets processing requirements."""
        return self.table_exists(table_name) and self.count_records(table_name) > 0
    
    def validate_output(self, table_name: str) -> bool:
        """Validate output data meets quality requirements."""
        return self.table_exists(table_name) and self.count_records(table_name) > 0
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics."""
        return getattr(self, 'metrics', {})