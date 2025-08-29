"""Location data loader using DuckDB best practices."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import json

from pydantic import ValidationError

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.loaders.base import BaseLoader
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.models.duckdb_models import TableIdentifier
from squack_pipeline.models.data_models import Location, DataLoadingMetrics, ValidationResult
from squack_pipeline.utils.logging import log_execution_time


class LocationLoader(BaseLoader):
    """Loader for location JSON data."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize location loader."""
        super().__init__(settings)
        self.connection_manager = DuckDBConnectionManager()
    
    def get_schema(self) -> Dict[str, str]:
        """Get expected location data schema."""
        return {
            "location_id": "VARCHAR",
            "name": "VARCHAR",
            "type": "VARCHAR",
            "city": "VARCHAR",
            "state": "VARCHAR",
            "country": "VARCHAR",
            "latitude": "DOUBLE",
            "longitude": "DOUBLE",
            "population": "INTEGER",
            "timezone": "VARCHAR",
            "metadata": "STRUCT"
        }
    
    @log_execution_time
    def load(self, table_name: str, source: Optional[Path] = None, sample_size: Optional[int] = None) -> str:
        """Load location data from configured JSON file into DuckDB using Pydantic validation and Bronze layer standardization."""
        # Use configured location file
        location_file = self.settings.data_sources.locations_file
        
        # Validate file exists
        if not location_file.exists():
            raise FileNotFoundError(f"Location data file not found: {location_file}")
        
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
        
        # Load and validate data using Pydantic models
        self.logger.info("Loading and validating location data using Pydantic models...")
        all_locations = []
        
        with open(location_file, 'r') as f:
            data = json.load(f)
        
        for record in data:
            try:
                # Validate using Pydantic model
                location_model = Location(**record)
                all_locations.append(location_model)
                
                # Apply sample size limit if specified
                if sample_size and len(all_locations) >= sample_size:
                    break
                    
            except ValidationError as e:
                self.logger.warning("Skipping invalid location record: %s", str(e))
        
        # Create Bronze layer table schema using Location model
        self._create_bronze_table_schema(table)
        
        # Insert validated data into Bronze table
        self._insert_location_data(table, all_locations)
        
        # Log loading results
        count = self.count_records(table.name)
        self.logger.success(f"Loaded {count} validated locations into Bronze layer")
        
        return table.name
    
    def validate(self, table_name: str) -> bool:
        """Validate loaded location data in Bronze layer schema."""
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
            
            # Validate required Bronze layer fields
            required_fields = ["city", "state", "zip_code"]
            
            for field in required_fields:
                # Check column exists in Bronze schema
                column_exists = any(col["name"] == field for col in info["schema"])
                if not column_exists:
                    self.logger.error(f"Required Bronze layer field {field} not found in table")
                    return False
                
                # Check for nulls in critical fields
                result = self.connection_manager.execute_safe(
                    f"SELECT COUNT(*) FROM {table.qualified_name} WHERE {field} IS NULL"
                )
                
                null_count = result.fetchone()[0] if result else 0
                if null_count > 0:
                    self.logger.warning(f"Found {null_count} null values in {field}")
            
            self.logger.success(f"Bronze layer location data validation passed for {table.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return False
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> Optional[list]:
        """Get sample location data for inspection from Bronze layer schema."""
        table = TableIdentifier(name=table_name)
        
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError(f"Invalid limit: {limit}")
        
        try:
            connection = self.connection_manager.get_connection()
            result = connection.execute(
                f"""
                SELECT 
                    city,
                    county,
                    state,
                    zip_code,
                    neighborhood
                FROM {table.qualified_name}
                LIMIT {limit}
                """
            )
            
            rows = result.fetchall()
            columns = [desc[0] for desc in result.description]
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            self.logger.error(f"Failed to get sample data: {e}")
            return None
    
    def validate_source_data(self, file_path: Path) -> ValidationResult:
        """Validate source location data using Pydantic models."""
        total_records = 0
        valid_records = 0
        errors = []
        
        if not file_path.exists():
            errors.append(f"File not found: {file_path}")
            return ValidationResult(is_valid=False, errors=errors, record_count=0)
                
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                errors.append(f"Expected list in {file_path}, got {type(data)}")
                return ValidationResult(is_valid=False, errors=errors, record_count=0)
            
            total_records = len(data)
            
            for i, record in enumerate(data):
                try:
                    Location(**record)
                    valid_records += 1
                except ValidationError as e:
                    errors.append(f"Validation error in record {i}: {e}")
                    
        except Exception as e:
            errors.append(f"Failed to read {file_path}: {e}")
        
        return ValidationResult(
            is_valid=len(errors) == 0 and valid_records == total_records,
            errors=errors,
            record_count=total_records
        )
    
    def _create_bronze_table_schema(self, table: TableIdentifier) -> None:
        """Create Bronze layer table schema based on Location model."""
        create_query = f"""
        CREATE TABLE {table.qualified_name} (
            city VARCHAR,
            county VARCHAR,
            state VARCHAR,
            zip_code VARCHAR,
            neighborhood VARCHAR
        )
        """
        
        self.connection_manager.execute_safe(create_query)
        self.logger.info(f"Created Bronze layer table schema for {table.name}")
    
    def _insert_location_data(self, table: TableIdentifier, locations: List[Location]) -> None:
        """Insert validated location data into Bronze layer table."""
        if not locations:
            self.logger.warning("No locations to insert")
            return
        
        # Prepare batch insert data
        insert_query = f"""
        INSERT INTO {table.qualified_name} (city, county, state, zip_code, neighborhood)
        VALUES (?, ?, ?, ?, ?)
        """
        
        # Convert Location objects to tuple data for insertion
        batch_data = []
        for loc in locations:
            batch_data.append((
                loc.city, loc.county, loc.state, loc.zip_code, loc.neighborhood
            ))
        
        # Execute batch insert
        connection = self.connection_manager.get_connection()
        connection.executemany(insert_query, batch_data)
        
        self.logger.info(f"Inserted {len(locations)} validated locations into Bronze layer")