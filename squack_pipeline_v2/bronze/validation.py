"""Bronze layer validation rules."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import PipelineLogger


class BronzeValidationResult(BaseModel):
    """Result of Bronze layer validation."""
    
    model_config = ConfigDict(frozen=True)
    
    table_name: str = Field(description="Table validated")
    entity_type: str = Field(description="Entity type")
    
    is_valid: bool = Field(description="Overall validation status")
    record_count: int = Field(ge=0, description="Number of records")
    
    schema_valid: bool = Field(description="Schema validation status")
    nulls_valid: bool = Field(description="Null check status")
    duplicates_valid: bool = Field(description="Duplicate check status")
    data_types_valid: bool = Field(description="Data type validation status")
    
    error_messages: list[str] = Field(default_factory=list, description="Validation errors")
    warning_messages: list[str] = Field(default_factory=list, description="Validation warnings")


class BronzeValidator:
    """Validator for Bronze layer data."""
    
    def __init__(self, connection_manager: DuckDBConnectionManager):
        """Initialize validator.
        
        Args:
            connection_manager: DuckDB connection manager
        """
        self.connection_manager = connection_manager
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
    
    def validate_property_bronze(self, table_name: str) -> BronzeValidationResult:
        """Validate Bronze property data.
        
        Args:
            table_name: Table to validate
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        # Check record count
        record_count = self.connection_manager.count_records(table_name)
        if record_count == 0:
            errors.append("No records found")
        
        # Check schema
        schema = self.connection_manager.get_table_schema(table_name)
        required_fields = [
            "listing_id", "listing_price", "bedrooms", "bathrooms",
            "square_feet", "address", "city", "state", "zip_code",
            "latitude", "longitude"
        ]
        
        schema_valid = True
        for field in required_fields:
            if field not in schema:
                errors.append(f"Missing required field: {field}")
                schema_valid = False
        
        # Check for nulls in critical fields
        nulls_valid = True
        critical_fields = ["listing_id", "listing_price", "square_feet"]
        for field in critical_fields:
            if field in schema:
                null_count = self._count_nulls(table_name, field)
                if null_count > 0:
                    warnings.append(f"{null_count} nulls in {field}")
                    if field == "listing_id":
                        nulls_valid = False
                        errors.append(f"NULL values in primary key field {field}")
        
        # Check for duplicates
        duplicates_valid = True
        if "listing_id" in schema:
            duplicate_count = self._count_duplicates(table_name, "listing_id")
            if duplicate_count > 0:
                errors.append(f"{duplicate_count} duplicate listing_ids")
                duplicates_valid = False
        
        # Check data types and ranges
        data_types_valid = self._validate_property_data_types(table_name)
        
        return BronzeValidationResult(
            table_name=table_name,
            entity_type="property",
            is_valid=len(errors) == 0,
            record_count=record_count,
            schema_valid=schema_valid,
            nulls_valid=nulls_valid,
            duplicates_valid=duplicates_valid,
            data_types_valid=data_types_valid,
            error_messages=errors,
            warning_messages=warnings
        )
    
    def validate_neighborhood_bronze(self, table_name: str) -> BronzeValidationResult:
        """Validate Bronze neighborhood data.
        
        Args:
            table_name: Table to validate
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        record_count = self.connection_manager.count_records(table_name)
        if record_count == 0:
            errors.append("No records found")
        
        # Check schema
        schema = self.connection_manager.get_table_schema(table_name)
        required_fields = ["neighborhood_id", "name", "city", "state"]
        
        schema_valid = True
        for field in required_fields:
            if field not in schema:
                errors.append(f"Missing required field: {field}")
                schema_valid = False
        
        # Check nulls
        nulls_valid = True
        if "neighborhood_id" in schema:
            null_count = self._count_nulls(table_name, "neighborhood_id")
            if null_count > 0:
                errors.append(f"NULL values in neighborhood_id")
                nulls_valid = False
        
        # Check duplicates
        duplicates_valid = True
        if "neighborhood_id" in schema:
            duplicate_count = self._count_duplicates(table_name, "neighborhood_id")
            if duplicate_count > 0:
                errors.append(f"{duplicate_count} duplicate neighborhood_ids")
                duplicates_valid = False
        
        data_types_valid = self._validate_neighborhood_data_types(table_name)
        
        return BronzeValidationResult(
            table_name=table_name,
            entity_type="neighborhood",
            is_valid=len(errors) == 0,
            record_count=record_count,
            schema_valid=schema_valid,
            nulls_valid=nulls_valid,
            duplicates_valid=duplicates_valid,
            data_types_valid=data_types_valid,
            error_messages=errors,
            warning_messages=warnings
        )
    
    def validate_wikipedia_bronze(self, table_name: str) -> BronzeValidationResult:
        """Validate Bronze Wikipedia data.
        
        Args:
            table_name: Table to validate
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        record_count = self.connection_manager.count_records(table_name)
        if record_count == 0:
            errors.append("No records found")
        
        # Check schema
        schema = self.connection_manager.get_table_schema(table_name)
        required_fields = ["page_id", "title", "summary", "content", "url"]
        
        schema_valid = True
        for field in required_fields:
            if field not in schema:
                errors.append(f"Missing required field: {field}")
                schema_valid = False
        
        # Check nulls
        nulls_valid = True
        if "page_id" in schema:
            null_count = self._count_nulls(table_name, "page_id")
            if null_count > 0:
                errors.append(f"NULL values in page_id")
                nulls_valid = False
        
        # Check duplicates
        duplicates_valid = True
        if "page_id" in schema:
            duplicate_count = self._count_duplicates(table_name, "page_id")
            if duplicate_count > 0:
                errors.append(f"{duplicate_count} duplicate page_ids")
                duplicates_valid = False
        
        # Check content length
        data_types_valid = True
        min_length = self._get_min_field_length(table_name, "content")
        if min_length < 100:
            warnings.append(f"Very short content found (min: {min_length} chars)")
        
        return BronzeValidationResult(
            table_name=table_name,
            entity_type="wikipedia",
            is_valid=len(errors) == 0,
            record_count=record_count,
            schema_valid=schema_valid,
            nulls_valid=nulls_valid,
            duplicates_valid=duplicates_valid,
            data_types_valid=data_types_valid,
            error_messages=errors,
            warning_messages=warnings
        )
    
    def _count_nulls(self, table_name: str, field: str) -> int:
        """Count NULL values in a field."""
        safe_table = DuckDBConnectionManager.safe_identifier(table_name)
        safe_field = DuckDBConnectionManager.safe_identifier(field)
        query = f"SELECT COUNT(*) FROM {safe_table} WHERE {safe_field} IS NULL"
        result = self.connection_manager.execute(query).fetchone()
        return result[0] if result else 0
    
    def _count_duplicates(self, table_name: str, field: str) -> int:
        """Count duplicate values in a field."""
        safe_table = DuckDBConnectionManager.safe_identifier(table_name)
        safe_field = DuckDBConnectionManager.safe_identifier(field)
        query = f"""
        SELECT COUNT(*) 
        FROM (
            SELECT {safe_field}, COUNT(*) as cnt
            FROM {safe_table}
            GROUP BY {safe_field}
            HAVING COUNT(*) > 1
        ) t
        """
        result = self.connection_manager.execute(query).fetchone()
        return result[0] if result else 0
    
    def _get_min_field_length(self, table_name: str, field: str) -> int:
        """Get minimum length of a text field."""
        safe_table = DuckDBConnectionManager.safe_identifier(table_name)
        safe_field = DuckDBConnectionManager.safe_identifier(field)
        query = f"SELECT MIN(LENGTH({safe_field})) FROM {safe_table}"
        result = self.connection_manager.execute(query).fetchone()
        return result[0] if result and result[0] else 0
    
    def _validate_property_data_types(self, table_name: str) -> bool:
        """Validate property data types and ranges."""
        try:
            # Check numeric ranges
            safe_table = DuckDBConnectionManager.safe_identifier(table_name)
            range_query = f"""
            SELECT 
                COUNT(*) as invalid_count
            FROM {safe_table}
            WHERE listing_price <= 0
                OR bedrooms < 0
                OR bathrooms < 0
                OR square_feet <= 0
                OR latitude NOT BETWEEN -90 AND 90
                OR longitude NOT BETWEEN -180 AND 180
            """
            result = self.connection_manager.execute(range_query).fetchone()
            
            if result and result[0] > 0:
                self.logger.warning(f"{result[0]} records with invalid data ranges")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error validating data types: {e}")
            return False
    
    def _validate_neighborhood_data_types(self, table_name: str) -> bool:
        """Validate neighborhood data types and ranges."""
        try:
            # Check numeric ranges where fields exist
            schema = self.connection_manager.get_table_schema(table_name)
            
            conditions = []
            if "population" in schema:
                conditions.append("population < 0")
            if "walkability_score" in schema:
                conditions.append("walkability_score NOT BETWEEN 0 AND 100")
            
            if conditions:
                safe_table = DuckDBConnectionManager.safe_identifier(table_name)
                range_query = f"""
                SELECT COUNT(*) as invalid_count
                FROM {safe_table}
                WHERE {' OR '.join(conditions)}
                """
                result = self.connection_manager.execute(range_query).fetchone()
                
                if result and result[0] > 0:
                    self.logger.warning(f"{result[0]} records with invalid data ranges")
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error validating data types: {e}")
            return False