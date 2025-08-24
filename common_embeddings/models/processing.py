"""
Pydantic models for processing pipeline data structures.

Clean, type-safe models for metadata combination and processing results.
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from common.property_finder_models import EntityType, SourceType, BaseMetadata
from .enums import ChunkingMethod


class ChunkData(BaseModel):
    """
    Simple model for chunk data from the chunking process.
    All fields are flat for direct use.
    """
    text: str = Field(description="The chunk text content")
    chunk_index: int = Field(0, description="Position of chunk in document")
    chunk_total: int = Field(1, description="Total chunks in document")
    text_hash: str = Field(description="Hash of chunk text")
    chunk_method: Optional[str] = Field(None, description="Chunking method used")
    parent_hash: Optional[str] = Field(None, description="Hash of parent document")
    start_position: Optional[int] = Field(None, description="Start position in original text")
    end_position: Optional[int] = Field(None, description="End position in original text")


class ProcessingChunkMetadata(BaseModel):
    """
    Metadata for a processed chunk with combined document and chunk information.
    
    This combines the original document metadata with chunk-specific metadata
    from the chunking process in a type-safe way.
    """
    
    # Document-level metadata (from original LlamaIndex Document)
    source_doc_id: str = Field(description="Unique identifier for source document")
    
    # Chunk-level metadata (from chunking process)
    chunk_index: int = Field(ge=0, description="Index of chunk within document")
    chunk_total: int = Field(ge=1, description="Total chunks in document")
    text_hash: str = Field(description="Hash of chunk text content")
    chunk_method: Optional[str] = Field(None, description="Chunking method used")
    
    # Optional parent document info (for multi-chunk documents)
    parent_hash: Optional[str] = Field(None, description="Hash of parent document")
    
    # Entity-specific metadata (preserved from original document)
    listing_id: Optional[str] = Field(None, description="Property listing ID")
    property_type: Optional[str] = Field(None, description="Type of property")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    city: Optional[str] = Field(None, description="Property city")
    state: Optional[str] = Field(None, description="Property state")
    source_file_index: Optional[int] = Field(None, description="Index in source file")
    
    neighborhood_id: Optional[str] = Field(None, description="Neighborhood identifier")
    neighborhood_name: Optional[str] = Field(None, description="Neighborhood name")
    
    page_id: Optional[int] = Field(None, description="Wikipedia page ID")
    article_id: Optional[int] = Field(None, description="Database article ID for correlation")
    title: Optional[str] = Field(None, description="Wikipedia article title")
    
    # Position information for chunks
    start_position: Optional[int] = Field(None, description="Starting character position in original text")
    end_position: Optional[int] = Field(None, description="Ending character position in original text")
    


class ProcessingResult(BaseModel):
    """
    Result of processing a single chunk through the embedding pipeline.
    
    Contains the generated embedding vector and associated metadata.
    """
    
    embedding: List[float] = Field(description="Generated embedding vector")
    metadata: BaseMetadata = Field(description="Structured metadata for the embedding")
    
    # Processing context
    entity_type: EntityType = Field(description="Type of entity processed")
    source_type: SourceType = Field(description="Type of data source")
    source_file: str = Field(description="Path to source file")
    
    # Processing timestamps
    processed_at: datetime = Field(default_factory=datetime.now, description="Processing timestamp")
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True  # Allow BaseMetadata subclasses
    )


class BatchProcessingResult(BaseModel):
    """
    Result of processing a batch of documents.
    
    Contains summary statistics and individual results.
    """
    
    results: List[ProcessingResult] = Field(description="Individual processing results")
    
    # Summary statistics
    total_documents: int = Field(description="Total documents processed")
    total_chunks: int = Field(description="Total chunks created")
    total_embeddings: int = Field(description="Total embeddings generated") 
    total_errors: int = Field(description="Total processing errors")
    
    # Processing metadata
    entity_type: EntityType = Field(description="Entity type processed")
    chunking_method: ChunkingMethod = Field(description="Chunking method used")
    model_identifier: str = Field(description="Embedding model used")
    
    # Performance metrics
    processing_time_seconds: float = Field(description="Total processing time")
    chunks_per_second: Optional[float] = Field(None, description="Processing rate")
    
    # Timestamps
    started_at: datetime = Field(description="Processing start time")
    completed_at: datetime = Field(default_factory=datetime.now, description="Processing completion time")
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_embeddings == 0:
            return 0.0
        return (self.total_embeddings / (self.total_embeddings + self.total_errors)) * 100
    
    def get_summary(self) -> Dict[str, Any]:
        """Get processing summary as dictionary."""
        return {
            "total_documents": self.total_documents,
            "total_chunks": self.total_chunks,
            "total_embeddings": self.total_embeddings,
            "total_errors": self.total_errors,
            "success_rate": f"{self.success_rate:.1f}%",
            "processing_time": f"{self.processing_time_seconds:.2f}s",
            "chunks_per_second": self.chunks_per_second,
            "entity_type": self.entity_type.value,
            "chunking_method": self.chunking_method.value,
            "model_identifier": self.model_identifier
        }


class DocumentBatch(BaseModel):
    """
    A batch of documents for processing.
    
    Provides structure for batch processing with metadata.
    """
    
    documents: List[Any] = Field(description="LlamaIndex Document objects")  # Using Any since Document is external
    batch_index: int = Field(ge=0, description="Batch index (0-based)")
    total_batches: int = Field(ge=1, description="Total number of batches")
    
    # Processing context
    entity_type: EntityType = Field(description="Entity type for this batch")
    source_type: SourceType = Field(description="Source type for this batch") 
    source_file: str = Field(description="Source file for this batch")
    
    @property
    def batch_size(self) -> int:
        """Get the actual size of this batch."""
        return len(self.documents)
    
    @property
    def is_last_batch(self) -> bool:
        """Check if this is the last batch."""
        return self.batch_index == self.total_batches - 1
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True  # Allow LlamaIndex Document objects