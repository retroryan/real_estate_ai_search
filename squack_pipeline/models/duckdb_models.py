"""Pydantic models for DuckDB configuration and validation."""

from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class DuckDBConnectionConfig(BaseModel):
    """Validated DuckDB connection configuration."""
    
    database_path: str = Field(
        default=":memory:", 
        description="Database file path or :memory:"
    )
    memory_limit: str = Field(
        default="8GB", 
        pattern=r"^\d+[KMG]B$",
        description="Memory limit for DuckDB"
    )
    threads: int = Field(
        default=4, 
        ge=1, 
        le=64,
        description="Number of threads for DuckDB"
    )
    preserve_insertion_order: bool = Field(
        default=True,
        description="Preserve data insertion order"
    )
    enable_object_cache: bool = Field(
        default=True,
        description="Enable object cache for better performance"
    )
    
    @field_validator('database_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Ensure parent directory exists for file databases."""
        if not v.startswith(":memory"):
            path = Path(v)
            path.parent.mkdir(parents=True, exist_ok=True)
        return v
    
    def to_duckdb_config(self) -> Dict[str, Any]:
        """Convert to DuckDB connection config dictionary."""
        # Only include valid DuckDB configuration options
        return {
            'memory_limit': self.memory_limit,
            'threads': self.threads,
            'preserve_insertion_order': self.preserve_insertion_order,
            'enable_object_cache': self.enable_object_cache,
        }


class TableIdentifier(BaseModel):
    """Safe table identifier with validation."""
    
    name: str = Field(
        ..., 
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$",
        description="Table name"
    )
    schema: Optional[str] = Field(
        default="main", 
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$",
        description="Schema name"
    )
    
    @property
    def qualified_name(self) -> str:
        """Get fully qualified table name."""
        if self.schema and self.schema != "main":
            return f"{self.schema}.{self.name}"
        return self.name
    
    @classmethod
    def from_string(cls, table_string: str) -> 'TableIdentifier':
        """Create from a string like 'schema.table' or 'table'."""
        parts = table_string.split('.')
        if len(parts) == 2:
            return cls(schema=parts[0], name=parts[1])
        elif len(parts) == 1:
            return cls(name=parts[0])
        else:
            raise ValueError(f"Invalid table identifier: {table_string}")


class ConnectionState(BaseModel):
    """Track connection state using Pydantic."""
    
    initialized: bool = Field(default=False, description="Connection initialized")
    database_path: str = Field(default=":memory:", description="Current database path")
    connection_id: Optional[str] = Field(default=None, description="Connection identifier")


class QueryResult(BaseModel):
    """Structured query result."""
    
    rows: list = Field(default_factory=list, description="Query result rows")
    columns: list[str] = Field(default_factory=list, description="Column names")
    row_count: int = Field(default=0, description="Number of rows returned")
    
    def to_dicts(self) -> list[Dict[str, Any]]:
        """Convert rows to list of dictionaries."""
        return [dict(zip(self.columns, row)) for row in self.rows]
    
    def first(self) -> Optional[Dict[str, Any]]:
        """Get first row as dictionary."""
        if self.rows:
            return dict(zip(self.columns, self.rows[0]))
        return None