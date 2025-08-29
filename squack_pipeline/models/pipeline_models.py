"""Pipeline processing models using Pydantic for type safety."""

from typing import Optional
from pydantic import BaseModel, Field

from squack_pipeline.models import EntityType, MedallionTier


class ProcessedTable(BaseModel):
    """Result of processing a table through a pipeline tier.
    
    This model represents the output of processing an entity through
    a medallion tier (Bronze, Silver, or Gold).
    """
    
    table_name: str = Field(
        ...,
        description="Name of the DuckDB table created"
    )
    entity_type: EntityType = Field(
        ...,
        description="Type of entity processed"
    )
    tier: MedallionTier = Field(
        ...,
        description="Medallion tier of the processed data"
    )
    record_count: int = Field(
        ...,
        ge=0,
        description="Number of records in the processed table"
    )
    timestamp: int = Field(
        ...,
        description="Unix timestamp when processing occurred"
    )
    
    class Config:
        """Pydantic configuration."""
        frozen = True  # Make instances immutable
        use_enum_values = False  # Keep enums as enums, not strings