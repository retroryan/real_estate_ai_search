"""Pydantic models for standardized writer interface."""

from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from squack_pipeline.models import EntityType


class WriteRequest(BaseModel):
    """Request for a write operation."""
    
    entity_type: EntityType = Field(description="Type of entity being written")
    table_name: str = Field(description="Source table name in DuckDB")
    record_count: int = Field(ge=0, description="Number of records to write")
    destination_path: Optional[Path] = Field(default=None, description="Output path for file-based writers")
    
    def get_destination_name(self) -> str:
        """Get a name for the destination (file name or index name)."""
        if self.destination_path:
            return self.destination_path.name
        return f"{self.entity_type.value}_{self.table_name}"


class WriteMetrics(BaseModel):
    """Metrics from a write operation."""
    
    records_written: int = Field(ge=0, description="Number of records successfully written")
    records_failed: int = Field(default=0, ge=0, description="Number of records that failed")
    bytes_written: int = Field(default=0, ge=0, description="Total bytes written (for file-based writers)")
    duration_seconds: float = Field(ge=0, description="Time taken for write operation")
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        total = self.records_written + self.records_failed
        if total == 0:
            return 100.0
        return (self.records_written / total) * 100.0
    
    @property
    def throughput_records_per_second(self) -> float:
        """Calculate throughput in records per second."""
        if self.duration_seconds == 0:
            return 0.0
        return self.records_written / self.duration_seconds


class ValidationResult(BaseModel):
    """Result of validating written output."""
    
    is_valid: bool = Field(description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional validation metadata")
    
    def add_error(self, error: str) -> None:
        """Add an error to the validation result."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the validation result."""
        self.warnings.append(warning)


class WriteResponse(BaseModel):
    """Response from a write operation."""
    
    success: bool = Field(description="Whether the write operation succeeded")
    entity_type: EntityType = Field(description="Type of entity written")
    destination: str = Field(description="Where data was written (file path or index name)")
    metrics: WriteMetrics = Field(description="Write operation metrics")
    validation: Optional[ValidationResult] = Field(default=None, description="Validation result if performed")
    error: Optional[str] = Field(default=None, description="Error message if operation failed")
    
    def is_complete_success(self) -> bool:
        """Check if write was completely successful with no failures."""
        return (
            self.success and 
            self.metrics.records_failed == 0 and
            (self.validation.is_valid if self.validation else True)
        )