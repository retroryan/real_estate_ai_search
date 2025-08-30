"""SQL-safe table identifier validation.

This module provides type-safe table identifiers to prevent SQL injection.
Following DuckDB best practices for secure table operations.
"""

import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class TableIdentifier(BaseModel):
    """SQL-safe table identifier with validation.
    
    Prevents SQL injection by validating table names against strict patterns.
    Only allows alphanumeric characters and underscores, starting with a letter.
    """
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Table name (alphanumeric and underscore only)"
    )
    schema: str = Field(
        default="main",
        min_length=1,
        max_length=64,
        description="Schema name"
    )
    
    @field_validator('name')
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        """Validate table name against SQL injection patterns."""
        # Pattern: Must start with letter, then alphanumeric or underscore
        pattern = r'^[a-zA-Z][a-zA-Z0-9_]{0,63}$'
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid table name '{v}'. Must start with a letter and contain "
                f"only alphanumeric characters and underscores (max 64 chars)."
            )
        return v
    
    @field_validator('schema')
    @classmethod
    def validate_schema_name(cls, v: str) -> str:
        """Validate schema name against SQL injection patterns."""
        pattern = r'^[a-zA-Z][a-zA-Z0-9_]{0,63}$'
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid schema name '{v}'. Must start with a letter and contain "
                f"only alphanumeric characters and underscores (max 64 chars)."
            )
        return v
    
    @property
    def qualified_name(self) -> str:
        """Get fully qualified table name with schema.
        
        Returns properly quoted identifier for safe SQL usage.
        """
        if self.schema == "main":
            # DuckDB doesn't require schema prefix for main schema
            return f'"{self.name}"'
        return f'"{self.schema}"."{self.name}"'
    
    @property
    def unquoted_name(self) -> str:
        """Get unquoted table name (use only with parameterized queries)."""
        return self.name
    
    def drop_statement(self) -> str:
        """Generate safe DROP TABLE statement."""
        return f"DROP TABLE IF EXISTS {self.qualified_name}"
    
    def create_statement(self, select_query: str) -> str:
        """Generate safe CREATE TABLE AS statement.
        
        Args:
            select_query: The SELECT portion of the CREATE TABLE AS
            
        Returns:
            Safe CREATE TABLE AS statement
        """
        return f"CREATE TABLE {self.qualified_name} AS {select_query}"
    
    def select_count(self) -> str:
        """Generate safe SELECT COUNT(*) statement."""
        return f"SELECT COUNT(*) FROM {self.qualified_name}"
    
    def describe_statement(self) -> str:
        """Generate safe DESCRIBE statement."""
        return f"DESCRIBE {self.qualified_name}"


# Pre-defined table names for the pipeline
BRONZE_TABLES = {
    "properties": TableIdentifier(name="bronze_properties"),
    "neighborhoods": TableIdentifier(name="bronze_neighborhoods"),
    "wikipedia": TableIdentifier(name="bronze_wikipedia"),
}

SILVER_TABLES = {
    "properties": TableIdentifier(name="silver_properties"),
    "neighborhoods": TableIdentifier(name="silver_neighborhoods"),
    "wikipedia": TableIdentifier(name="silver_wikipedia"),
}

GOLD_TABLES = {
    "properties": TableIdentifier(name="gold_properties"),
    "neighborhoods": TableIdentifier(name="gold_neighborhoods"),
    "wikipedia": TableIdentifier(name="gold_wikipedia"),
    "market_summary": TableIdentifier(name="gold_market_summary"),
}

EMBEDDING_TABLES = {
    "properties": TableIdentifier(name="embeddings_properties"),
    "neighborhoods": TableIdentifier(name="embeddings_neighborhoods"),
    "wikipedia": TableIdentifier(name="embeddings_wikipedia"),
}