"""
Database connection management with constructor injection.
Handles SQLite database connections for Wikipedia data.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    SQLite database connection manager.
    All configuration is injected through constructor.
    """
    
    def __init__(self, db_path: Path):
        """
        Initialize database connection with explicit path.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Verify database exists and is accessible
        if not self.db_path.exists():
            logger.warning(f"Database file does not exist: {self.db_path}")
        else:
            logger.info(f"Database connection initialized: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as list of dicts.
        
        Args:
            query: SQL SELECT query
            params: Query parameters for safe parameterization
            
        Returns:
            List of dictionaries representing rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Convert Row objects to dictionaries
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def execute_scalar(self, query: str, params: Optional[tuple] = None) -> Any:
        """
        Execute a query and return a single scalar value.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Single scalar value or None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            result = cursor.fetchone()
            return result[0] if result else None
    
    def execute_command(self, command: str, params: Optional[tuple] = None) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE command.
        
        Args:
            command: SQL command
            params: Command parameters
            
        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if params:
                cursor.execute(command, params)
            else:
                cursor.execute(command)
            
            conn.commit()
            return cursor.rowcount
    
    def execute_many(self, command: str, params_list: List[tuple]) -> int:
        """
        Execute a command with multiple parameter sets.
        
        Args:
            command: SQL command
            params_list: List of parameter tuples
            
        Returns:
            Total number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(command, params_list)
            conn.commit()
            return cursor.rowcount
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table
            
        Returns:
            True if table exists, False otherwise
        """
        query = """
            SELECT COUNT(*) 
            FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        count = self.execute_scalar(query, (table_name,))
        return count > 0
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get information about table columns.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        query = f"PRAGMA table_info({table_name})"
        return self.execute_query(query)