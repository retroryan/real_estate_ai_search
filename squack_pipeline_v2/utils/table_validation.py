"""Table name validation utilities following DuckDB best practices."""

import re
from typing import Optional


def validate_table_name(name: str) -> str:
    """Validate table name follows DuckDB naming conventions.
    
    DuckDB Best Practice: Validate table names at entry points.
    Valid table names must:
    - Start with a letter
    - Contain only letters, numbers, and underscores
    - Be between 1 and 64 characters
    
    Args:
        name: Table name to validate
        
    Returns:
        The validated table name
        
    Raises:
        ValueError: If table name is invalid
    """
    if not name:
        raise ValueError("Table name cannot be empty")
    
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{0,63}$', name):
        raise ValueError(
            f"Invalid table name: {name}. "
            "Table names must start with a letter and contain only "
            "letters, numbers, and underscores (max 64 characters)"
        )
    
    return name


def validate_column_name(name: str) -> str:
    """Validate column name follows DuckDB conventions.
    
    Args:
        name: Column name to validate
        
    Returns:
        The validated column name
        
    Raises:
        ValueError: If column name is invalid
    """
    if not name:
        raise ValueError("Column name cannot be empty")
    
    # DuckDB allows more flexibility with column names but we enforce stricter rules
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]{0,127}$', name):
        raise ValueError(
            f"Invalid column name: {name}. "
            "Column names must start with a letter or underscore and contain only "
            "letters, numbers, and underscores (max 128 characters)"
        )
    
    return name


def safe_identifier(identifier: str, identifier_type: str = "table") -> str:
    """Create a safe SQL identifier by validating and optionally quoting.
    
    Args:
        identifier: The identifier to make safe
        identifier_type: Type of identifier ("table", "column", "schema")
        
    Returns:
        A safe identifier for use in SQL
    """
    if identifier_type == "table":
        return validate_table_name(identifier)
    elif identifier_type == "column":
        return validate_column_name(identifier)
    else:
        # For other types, apply basic validation
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]{0,127}$', identifier):
            raise ValueError(f"Invalid {identifier_type} name: {identifier}")
        return identifier