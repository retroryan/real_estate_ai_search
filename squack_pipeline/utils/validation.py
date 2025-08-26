"""Data validation utilities for the pipeline."""

from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ValidationError

from squack_pipeline.utils.logging import PipelineLogger


logger = PipelineLogger.get_logger(__name__)


class ValidationResult:
    """Result of a validation operation."""
    
    def __init__(self):
        """Initialize validation result."""
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.records_validated = 0
        self.records_failed = 0
    
    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        self.is_valid = False
        self.records_failed += 1
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)
    
    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result into this one."""
        self.is_valid = self.is_valid and other.is_valid
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.records_validated += other.records_validated
        self.records_failed += other.records_failed
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.records_validated == 0:
            return 0.0
        return (self.records_validated - self.records_failed) / self.records_validated


def validate_pydantic_model(
    data: Dict[str, Any],
    model_class: Type[BaseModel],
    strict: bool = True
) -> tuple[Optional[BaseModel], Optional[ValidationError]]:
    """Validate data against a Pydantic model."""
    try:
        if strict:
            model = model_class.model_validate(data)
        else:
            model = model_class.model_validate(data, strict=False)
        return model, None
    except ValidationError as e:
        return None, e


def validate_batch(
    records: List[Dict[str, Any]],
    model_class: Type[BaseModel],
    fail_fast: bool = False
) -> ValidationResult:
    """Validate a batch of records."""
    result = ValidationResult()
    
    for i, record in enumerate(records):
        result.records_validated += 1
        
        model, error = validate_pydantic_model(record, model_class)
        
        if error:
            error_msg = f"Record {i}: {error}"
            result.add_error(error_msg)
            logger.error(f"Validation failed for record {i}", error=str(error))
            
            if fail_fast:
                break
        else:
            logger.debug(f"Record {i} validated successfully")
    
    return result


def validate_schema_compatibility(
    source_schema: Dict[str, str],
    target_schema: Dict[str, str]
) -> ValidationResult:
    """Validate schema compatibility between source and target."""
    result = ValidationResult()
    
    # Check for missing columns
    missing_columns = set(target_schema.keys()) - set(source_schema.keys())
    if missing_columns:
        result.add_error(f"Missing required columns: {missing_columns}")
    
    # Check for type mismatches
    for column, expected_type in target_schema.items():
        if column in source_schema:
            actual_type = source_schema[column]
            if actual_type != expected_type:
                result.add_warning(
                    f"Type mismatch for column {column}: "
                    f"expected {expected_type}, got {actual_type}"
                )
    
    # Check for extra columns (informational)
    extra_columns = set(source_schema.keys()) - set(target_schema.keys())
    if extra_columns:
        logger.info(f"Extra columns will be ignored: {extra_columns}")
    
    return result


def validate_data_completeness(
    data: List[Dict[str, Any]],
    required_fields: List[str],
    min_completeness: float = 0.9
) -> ValidationResult:
    """Validate data completeness."""
    result = ValidationResult()
    
    if not data:
        result.add_error("No data to validate")
        return result
    
    total_fields = len(data) * len(required_fields)
    missing_count = 0
    
    for record in data:
        for field in required_fields:
            if field not in record or record[field] is None or record[field] == "":
                missing_count += 1
    
    completeness = 1 - (missing_count / total_fields) if total_fields > 0 else 0
    
    if completeness < min_completeness:
        result.add_error(
            f"Data completeness {completeness:.2%} is below threshold {min_completeness:.2%}"
        )
    else:
        logger.info(f"Data completeness: {completeness:.2%}")
    
    result.records_validated = len(data)
    return result


def validate_numeric_ranges(
    data: List[Dict[str, Any]],
    field: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> ValidationResult:
    """Validate numeric values are within expected ranges."""
    result = ValidationResult()
    
    for i, record in enumerate(data):
        if field not in record:
            continue
        
        value = record[field]
        if value is None:
            continue
        
        try:
            numeric_value = float(value)
            
            if min_value is not None and numeric_value < min_value:
                result.add_warning(
                    f"Record {i}: {field}={numeric_value} is below minimum {min_value}"
                )
            
            if max_value is not None and numeric_value > max_value:
                result.add_warning(
                    f"Record {i}: {field}={numeric_value} is above maximum {max_value}"
                )
        
        except (TypeError, ValueError):
            result.add_error(f"Record {i}: {field}={value} is not a valid number")
    
    result.records_validated = len(data)
    return result


def validate_unique_constraints(
    data: List[Dict[str, Any]],
    unique_fields: List[str]
) -> ValidationResult:
    """Validate unique constraints on specified fields."""
    result = ValidationResult()
    seen_values = {field: set() for field in unique_fields}
    
    for i, record in enumerate(data):
        for field in unique_fields:
            if field in record:
                value = record[field]
                if value in seen_values[field]:
                    result.add_error(
                        f"Duplicate value for {field}: {value} at record {i}"
                    )
                else:
                    seen_values[field].add(value)
    
    result.records_validated = len(data)
    return result