"""
Metadata models for correlation and tracking.

These models follow the minimalist design philosophy where embeddings store
only essential identifiers needed to locate source data, preventing data
duplication and synchronization issues.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import uuid4

from .enums import (
    EntityType,
    SourceType,
    EmbeddingProvider,
    ChunkingMethod,
    PreprocessingStep,
    AugmentationType,
)


class BaseMetadata(BaseModel):
    """
    Base metadata for all embeddings with correlation identifiers.
    
    This contains the minimal set of fields required for every embedding
    to enable correlation with source data and traceability.
    """
    
    # Primary Identifiers (MANDATORY)
    embedding_id: str = Field(default_factory=lambda: str(uuid4()),
                             description="Unique identifier for this embedding")
    entity_type: EntityType = Field(description="Type of entity this embedding represents")
    
    # Source Tracking (MANDATORY)
    source_type: SourceType = Field(description="Type of data source")
    source_file: str = Field(description="Path to source file or database")
    source_collection: str = Field(description="ChromaDB collection name")
    source_timestamp: datetime = Field(description="When source data was last modified")
    
    # Embedding Context (MANDATORY)
    embedding_model: str = Field(description="Model name used for embedding")
    embedding_provider: EmbeddingProvider = Field(description="Provider used")
    embedding_dimension: int = Field(description="Dimension of embedding vector")
    embedding_version: str = Field(default="1.0", description="Version of embedding pipeline")
    text_hash: str = Field(description="SHA256 hash of text used for embedding")
    generation_timestamp: datetime = Field(default_factory=datetime.utcnow,
                                          description="When embedding was created")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def model_dump(self, **kwargs) -> dict:
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


class ChunkMetadata(BaseModel):
    """
    Metadata for multi-chunk documents.
    
    Required when a document is split into multiple embeddings.
    """
    
    chunk_index: int = Field(ge=0, description="Zero-based chunk position")
    chunk_total: int = Field(ge=1, description="Total chunks from source")
    parent_id: str = Field(description="Primary ID of parent document")
    chunk_boundaries: Optional[tuple[int, int]] = Field(
        default=None,
        description="Character positions (start, end) in original text"
    )
    
    @validator('chunk_index')
    def validate_chunk_index(cls, v, values):
        """Ensure chunk_index is less than chunk_total."""
        if 'chunk_total' in values and v >= values['chunk_total']:
            raise ValueError(f"chunk_index {v} must be less than chunk_total {values['chunk_total']}")
        return v


class PropertyMetadata(BaseMetadata):
    """
    Minimal metadata for property embeddings.
    
    Only stores identifiers needed for correlation with source property data.
    """
    
    listing_id: str = Field(description="Primary identifier for property")
    source_file_index: Optional[int] = Field(
        default=None,
        description="Index position in source JSON array"
    )
    
    def __init__(self, **data):
        """Ensure entity_type is set correctly."""
        data['entity_type'] = EntityType.PROPERTY
        super().__init__(**data)


class NeighborhoodMetadata(BaseMetadata):
    """
    Minimal metadata for neighborhood embeddings.
    
    Only stores identifiers needed for correlation with source neighborhood data.
    """
    
    neighborhood_id: str = Field(description="Primary identifier for neighborhood")
    neighborhood_name: str = Field(description="Name as it appears in source")
    source_file_index: Optional[int] = Field(
        default=None,
        description="Index position in source JSON array"
    )
    
    def __init__(self, **data):
        """Ensure entity_type is set correctly."""
        data['entity_type'] = EntityType.NEIGHBORHOOD
        super().__init__(**data)


class WikipediaMetadata(BaseMetadata):
    """
    Minimal metadata for Wikipedia article embeddings.
    
    Only stores identifiers needed for correlation with SQLite database.
    """
    
    page_id: int = Field(description="Wikipedia page ID from database")
    article_id: Optional[int] = Field(
        default=None,
        description="Database row ID for direct lookup"
    )
    has_summary: bool = Field(
        default=False,
        description="Whether page_summaries table has entry"
    )
    
    # Multi-chunk support (Wikipedia articles are often chunked)
    chunk_metadata: Optional[ChunkMetadata] = None
    
    def __init__(self, **data):
        """Ensure entity_type is set correctly."""
        if 'has_summary' in data and data['has_summary']:
            data['entity_type'] = EntityType.WIKIPEDIA_SUMMARY
        else:
            data['entity_type'] = EntityType.WIKIPEDIA_ARTICLE
        super().__init__(**data)


class EmbeddingContextMetadata(BaseModel):
    """
    Additional context about how the embedding was generated.
    
    This is stored separately and can be attached to any entity metadata.
    """
    
    embedding_model: str
    embedding_provider: EmbeddingProvider
    embedding_dimension: int
    embedding_version: str = "1.0"
    text_hash: str
    generation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProcessingMetadata(BaseModel):
    """
    Details about text processing applied before embedding.
    
    This helps understand how the text was prepared for embedding generation.
    """
    
    chunking_method: ChunkingMethod
    chunk_size: Optional[int] = Field(None, ge=1, description="Max chunk size")
    chunk_overlap: Optional[int] = Field(None, ge=0, description="Overlap size")
    text_preprocessing: List[PreprocessingStep] = Field(
        default_factory=list,
        description="Preprocessing steps applied"
    )
    augmentation_type: AugmentationType = Field(
        default=AugmentationType.NONE,
        description="Type of augmentation applied"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True