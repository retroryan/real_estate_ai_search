"""Base processor interface for data processing operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import duckdb

from squack_pipeline.config.schemas import MedallionTier
from squack_pipeline.config.settings import PipelineSettings
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
        """Create a new table from a SQL query."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        # Drop table if exists
        self.execute_sql(f"DROP TABLE IF EXISTS {table_name}")
        
        # Create new table
        self.execute_sql(f"CREATE TABLE {table_name} AS {query}")
        
        # Log table creation
        count = self.count_records(table_name)
        self.logger.info(f"Created table {table_name} with {count} records")
        
        return table_name
    
    def count_records(self, table_name: str) -> int:
        """Count records in a table."""
        result = self.execute_sql(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return result[0] if result else 0
    
    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """Get the schema of a table."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        result = self.execute_sql(
            f"SELECT column_name, data_type "
            f"FROM information_schema.columns "
            f"WHERE table_name = '{table_name}'"
        ).fetchall()
        
        return {row[0]: row[1] for row in result}


class TransformationProcessor(BaseProcessor):
    """Base class for transformation processors."""
    
    @abstractmethod
    def get_transformation_query(self, input_table: str) -> str:
        """Get the SQL transformation query.
        
        Args:
            input_table: Name of the input table
            
        Returns:
            SQL query string for transformation
        """
        pass
    
    def process(self, input_table: str, output_table: Optional[str] = None) -> bool:
        """Process data using SQL transformation.
        
        Args:
            input_table: Name of the input table
            output_table: Name of the output table (optional, will be generated if not provided)
            
        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            # Validate input
            if not self.validate_input(input_table):
                self.logger.error(f"Input validation failed for table {input_table}")
                return False
            
            # Get transformation query
            query = self.get_transformation_query(input_table)
            
            # Generate output table name if not provided
            if not output_table:
                output_table = f"{self.tier.value}_{input_table}" if self.tier else f"processed_{input_table}"
            
            # Execute transformation
            self.create_table_from_query(output_table, query)
            
            # Validate output
            if not self.validate_output(output_table):
                self.logger.error(f"Output validation failed for table {output_table}")
                return False
            
            self.logger.success(f"Successfully processed {input_table} → {output_table}")
            return True
            
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            return False