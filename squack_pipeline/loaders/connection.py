"""DuckDB connection management for the pipeline."""

from pathlib import Path
from typing import Optional, Dict, Any

import duckdb

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.utils.logging import PipelineLogger, log_execution_time


class DuckDBConnectionManager:
    """Singleton DuckDB connection manager."""
    
    _instance: Optional['DuckDBConnectionManager'] = None
    _connection: Optional[duckdb.DuckDBPyConnection] = None
    
    def __new__(cls) -> 'DuckDBConnectionManager':
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize connection manager."""
        if not hasattr(self, 'initialized'):
            self.logger = PipelineLogger.get_logger(self.__class__.__name__)
            self.settings: Optional[PipelineSettings] = None
            self.initialized = True
    
    @log_execution_time
    def initialize(self, settings: PipelineSettings) -> None:
        """Initialize connection with settings."""
        self.settings = settings
        
        if self._connection is not None:
            self.logger.info("DuckDB connection already initialized")
            return
        
        # Create connection
        db_path = settings.duckdb.database_path
        self._connection = duckdb.connect(db_path)
        
        # Configure DuckDB settings
        self._configure_duckdb()
        
        self.logger.info(f"DuckDB connection initialized: {db_path}")
    
    def _configure_duckdb(self) -> None:
        """Configure DuckDB with optimal settings."""
        if not self._connection or not self.settings:
            return
        
        config = self.settings.duckdb
        
        # Memory and performance settings
        self._connection.execute(f"SET memory_limit = '{config.memory_limit}'")
        self._connection.execute(f"SET threads = {config.threads}")
        
        # Progress and output settings
        if config.enable_progress_bar:
            self._connection.execute("SET enable_progress_bar = true")
        
        if config.preserve_insertion_order:
            self._connection.execute("SET preserve_insertion_order = true")
        
        # Parquet settings (DuckDB 1.0+ uses different parameter name)
        parquet_config = self.settings.parquet
        try:
            self._connection.execute(f"SET force_compression = '{parquet_config.compression}'")
        except Exception:
            # Fallback for different DuckDB versions
            self.logger.debug("Could not set compression setting, using defaults")
        
        self.logger.debug("DuckDB configuration applied")
    
    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get the DuckDB connection."""
        if self._connection is None:
            raise RuntimeError("DuckDB connection not initialized. Call initialize() first.")
        return self._connection
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> Any:
        """Execute a query and return results."""
        connection = self.get_connection()
        
        if params:
            return connection.execute(query, params)
        else:
            return connection.execute(query)
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a table."""
        connection = self.get_connection()
        
        # Check if table exists
        result = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            (table_name,)
        ).fetchone()
        
        if not result or result[0] == 0:
            return {"exists": False}
        
        # Get table schema
        schema_result = connection.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns WHERE table_name = ?",
            (table_name,)
        ).fetchall()
        
        # Get row count
        count_result = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        
        return {
            "exists": True,
            "row_count": count_result[0] if count_result else 0,
            "schema": [
                {"name": row[0], "type": row[1], "nullable": row[2] == "YES"}
                for row in schema_result
            ]
        }
    
    def list_tables(self) -> list[str]:
        """List all tables in the database."""
        connection = self.get_connection()
        result = connection.execute(
            "SELECT table_name FROM information_schema.tables"
        ).fetchall()
        return [row[0] for row in result]
    
    def close(self) -> None:
        """Close the DuckDB connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            self.logger.info("DuckDB connection closed")
    
    def __enter__(self) -> 'DuckDBConnectionManager':
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        if exc_type:
            self.logger.error(f"Exception in DuckDB context: {exc_val}")
        # Don't close connection automatically - let it be reused