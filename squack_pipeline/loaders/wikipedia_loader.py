"""Wikipedia data loader using DuckDB's SQLite extension."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import sqlite3

from pydantic import ValidationError

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.loaders.base import BaseLoader
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.models.duckdb_models import TableIdentifier
from squack_pipeline.models.data_models import WikipediaArticle, DataLoadingMetrics, ValidationResult
from squack_pipeline.utils.logging import log_execution_time


class WikipediaLoader(BaseLoader):
    """Loader for Wikipedia SQLite database."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize Wikipedia loader."""
        super().__init__(settings)
        self.connection_manager = DuckDBConnectionManager()
    
    def get_schema(self) -> Dict[str, str]:
        """Get expected Wikipedia article schema."""
        return {
            "page_id": "VARCHAR",
            "title": "VARCHAR",
            "url": "VARCHAR",
            "summary": "VARCHAR",
            "content": "VARCHAR",
            "categories": "VARCHAR[]",
            "latitude": "DOUBLE",
            "longitude": "DOUBLE",
            "relevance_score": "DOUBLE",
            "last_modified": "TIMESTAMP"
        }
    
    @log_execution_time
    def load(self, table_name: str, source: Optional[Path] = None, sample_size: Optional[int] = None) -> str:
        """Load Wikipedia data from configured SQLite database into DuckDB."""
        # Use configured Wikipedia database path
        db_path = self.settings.data_sources.wikipedia_db_path
        
        # Validate database exists
        if not db_path.exists():
            raise FileNotFoundError(f"Wikipedia database not found: {db_path}")
        
        # Create validated table identifier
        table = TableIdentifier(name=table_name)
        
        # Initialize connection if needed
        if not self.connection:
            self.connection_manager.initialize(self.settings)
            self.connection = self.connection_manager.get_connection()
        
        # Drop existing table safely
        self.connection_manager.drop_table(table, if_exists=True)
        
        # Determine sample size
        sample_size = sample_size or self.settings.data.sample_size
        
        try:
            # Install and load SQLite extension if needed
            self.connection_manager.execute_safe("INSTALL sqlite")
            self.connection_manager.execute_safe("LOAD sqlite")
            
            # Attach the SQLite database
            attach_query = f"ATTACH '{db_path.absolute()}' AS wiki (TYPE sqlite)"
            self.connection_manager.execute_safe(attach_query)
            
            # Create DuckDB table from SQLite articles table
            # Handle sample size if specified
            if sample_size:
                load_query = f"""
                CREATE TABLE {table.qualified_name} AS
                SELECT * FROM wiki.articles
                LIMIT {sample_size}
                """
            else:
                load_query = f"""
                CREATE TABLE {table.qualified_name} AS
                SELECT * FROM wiki.articles
                """
            
            self.connection_manager.execute_safe(load_query)
            
            # Detach to release locks
            self.connection_manager.execute_safe("DETACH wiki")
            
            # Log loading results
            count = self.count_records(table.name)
            self.logger.success(f"Loaded {count} Wikipedia articles from {db_path.name}")
            
            return table.name
            
        except Exception as e:
            # Try to detach if attach succeeded but load failed
            try:
                self.connection_manager.execute_safe("DETACH wiki")
            except:
                pass
            raise e
    
    def validate(self, table_name: str) -> bool:
        """Validate loaded Wikipedia data."""
        table = TableIdentifier(name=table_name)
        
        try:
            # Check table exists and has data
            info = self.connection_manager.get_table_info(table)
            if not info["exists"]:
                self.logger.error(f"Table {table.name} does not exist")
                return False
            
            if info["row_count"] == 0:
                self.logger.warning(f"Table {table.name} is empty")
                return False
            
            # Validate required fields
            required_fields = ["pageid", "title"]
            
            for field in required_fields:
                # Check column exists
                column_exists = any(col["name"] == field for col in info["schema"])
                if not column_exists:
                    self.logger.error(f"Required field {field} not found in table")
                    return False
                
                # Check for nulls
                result = self.connection_manager.execute_safe(
                    f"SELECT COUNT(*) FROM {table.qualified_name} WHERE {field} IS NULL"
                )
                
                null_count = result.fetchone()[0] if result else 0
                if null_count > 0:
                    self.logger.warning(f"Found {null_count} null values in {field}")
            
            # Check relevance scores if present
            if any(col["name"] == "relevance_score" for col in info["schema"]):
                result = self.connection_manager.execute_safe(
                    f"""
                    SELECT COUNT(*) FROM {table.qualified_name}
                    WHERE relevance_score < 0 OR relevance_score > 1
                    """
                )
                
                invalid_scores = result.fetchone()[0] if result else 0
                if invalid_scores > 0:
                    self.logger.warning(f"Found {invalid_scores} articles with invalid relevance scores")
            
            self.logger.success(f"Wikipedia data validation passed for {table.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return False
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> Optional[list]:
        """Get sample Wikipedia data for inspection."""
        table = TableIdentifier(name=table_name)
        
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError(f"Invalid limit: {limit}")
        
        try:
            result = self.connection_manager.execute(
                f"""
                SELECT 
                    pageid as page_id,
                    title,
                    relevance_score,
                    SUBSTRING(extract, 1, 100) as summary_preview
                FROM {table.qualified_name}
                ORDER BY relevance_score DESC NULLS LAST
                LIMIT {limit}
                """
            )
            
            return result.to_dicts()
            
        except Exception as e:
            self.logger.error(f"Failed to get sample data: {e}")
            return None