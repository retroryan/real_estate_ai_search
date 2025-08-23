"""
Pydantic models for embedding data.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, field_validator


class EmbeddingData(BaseModel):
    """
    Container for vector embedding data with metadata.
    
    This model holds the actual embedding vector along with metadata
    about how it was generated.
    """
    
    embedding_id: str = Field(..., description="UUID for correlation")
    vector: List[float] = Field(..., description="The embedding vector")
    dimension: int = Field(..., gt=0, description="Dimension of the embedding")
    model_name: str = Field(..., description="Name of the embedding model")
    provider: str = Field(..., description="Embedding provider (e.g., 'ollama', 'openai')")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    @field_validator('vector')
    @classmethod
    def validate_vector(cls, v: List[float], info) -> List[float]:
        """Validate vector has correct dimension."""
        if 'dimension' in info.data and len(v) != info.data['dimension']:
            raise ValueError(f"Vector dimension {len(v)} doesn't match specified dimension {info.data['dimension']}")
        return v
    
    @field_validator('dimension')
    @classmethod
    def validate_dimension(cls, v: int, info) -> int:
        """Validate dimension matches vector length if vector is provided."""
        if 'vector' in info.data and len(info.data['vector']) != v:
            raise ValueError(f"Dimension {v} doesn't match vector length {len(info.data['vector'])}")
        return v


class PropertyEmbedding(BaseModel):
    """
    Dedicated model for property embeddings used in bulk loading.
    
    This model is used when loading embeddings separately from property data.
    """
    
    embedding_id: str = Field(..., description="UUID for this embedding")
    listing_id: str = Field(..., description="Links to EnrichedProperty.listing_id")
    vector: List[float] = Field(..., description="The embedding vector")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="ChromaDB metadata")
    text: str = Field(..., description="Original text used for embedding")
    
    @field_validator('listing_id')
    @classmethod
    def validate_listing_id(cls, v: str) -> str:
        """Ensure listing_id is not empty."""
        if not v or not v.strip():
            raise ValueError("listing_id cannot be empty")
        return v.strip()
    
    @field_validator('vector')
    @classmethod
    def validate_vector_not_empty(cls, v: List[float]) -> List[float]:
        """Ensure vector is not empty."""
        if not v:
            raise ValueError("Embedding vector cannot be empty")
        return v


class WikipediaEmbedding(BaseModel):
    """
    Dedicated model for Wikipedia embeddings used in bulk loading.
    
    Supports multi-chunk documents through chunk indexing.
    """
    
    embedding_id: str = Field(..., description="UUID for this embedding")
    page_id: int = Field(..., gt=0, description="Links to WikipediaArticle.page_id")
    chunk_index: int = Field(0, ge=0, description="Index for multi-chunk documents")
    chunk_total: int = Field(1, gt=0, description="Total chunks for this document")
    vector: List[float] = Field(..., description="The embedding vector")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="ChromaDB metadata")
    text: str = Field(..., description="Original text chunk used for embedding")
    
    @field_validator('chunk_index')
    @classmethod
    def validate_chunk_index(cls, v: int, info) -> int:
        """Validate chunk_index is within valid range."""
        if 'chunk_total' in info.data and v >= info.data['chunk_total']:
            raise ValueError(f"chunk_index {v} must be less than chunk_total {info.data['chunk_total']}")
        return v
    
    @field_validator('vector')
    @classmethod
    def validate_vector_not_empty(cls, v: List[float]) -> List[float]:
        """Ensure vector is not empty."""
        if not v:
            raise ValueError("Embedding vector cannot be empty")
        return v


class NeighborhoodEmbedding(BaseModel):
    """
    Dedicated model for neighborhood embeddings used in bulk loading.
    """
    
    embedding_id: str = Field(..., description="UUID for this embedding")
    neighborhood_id: str = Field(..., description="Links to EnrichedNeighborhood.neighborhood_id")
    neighborhood_name: str = Field(..., description="Neighborhood name for matching")
    vector: List[float] = Field(..., description="The embedding vector")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="ChromaDB metadata")
    text: str = Field(..., description="Original text used for embedding")
    
    @field_validator('neighborhood_name')
    @classmethod
    def validate_neighborhood_name(cls, v: str) -> str:
        """Ensure neighborhood_name is not empty."""
        if not v or not v.strip():
            raise ValueError("neighborhood_name cannot be empty")
        return v.strip()
    
    @field_validator('vector')
    @classmethod
    def validate_vector_not_empty(cls, v: List[float]) -> List[float]:
        """Ensure vector is not empty."""
        if not v:
            raise ValueError("Embedding vector cannot be empty")
        return v