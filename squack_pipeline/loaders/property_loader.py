"""Property data loader using DuckDB best practices."""

from pathlib import Path
from typing import Dict, Any, Optional

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.loaders.base import BaseLoader
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.models.duckdb_models import TableIdentifier
from squack_pipeline.utils.logging import log_execution_time


class PropertyLoader(BaseLoader):
    """Loader for property JSON data."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize property loader."""
        super().__init__(settings)
        self.connection_manager = DuckDBConnectionManager()
    
    def get_schema(self) -> Dict[str, str]:
        """Get expected property data schema."""
        return {
            "listing_id": "VARCHAR",
            "neighborhood_id": "VARCHAR",
            "address": "STRUCT",
            "coordinates": "STRUCT",
            "property_details": "STRUCT",
            "listing_price": "DOUBLE",
            "price_per_sqft": "DOUBLE",
            "description": "VARCHAR",
            "features": "VARCHAR[]",
            "listing_date": "DATE",
            "days_on_market": "INTEGER",
            "virtual_tour_url": "VARCHAR",
            "images": "VARCHAR[]",
            "price_history": "STRUCT[]"
        }
    
    @log_execution_time
    def load(self, source: Path, table_name: str = "raw_properties", sample_size: Optional[int] = None) -> str:
        """Load property data from JSON file into DuckDB."""
        if not source.exists():
            raise FileNotFoundError(f"Property data file not found: {source}")
        
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
        
        # Load JSON data directly into DuckDB
        load_query = f"""
        CREATE TABLE {table.qualified_name} AS
        SELECT *
        FROM read_json_auto('{source.absolute()}')
        {f'LIMIT {sample_size}' if sample_size else ''}
        """
        
        self.connection_manager.execute_safe(load_query)
        
        # Log loading results
        count = self.count_records(table.name)
        self.logger.success(f"Loaded {count} properties from {source.name}")
        
        return table.name
    
    def validate(self, table_name: str) -> bool:
        """Validate loaded property data."""
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
            
            # Validate required fields - using parameterized queries where possible
            required_fields = ["listing_id", "listing_price", "description"]
            
            for field in required_fields:
                # For column names in WHERE clause, we need to validate they exist first
                column_exists = any(col["name"] == field for col in info["schema"])
                if not column_exists:
                    self.logger.error(f"Required field {field} not found in table")
                    return False
                
                # Safe query since we validated column exists
                result = self.connection_manager.execute_safe(
                    f"SELECT COUNT(*) FROM {table.qualified_name} WHERE {field} IS NULL"
                )
                
                null_count = result.fetchone()[0] if result else 0
                if null_count > 0:
                    self.logger.warning(f"Found {null_count} null values in {field}")
            
            # Validate price values are positive
            result = self.connection_manager.execute_safe(
                f"SELECT COUNT(*) FROM {table.qualified_name} WHERE listing_price <= 0"
            )
            
            invalid_prices = result.fetchone()[0] if result else 0
            if invalid_prices > 0:
                self.logger.error(f"Found {invalid_prices} properties with invalid prices")
                return False
            
            self.logger.success(f"Property data validation passed for {table.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return False
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> Optional[list]:
        """Get sample property data for inspection."""
        table = TableIdentifier(name=table_name)
        
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError(f"Invalid limit: {limit}")
        
        try:
            result = self.connection_manager.execute(
                f"""
                SELECT 
                    listing_id,
                    listing_price,
                    property_details.bedrooms as bedrooms,
                    property_details.bathrooms as bathrooms,
                    address.city as city,
                    description
                FROM {table.qualified_name}
                LIMIT {limit}
                """
            )
            
            return result.to_dicts()
            
        except Exception as e:
            self.logger.error(f"Failed to get sample data: {e}")
            return None