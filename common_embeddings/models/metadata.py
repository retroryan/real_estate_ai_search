"""
Metadata models for embeddings tracking.

These models extend the base metadata from common with
embedding-specific fields for correlation and tracking.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import uuid4

from common.property_finder_models import (
    BaseMetadata,
    EntityType,
    SourceType,
    EmbeddingProvider,
)
from .enums import (
    ChunkingMethod,
    PreprocessingStep,
    AugmentationType,
)


class PropertyMetadata(BaseMetadata):
    """
    Metadata for property embeddings.
    
    Extends BaseMetadata with property-specific fields.
    """
    
    listing_id: str = Field(description="Property listing identifier")
    property_type: Optional[str] = Field(None, description="Type of property")
    price: Optional[float] = Field(None, description="Property price")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NeighborhoodMetadata(BaseMetadata):
    """
    Metadata for neighborhood embeddings.
    
    Extends BaseMetadata with neighborhood-specific fields.
    """
    
    neighborhood_id: str = Field(description="Neighborhood identifier")
    neighborhood_name: str = Field(description="Name of the neighborhood")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State name")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WikipediaMetadata(BaseMetadata):
    """
    Metadata for Wikipedia article embeddings.
    
    Extends BaseMetadata with Wikipedia-specific fields.
    """
    
    page_id: int = Field(description="Wikipedia page ID")
    title: str = Field(description="Article title")
    url: Optional[str] = Field(None, description="Wikipedia URL")
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0,
                                             description="Relevance score for location articles")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChunkMetadata(BaseModel):
    """
    Metadata for text chunks within documents.
    
    Tracks how documents were split into chunks for embedding.
    """
    
    chunk_index: int = Field(description="Index of this chunk in the document")
    chunk_total: int = Field(description="Total number of chunks from this document")
    start_position: int = Field(description="Starting character position in original text")
    end_position: int = Field(description="Ending character position in original text")
    token_count: Optional[int] = Field(None, description="Number of tokens in chunk")
    overlap_previous: Optional[int] = Field(None, description="Characters overlapping with previous chunk")
    overlap_next: Optional[int] = Field(None, description="Characters overlapping with next chunk")
    
    @field_validator('chunk_index')
    @classmethod
    def validate_chunk_index(cls, v: int, info) -> int:
        """Ensure chunk_index is valid."""
        if 'chunk_total' in info.data and v >= info.data['chunk_total']:
            raise ValueError(f"chunk_index {v} must be less than chunk_total {info.data['chunk_total']}")
        return v


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


class ProcessingMetadata(BaseModel):
    """
    Details about text processing applied before embedding.
    
    Helps understand how the text was prepared for embedding generation.
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
    original_text_length: int = Field(ge=0, description="Length before processing")
    processed_text_length: int = Field(ge=0, description="Length after processing")