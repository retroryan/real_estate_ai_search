"""Simplified pipeline execution models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ProcessingResult(BaseModel):
    """Result from processing a stage."""
    
    model_config = ConfigDict(frozen=True)
    
    success: bool = Field(description="Whether processing succeeded")
    stage_name: str = Field(description="Stage that was processed")
    entity_type: str = Field(description="Entity type processed")
    
    input_count: int = Field(ge=0, description="Input record count")
    output_count: int = Field(ge=0, description="Output record count")
    
    output_table: Optional[str] = Field(default=None, description="Output table created")
    output_path: Optional[str] = Field(default=None, description="Output file path if applicable")
    
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
    
    duration_seconds: float = Field(ge=0, description="Processing duration")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")