"""Property data loader using DuckDB."""

from pathlib import Path
from typing import Dict, Any, Optional

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.loaders.base import BaseLoader
from squack_pipeline.loaders.connection import DuckDBConnectionManager
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
    def load(self, source: Path) -> str:
        """Load property data from JSON file into DuckDB."""
        if not source.exists():
            raise FileNotFoundError(f"Property data file not found: {source}")
        
        table_name = "raw_properties"
        
        # Initialize connection if needed
        if not self.connection:
            self.connection_manager.initialize(self.settings)
            self.connection = self.connection_manager.get_connection()
        
        # Drop existing table
        self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Load JSON data directly into DuckDB
        load_query = f"""
        CREATE TABLE {table_name} AS
        SELECT *
        FROM read_json_auto('{source.absolute()}')
        """
        
        # Apply sample size if specified
        if self.settings.data.sample_size:
            load_query += f" LIMIT {self.settings.data.sample_size}"
        
        self.connection.execute(load_query)
        
        # Log loading results
        count = self.count_records(table_name)
        self.logger.success(f"Loaded {count} properties from {source.name}")
        
        return table_name
    
    def validate(self, table_name: str) -> bool:
        """Validate loaded property data."""
        if not self.connection:
            return False
        
        try:
            # Check required columns exist
            info = self.connection_manager.get_table_info(table_name)
            if not info["exists"]:
                self.logger.error(f"Table {table_name} does not exist")
                return False
            
            if info["row_count"] == 0:
                self.logger.warning(f"Table {table_name} is empty")
                return False
            
            # Validate required fields
            required_fields = ["listing_id", "listing_price", "description"]
            
            for field in required_fields:
                result = self.connection.execute(
                    f"SELECT COUNT(*) FROM {table_name} WHERE {field} IS NULL"
                ).fetchone()
                
                null_count = result[0] if result else 0
                if null_count > 0:
                    self.logger.warning(f"Found {null_count} null values in {field}")
            
            # Validate price values are positive
            result = self.connection.execute(
                f"SELECT COUNT(*) FROM {table_name} WHERE listing_price <= 0"
            ).fetchone()
            
            invalid_prices = result[0] if result else 0
            if invalid_prices > 0:
                self.logger.error(f"Found {invalid_prices} properties with invalid prices")
                return False
            
            self.logger.success(f"Property data validation passed for {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return False
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> Optional[list]:
        """Get sample property data for inspection."""
        if not self.connection:
            return None
        
        try:
            result = self.connection.execute(
                f"""
                SELECT 
                    listing_id,
                    listing_price,
                    property_details.bedrooms as bedrooms,
                    property_details.bathrooms as bathrooms,
                    address.city as city,
                    description
                FROM {table_name}
                LIMIT {limit}
                """
            ).fetchall()
            
            # Convert to list of dictionaries
            columns = ["listing_id", "listing_price", "bedrooms", "bathrooms", "city", "description"]
            return [dict(zip(columns, row)) for row in result]
            
        except Exception as e:
            self.logger.error(f"Failed to get sample data: {e}")
            return None