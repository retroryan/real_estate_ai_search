"""DuckDB connection management following best practices."""

from contextlib import contextmanager
from typing import Optional, Any, Generator
import duckdb

from squack_pipeline.models.duckdb_models import (
    DuckDBConnectionConfig,
    TableIdentifier
)
from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.utils.logging import PipelineLogger


class DuckDBConnectionManager:
    """DuckDB connection manager following best practices."""
    
    _instance: Optional['DuckDBConnectionManager'] = None
    _connection: Optional[duckdb.DuckDBPyConnection] = None
    
    def __new__(cls) -> 'DuckDBConnectionManager':
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
            cls._instance.database_path = ":memory:"
            cls._instance.logger = PipelineLogger.get_logger(cls.__name__)
            cls._instance.config = None
        return cls._instance
    
    def initialize(self, settings: PipelineSettings) -> None:
        """Initialize connection with validated configuration."""
        # Build config from settings
        config = DuckDBConnectionConfig(
            database_path=settings.duckdb.database_path,
            memory_limit=settings.duckdb.memory_limit,
            threads=settings.duckdb.threads,
            preserve_insertion_order=settings.duckdb.preserve_insertion_order,
        )
        
        if self.initialized and self._connection:
            if self.database_path == config.database_path:
                self.logger.info(f"Connection already initialized to {self.database_path}")
                return
            else:
                # Different database requested, close existing
                self.close()
        
        # Create new connection with config
        duckdb_config = config.to_duckdb_config()
        self._connection = duckdb.connect(
            database=config.database_path,
            config=duckdb_config
        )
        
        # Store config and update state
        self.config = config
        self.initialized = True
        self.database_path = str(config.database_path)
        
        # Apply any additional parquet settings
        self._apply_parquet_settings(settings)
        
        self.logger.info(f"DuckDB initialized: {config.database_path}")
    
    def _apply_parquet_settings(self, settings: PipelineSettings) -> None:
        """Apply parquet-specific settings that can't be set in config."""
        if not self._connection:
            return
            
        try:
            compression = settings.parquet.compression
            self._connection.execute(f"SET force_compression = '{compression}'")
        except Exception:
            self.logger.debug("Could not set parquet compression, using defaults")
    
    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get the raw connection."""
        if not self._connection:
            raise RuntimeError("Connection not initialized. Call initialize() first.")
        return self._connection
    
    @contextmanager
    def get_connection_context(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """Get connection as context manager for safety."""
        if not self._connection:
            raise RuntimeError("Connection not initialized. Call initialize() first.")
        
        try:
            yield self._connection
        except Exception as e:
            self.logger.error(f"Error in DuckDB operation: {e}")
            raise
    
    def execute_safe(self, query: str, params: Optional[tuple] = None) -> Any:
        """Execute query safely with proper error handling."""
        if not self._connection:
            raise RuntimeError("Connection not initialized. Call initialize() first.")
        
        try:
            if params:
                return self._connection.execute(query, params)
            return self._connection.execute(query)
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            raise
    
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """Execute query and return result."""
        with self.get_connection_context() as conn:
            if params:
                return conn.execute(query, params)
            else:
                return conn.execute(query)
    
    def execute_on_table(self, table: TableIdentifier, operation: str, **kwargs) -> Any:
        """Execute operation on a validated table."""
        operations = {
            'count': f"SELECT COUNT(*) FROM {table.qualified_name}",
            'describe': f"DESCRIBE {table.qualified_name}",
            'drop': f"DROP TABLE IF EXISTS {table.qualified_name}",
            'truncate': f"TRUNCATE {table.qualified_name}",
        }
        
        if operation not in operations:
            raise ValueError(f"Unknown operation: {operation}")
        
        query = operations[operation]
        
        # Add LIMIT if provided
        if operation == 'select' and 'limit' in kwargs:
            query = f"SELECT * FROM {table.qualified_name} LIMIT {int(kwargs['limit'])}"
        
        return self.execute(query)
    
    def table_exists(self, table: TableIdentifier) -> bool:
        """Check if table exists using safe query."""
        result = self.execute_safe(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ? AND table_schema = COALESCE(?, 'main')",
            (table.name, table.schema if table.schema else 'main')
        )
        row = result.fetchone() if result else None
        return bool(row and row[0] > 0)
    
    def get_table_info(self, table: TableIdentifier) -> dict:
        """Get table information safely."""
        if not self.table_exists(table):
            return {"exists": False}
        
        # Get schema
        schema_result = self.execute_safe(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = ? AND table_schema = COALESCE(?, 'main')",
            (table.name, table.schema)
        )
        schema_rows = schema_result.fetchall() if schema_result else []
        
        # Get row count - table is pre-validated
        count_result = self.execute_safe(
            f"SELECT COUNT(*) FROM {table.qualified_name}"
        )
        count_row = count_result.fetchone() if count_result else None
        
        return {
            "exists": True,
            "row_count": count_row[0] if count_row else 0,
            "schema": [
                {"name": row[0], "type": row[1], "nullable": row[2] == "YES"}
                for row in schema_rows
            ]
        }
    
    def list_tables(self) -> list[str]:
        """List all tables in the database."""
        result = self.execute_safe(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        )
        rows = result.fetchall() if result else []
        return [row[0] for row in rows]
    
    def drop_table(self, table: TableIdentifier, if_exists: bool = True) -> None:
        """Safely drop a table."""
        if_exists_clause = "IF EXISTS" if if_exists else ""
        query = f"DROP TABLE {if_exists_clause} {table.qualified_name}"
        self.execute_safe(query)
    
    def execute_on_table(self, table: TableIdentifier, query_template: str) -> Any:
        """Execute query on validated table."""
        # Table name is pre-validated by Pydantic
        query = query_template.format(table=table.qualified_name)
        return self.execute_safe(query)
    
    def table_exists(self, table: TableIdentifier) -> bool:
        """Check if table exists using safe query."""
        result = self.execute_safe(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ? AND table_schema = COALESCE(?, 'main')",
            (table.name, table.schema)
        )
        row = result.fetchone()
        return bool(row and row[0] > 0)
    
    def close(self) -> None:
        """Close the connection and reset state."""
        if self._connection:
            self._connection.close()
            self._connection = None
        
        self.initialized = False
        self.database_path = ":memory:"
        self.config = None
        self.logger.info("Connection closed and state reset")
    
    def __enter__(self) -> 'DuckDBConnectionManager':
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        if exc_type:
            self.logger.error(f"Exception in DuckDB context: {exc_val}")
        # Don't auto-close - allow reuse across pipeline