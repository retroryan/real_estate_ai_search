"""Base loader interface for data loading operations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
from pydantic import BaseModel

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.utils.logging import PipelineLogger


class BaseLoader(ABC):
    """Abstract base class for all data loaders."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize the loader with pipeline settings."""
        self.settings = settings
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.connection: Optional[duckdb.DuckDBPyConnection] = None
    
    def set_connection(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Set the DuckDB connection for the loader."""
        self.connection = connection
        self.logger.debug("DuckDB connection established")
    
    @abstractmethod
    def load(self, source: Path) -> str:
        """Load data from source into DuckDB table.
        
        Args:
            source: Path to the data source
            
        Returns:
            Name of the created table in DuckDB
        """
        pass
    
    @abstractmethod
    def validate(self, table_name: str) -> bool:
        """Validate loaded data meets requirements.
        
        Args:
            table_name: Name of the table to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, str]:
        """Get the expected schema for this loader.
        
        Returns:
            Dictionary mapping column names to types
        """
        pass
    
    def count_records(self, table_name: str) -> int:
        """Count records in a table."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        result = self.connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return result[0] if result else 0
    
    def get_sample(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample records from a table."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        result = self.connection.execute(
            f"SELECT * FROM {table_name} LIMIT {limit}"
        ).fetchall()
        
        # Get column names
        columns = [desc[0] for desc in self.connection.description]
        
        # Convert to list of dictionaries
        return [dict(zip(columns, row)) for row in result]
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in DuckDB."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        result = self.connection.execute(
            f"SELECT COUNT(*) FROM information_schema.tables "
            f"WHERE table_name = '{table_name}'"
        ).fetchone()
        
        return result[0] > 0 if result else False