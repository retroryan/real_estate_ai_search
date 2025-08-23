"""
Base Pydantic model with common fields and functionality.
"""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, Field, ConfigDict


class BaseEnrichedModel(BaseModel):
    """
    Base model for all enriched data models.
    
    Provides common configuration and fields used across all models.
    """
    
    model_config = ConfigDict(
        # Use enum values instead of names for serialization
        use_enum_values=True,
        # Validate field values on assignment
        validate_assignment=True,
        # Allow population by field name
        populate_by_name=True,
        # Include all fields in serialization, even None values
        # This ensures consistent structure
        exclude_none=False,
        # Allow arbitrary types for complex objects
        arbitrary_types_allowed=True,
    )
    
    # Metadata fields
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when this record was created"
    )
    
    enrichment_version: str = Field(
        default="1.0.0",
        description="Version of the enrichment pipeline"
    )


def generate_uuid() -> str:
    """
    Generate a UUID for correlation purposes.
    
    Returns:
        A string UUID
    """
    return str(uuid.uuid4())