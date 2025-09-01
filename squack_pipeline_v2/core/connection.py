"""DuckDB connection management following best practices.

Key improvements:
- Configuration applied during connection creation (not after)
- Singleton pattern for connection reuse
- SQL injection prevention via parameterized queries
- Thread-safe operations
"""

import duckdb
import threading
from pathlib import Path
from typing import Optional, Any
from contextlib import contextmanager

from squack_pipeline_v2.core.settings import DuckDBConfig


class DuckDBConnectionManager:
    """Thread-safe singleton DuckDB connection manager.
    
    Follows DuckDB best practices:
    - Single connection reused across operations (performance)
    - Configuration applied during connection creation
    - SQL injection prevention through parameterized queries
    - Proper transaction management
    """
    
    _instance = None
    _lock = threading.Lock()
    _connection: Optional[duckdb.DuckDBPyConnection] = None
    _initialized = False
    
    def __new__(cls, settings: DuckDBConfig = None):
        """Ensure singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, settings: DuckDBConfig = None):
        """Initialize connection manager with settings.
        
        Args:
            settings: DuckDB configuration settings
        """
        # Only initialize once
        if not DuckDBConnectionManager._initialized:
            self.settings = settings or DuckDBConfig()
            DuckDBConnectionManager._initialized = True
    
    def connect(self) -> duckdb.DuckDBPyConnection:
        """Get or create DuckDB connection with proper configuration.
        
        Configuration is applied during connection creation for best performance.
        
        Returns:
            Configured DuckDB connection
        """
        if self._connection is None:
            with self._lock:
                if self._connection is None:
                    # Apply configuration during connection creation (best practice)
                    config = {
                        'memory_limit': self.settings.memory_limit,
                        'threads': self.settings.threads,
                        'max_memory': self.settings.memory_limit,  # v0.10.0+ feature
                    }
                    
                    # Create connection with configuration
                    self._connection = duckdb.connect(
                        database=self.settings.database_file,
                        config=config
                    )
                    
                    # Install and load required extensions
                    self._connection.execute("INSTALL json")
                    self._connection.execute("LOAD json")
                    
                    # Install parquet extension for efficient file operations
                    self._connection.execute("INSTALL parquet")
                    self._connection.execute("LOAD parquet")
        
        return self._connection
    
    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get the DuckDB connection for Relation API usage.
        
        Returns:
            DuckDB connection object
        """
        return self.connect()
    
    def disconnect(self) -> None:
        """Close the DuckDB connection."""
        if self._connection:
            with self._lock:
                if self._connection:
                    self._connection.close()
                    self._connection = None
    
    def close(self) -> None:
        """Close the DuckDB connection (alias for disconnect)."""
        self.disconnect()
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions.
        
        Ensures proper commit/rollback handling.
        
        Yields:
            DuckDB connection within a transaction
        """
        conn = self.connect()
        try:
            conn.execute("BEGIN TRANSACTION")
            yield conn
            conn.execute("COMMIT")
        except Exception as e:
            conn.execute("ROLLBACK")
            raise e
    
    def execute(
        self, 
        query: str, 
        parameters: Optional[tuple] = None
    ) -> duckdb.DuckDBPyRelation:
        """Execute a SQL query with optional parameters.
        
        Always use parameters for user-provided data to prevent SQL injection.
        
        Args:
            query: SQL query to execute
            parameters: Optional query parameters for safe interpolation
            
        Returns:
            Query result relation
        """
        conn = self.connect()
        if parameters:
            return conn.execute(query, parameters)
        return conn.execute(query)
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists
        """
        result = self.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            (table_name,)
        ).fetchone()
        return result[0] > 0 if result else False
    
    def drop_table(self, table_name: str) -> None:
        """Drop a table if it exists.
        
        Args:
            table_name: Name of the table to drop
        """
        self.execute(f"DROP TABLE IF EXISTS {table_name}")
    
    def count_records(self, table_name: str) -> int:
        """Count records in a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Number of records in table
        """
        if not self.table_exists(table_name):
            return 0
        
        result = self.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return result[0] if result else 0
    
    def get_table_schema(self, table_name: str) -> list:
        """Get schema information for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of tuples with (column_name, column_type)
        """
        if not self.table_exists(table_name):
            return []
        
        result = self.execute(f"DESCRIBE {table_name}").fetchall()
        return result
    
    def create_table_as(
        self, 
        table_name: str, 
        select_query: str,
        parameters: Optional[tuple] = None
    ) -> None:
        """Create table from SELECT query.
        
        Args:
            table_name: Name of table to create
            select_query: SELECT query to create table from
            parameters: Optional parameters for the SELECT query
        """
        # Drop if exists
        self.drop_table(table_name)
        
        # Create table
        create_sql = f"CREATE TABLE {table_name} AS {select_query}"
        self.execute(create_sql, parameters)
    
    def copy_to_parquet(
        self,
        table_name: str,
        output_path: Path,
        compression: str = 'snappy'
    ) -> None:
        """Export table to Parquet file.
        
        Args:
            table_name: Name of table to export
            output_path: Path for output Parquet file
            compression: Parquet compression type
        """
        query = f"""
        COPY {table_name} 
        TO '{output_path.absolute()}'
        (FORMAT PARQUET, COMPRESSION '{compression}')
        """
        self.execute(query)
    
    def read_parquet(
        self,
        file_path: Path,
        table_name: str,
        sample_size: Optional[int] = None
    ) -> None:
        """Read Parquet file into table.
        
        Args:
            file_path: Path to Parquet file
            table_name: Name of table to create
            sample_size: Optional number of records to load
        """
        # Build SELECT query
        select_query = f"SELECT * FROM read_parquet('{file_path.absolute()}')"
        if sample_size:
            select_query += f" LIMIT {sample_size}"
        
        # Create table
        self.create_table_as(table_name, select_query)
    
    def analyze_query(self, query: str) -> list:
        """Analyze query performance using EXPLAIN ANALYZE.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Query execution plan with timing
        """
        explain_query = f"EXPLAIN ANALYZE {query}"
        return self.execute(explain_query).fetchall()
    
    def get_query_plan(self, query: str) -> list:
        """Get query execution plan using EXPLAIN.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Query execution plan
        """
        explain_query = f"EXPLAIN {query}"
        return self.execute(explain_query).fetchall()
    
    def __enter__(self):
        """Enter context manager."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - connection persists (singleton)."""
        # Don't disconnect on exit - maintain singleton connection
        pass
    
    def __del__(self):
        """Cleanup on deletion."""
        self.disconnect()