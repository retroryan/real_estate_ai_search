"""
Pydantic models for statistics and collection information.

Clean, type-safe models for system statistics and performance metrics.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from property_finder_models import EntityType, EmbeddingProvider
from .enums import ChunkingMethod


class CollectionInfo(BaseModel):
    """
    Information about a specific ChromaDB collection.
    
    Provides type-safe structure for collection metadata and statistics.
    """
    
    collection_name: str = Field(description="Name of the collection")
    entity_type: EntityType = Field(description="Type of entities in collection")
    model: str = Field(description="Embedding model identifier")
    count: int = Field(ge=0, description="Number of embeddings in collection")
    exists: bool = Field(description="Whether collection exists")
    
    # Optional metadata
    created_at: Optional[datetime] = Field(None, description="Collection creation time")
    version: Optional[str] = Field(None, description="Collection version")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PipelineStatistics(BaseModel):
    """
    Statistics from embedding pipeline processing.
    
    Comprehensive metrics about processing performance and results.
    """
    
    # Processing counts
    documents_processed: int = Field(ge=0, description="Total documents processed")
    chunks_created: int = Field(ge=0, description="Total chunks generated")
    embeddings_generated: int = Field(ge=0, description="Total embeddings created")
    errors: int = Field(ge=0, description="Total processing errors")
    
    # Model and configuration info
    model_identifier: str = Field(description="Embedding model used")
    chunking_method: str = Field(description="Chunking strategy used")
    batch_size: int = Field(ge=1, description="Processing batch size")
    
    # Performance metrics
    processor_stats: Optional[Dict[str, Any]] = Field(None, description="Batch processor statistics")
    
    # Derived metrics
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total_attempts = self.embeddings_generated + self.errors
        if total_attempts == 0:
            return 0.0
        return (self.embeddings_generated / total_attempts) * 100
    
    @property
    def chunks_per_document(self) -> float:
        """Calculate average chunks per document."""
        if self.documents_processed == 0:
            return 0.0
        return self.chunks_created / self.documents_processed
    
    def get_summary(self) -> Dict[str, Any]:
        """Get processing summary as dictionary."""
        return {
            "documents_processed": self.documents_processed,
            "chunks_created": self.chunks_created,
            "embeddings_generated": self.embeddings_generated,
            "errors": self.errors,
            "success_rate": f"{self.success_rate:.1f}%",
            "chunks_per_document": f"{self.chunks_per_document:.1f}",
            "model_identifier": self.model_identifier,
            "chunking_method": self.chunking_method
        }


class BatchProcessorStatistics(BaseModel):
    """
    Statistics from batch processing operations.
    
    Performance metrics for batch embedding generation.
    """
    
    total_processed: int = Field(ge=0, description="Total items processed")
    total_failed: int = Field(ge=0, description="Total items that failed")
    success_rate: float = Field(ge=0.0, le=1.0, description="Success rate (0.0-1.0)")
    timestamp: datetime = Field(description="Statistics generation timestamp")
    
    # Processing performance
    processing_time_seconds: Optional[float] = Field(None, ge=0.0, description="Total processing time")
    items_per_second: Optional[float] = Field(None, ge=0.0, description="Processing rate")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @property
    def success_rate_percentage(self) -> float:
        """Get success rate as percentage."""
        return self.success_rate * 100


class SystemStatistics(BaseModel):
    """
    Overall system statistics and health metrics.
    
    High-level view of the embedding system performance.
    """
    
    # Configuration info
    embedding_provider: EmbeddingProvider = Field(description="Active embedding provider")
    chunking_method: ChunkingMethod = Field(description="Active chunking method")
    
    # Storage info
    storage_path: str = Field(description="ChromaDB storage path")
    
    # Processing totals (across all collections/sessions)
    total_collections: Optional[int] = Field(None, ge=0, description="Total number of collections")
    total_embeddings: Optional[int] = Field(None, ge=0, description="Total embeddings across all collections")
    
    # Timestamps
    generated_at: datetime = Field(default_factory=datetime.now, description="Statistics generation time")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }