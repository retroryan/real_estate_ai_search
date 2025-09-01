"""Bronze layer metadata models using Pydantic."""

from pydantic import BaseModel, Field, ConfigDict


class BronzeMetadata(BaseModel):
    """Metadata for Bronze layer ingestion results."""
    
    model_config = ConfigDict(frozen=True)
    
    table_name: str = Field(description="Name of the Bronze table created")
    source_path: str = Field(description="Path to source data")
    records_loaded: int = Field(ge=0, description="Number of records loaded")
    sample_size: int = Field(default=0, ge=0, description="Sample size limit (0 means no limit)")