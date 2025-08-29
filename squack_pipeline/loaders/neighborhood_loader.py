"""Neighborhood data loader using DuckDB best practices for nested data."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import json

from pydantic import ValidationError

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.loaders.base import BaseLoader
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.models.duckdb_models import TableIdentifier
from squack_pipeline.models.data_models import Neighborhood, DataLoadingMetrics, ValidationResult
from squack_pipeline.utils.logging import log_execution_time


class NeighborhoodLoader(BaseLoader):
    """Loader for neighborhood JSON data preserving nested structures."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize neighborhood loader."""
        super().__init__(settings)
        self.connection_manager = DuckDBConnectionManager()
    
    def get_schema(self) -> Dict[str, str]:
        """Get expected neighborhood data schema with nested STRUCT types."""
        return {
            "neighborhood_id": "VARCHAR",
            "name": "VARCHAR",
            "city": "VARCHAR",
            "county": "VARCHAR",
            "state": "VARCHAR",
            "coordinates": "STRUCT(latitude DOUBLE, longitude DOUBLE)",
            "characteristics": "STRUCT(walkability_score INTEGER, transit_score INTEGER, school_rating INTEGER, safety_rating INTEGER, nightlife_score INTEGER, family_friendly_score INTEGER)",
            "demographics": "STRUCT(primary_age_group VARCHAR, vibe VARCHAR, population INTEGER, median_household_income INTEGER)",
            "description": "VARCHAR",
            "amenities": "VARCHAR[]",
            "lifestyle_tags": "VARCHAR[]",
            "median_home_price": "INTEGER",
            "price_trend": "VARCHAR",
            "wikipedia_correlations": "JSON"
        }
    
    @log_execution_time
    def load(self, table_name: str, source: Optional[Path] = None, sample_size: Optional[int] = None) -> str:
        """Load neighborhood data from JSON files into DuckDB preserving nested structures using STRUCT types."""
        # Use configured neighborhood files
        neighborhood_files = self.settings.data_sources.neighborhoods_files
        
        # Validate files exist
        for file_path in neighborhood_files:
            if not file_path.exists():
                raise FileNotFoundError(f"Neighborhood data file not found: {file_path}")
        
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
        
        # Load data using DuckDB's read_json with auto_detect for STRUCT types
        self.logger.info("Loading neighborhood data with nested structures preserved...")
        
        for idx, file_path in enumerate(neighborhood_files):
            # Validate data with Pydantic first
            validation_result = self._validate_json_file(file_path, sample_size)
            if not validation_result.is_valid:
                self.logger.warning(f"Validation issues in {file_path}: {validation_result.errors}")
            
            # Use DuckDB's read_json to automatically create STRUCT types
            if idx == 0:
                # Create table from first file
                if sample_size:
                    query = f"""
                    CREATE TABLE {table.qualified_name} AS 
                    SELECT * FROM read_json('{file_path}', 
                        auto_detect=true,
                        format='array',
                        maximum_object_size=20000000
                    ) LIMIT {sample_size}
                    """
                else:
                    query = f"""
                    CREATE TABLE {table.qualified_name} AS 
                    SELECT * FROM read_json('{file_path}', 
                        auto_detect=true,
                        format='array',
                        maximum_object_size=20000000
                    )
                    """
            else:
                # Insert into existing table
                if sample_size:
                    remaining = sample_size - self.count_records(table.name)
                    if remaining <= 0:
                        break
                    query = f"""
                    INSERT INTO {table.qualified_name}
                    SELECT * FROM read_json('{file_path}', 
                        auto_detect=true,
                        format='array',
                        maximum_object_size=20000000
                    ) LIMIT {remaining}
                    """
                else:
                    query = f"""
                    INSERT INTO {table.qualified_name}
                    SELECT * FROM read_json('{file_path}', 
                        auto_detect=true,
                        format='array',
                        maximum_object_size=20000000
                    )
                    """
            
            self.connection_manager.execute_safe(query)
            
            # Check if we've reached sample size
            if sample_size and self.count_records(table.name) >= sample_size:
                break
        
        # Log loading results
        count = self.count_records(table.name)
        self.logger.success(f"Loaded {count} neighborhoods with nested structures preserved into Bronze layer")
        
        return table.name
    
    def validate(self, table_name: str) -> bool:
        """Validate loaded neighborhood data with nested structure."""
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
            
            # Validate required nested fields using dot notation
            required_fields = [
                "neighborhood_id",
                "name",
                "city",
                "state",
                "coordinates.latitude",
                "coordinates.longitude",
                "characteristics.walkability_score",
                "characteristics.school_rating"
            ]
            
            for field in required_fields:
                # Check for nulls in critical fields
                result = self.connection_manager.execute_safe(
                    f"SELECT COUNT(*) FROM {table.qualified_name} WHERE {field} IS NULL"
                )
                
                null_count = result.fetchone()[0] if result else 0
                if null_count > 0:
                    self.logger.warning(f"Found {null_count} null values in {field}")
            
            # Validate coordinate ranges using nested field access
            result = self.connection_manager.execute_safe(
                f"""
                SELECT COUNT(*) FROM {table.qualified_name} 
                WHERE coordinates.latitude < -90 OR coordinates.latitude > 90 
                   OR coordinates.longitude < -180 OR coordinates.longitude > 180
                """
            )
            
            invalid_coords = result.fetchone()[0] if result else 0
            if invalid_coords > 0:
                self.logger.error(f"Found {invalid_coords} neighborhoods with invalid coordinates")
                return False
            
            # Validate score ranges using nested field access
            result = self.connection_manager.execute_safe(
                f"""
                SELECT COUNT(*) FROM {table.qualified_name} 
                WHERE characteristics.walkability_score < 0 OR characteristics.walkability_score > 100 
                   OR characteristics.school_rating < 0 OR characteristics.school_rating > 10
                """
            )
            
            invalid_scores = result.fetchone()[0] if result else 0
            if invalid_scores > 0:
                self.logger.error(f"Found {invalid_scores} neighborhoods with invalid scores")
                return False
            
            self.logger.success(f"Bronze layer neighborhood data validation passed for {table.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return False
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> Optional[list]:
        """Get sample neighborhood data with nested structures."""
        table = TableIdentifier(name=table_name)
        
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError(f"Invalid limit: {limit}")
        
        try:
            connection = self.connection_manager.get_connection()
            result = connection.execute(
                f"""
                SELECT 
                    neighborhood_id,
                    name,
                    city,
                    state,
                    characteristics.walkability_score as walkability_score,
                    characteristics.school_rating as school_rating,
                    demographics.population as population,
                    description,
                    coordinates,
                    characteristics,
                    demographics
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
    
    def _validate_json_file(self, file_path: Path, sample_size: Optional[int] = None) -> ValidationResult:
        """Validate JSON file using Pydantic models."""
        errors = []
        valid_records = 0
        total_records = 0
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                errors.append(f"Expected list in {file_path}, got {type(data)}")
                return ValidationResult(is_valid=False, errors=errors, record_count=0)
            
            # Limit validation to sample size if specified
            data_to_validate = data[:sample_size] if sample_size else data
            total_records = len(data_to_validate)
            
            for i, record in enumerate(data_to_validate):
                try:
                    Neighborhood(**record)
                    valid_records += 1
                except ValidationError as e:
                    # Just log first few errors to avoid spam
                    if len(errors) < 5:
                        errors.append(f"Validation error in record {i}: {str(e)[:100]}")
                    
        except Exception as e:
            errors.append(f"Failed to read {file_path}: {e}")
            return ValidationResult(is_valid=False, errors=errors, record_count=0)
        
        return ValidationResult(
            is_valid=(valid_records == total_records),
            errors=errors,
            record_count=total_records
        )
    
    def validate_source_data(self, file_paths: List[Path]) -> ValidationResult:
        """Validate source neighborhood data using Pydantic models."""
        total_records = 0
        valid_records = 0
        all_errors = []
        
        for file_path in file_paths:
            result = self._validate_json_file(file_path)
            total_records += result.record_count
            if result.is_valid:
                valid_records += result.record_count
            all_errors.extend(result.errors)
        
        return ValidationResult(
            is_valid=(valid_records == total_records and len(all_errors) == 0),
            errors=all_errors,
            record_count=total_records
        )