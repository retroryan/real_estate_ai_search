"""
Core base models and utilities for Property Finder.

Provides foundational classes used across all modules.
"""

from datetime import datetime
from typing import Optional, Any, Dict
from uuid import uuid4
import uuid

from pydantic import BaseModel, Field, ConfigDict


class BaseEnrichedModel(BaseModel):
    """
    Base model for all enriched data models.
    
    Provides common configuration and fields used across enriched entities.
    """
    
    model_config = ConfigDict(
        # Use enum values instead of names for serialization
        use_enum_values=True,
        # Validate field values on assignment
        validate_assignment=True,
        # Allow population by field name
        populate_by_name=True,
        # Include all fields in serialization, even None values
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


class BaseMetadata(BaseModel):
    """
    Base metadata for all embeddings with correlation identifiers.
    
    Contains the minimal set of fields required for every embedding
    to enable correlation with source data and traceability.
    """
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    # Primary Identifiers
    embedding_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this embedding"
    )
    
    # Source Tracking
    source_file: str = Field(description="Path to source file or database")
    source_collection: str = Field(description="ChromaDB collection name")
    source_timestamp: datetime = Field(description="When source data was last modified")
    
    # Embedding Context
    embedding_model: str = Field(description="Model name used for embedding")
    embedding_dimension: int = Field(description="Dimension of embedding vector")
    embedding_version: str = Field(default="1.0", description="Version of embedding pipeline")
    text_hash: str = Field(description="SHA256 hash of text used for embedding")
    generation_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When embedding was created"
    )
    
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override to ensure ChromaDB-compatible serialization."""
        # Set exclude_none=True by default for ChromaDB compatibility
        if 'exclude_none' not in kwargs:
            kwargs['exclude_none'] = True
        
        data = super().model_dump(**kwargs)
        
        # Clean data for ChromaDB compatibility
        cleaned = {}
        for key, value in data.items():
            if value is None:
                continue  # Skip None values
            elif isinstance(value, datetime):
                cleaned[key] = value.isoformat()
            elif isinstance(value, (str, int, float, bool)):
                cleaned[key] = value
            elif isinstance(value, dict):
                # Flatten nested dicts or convert to string
                cleaned[key] = str(value)
            elif isinstance(value, list):
                # Convert lists to comma-separated strings
                cleaned[key] = ','.join(str(v) for v in value)
            elif isinstance(value, tuple):
                # Convert tuples to comma-separated strings
                cleaned[key] = ','.join(str(v) for v in value)
            else:
                # Convert everything else to string
                cleaned[key] = str(value)
        
        return cleaned


def generate_uuid() -> str:
    """
    Generate a UUID for correlation purposes.
    
    Returns:
        A string UUID
    """
    return str(uuid.uuid4())