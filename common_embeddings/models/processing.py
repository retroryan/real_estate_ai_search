"""
Pydantic models for processing pipeline data structures.

Clean, type-safe models for metadata combination and processing results.
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field

from property_finder_models import EntityType, SourceType, BaseMetadata
from .enums import ChunkingMethod


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
    
    neighborhood_id: Optional[str] = Field(None, description="Neighborhood identifier")
    neighborhood_name: Optional[str] = Field(None, description="Neighborhood name")
    
    page_id: Optional[int] = Field(None, description="Wikipedia page ID")
    title: Optional[str] = Field(None, description="Wikipedia article title")
    
    # Additional metadata as flexible dict
    extra_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata fields")
    
    @classmethod
    def from_combined_dict(
        cls, 
        document_metadata: Dict[str, Any], 
        chunk_metadata: Dict[str, Any],
        source_doc_id: Optional[str] = None
    ) -> "ChunkMetadata":
        """
        Create ChunkMetadata from combined document and chunk metadata dictionaries.
        
        Args:
            document_metadata: Original document metadata
            chunk_metadata: Chunk-specific metadata from chunking process
            source_doc_id: Optional source document ID override
            
        Returns:
            ChunkMetadata instance with combined data
        """
        # Combine both metadata dicts
        combined = {**document_metadata, **chunk_metadata}
        
        # Generate source_doc_id if not provided
        if source_doc_id:
            combined['source_doc_id'] = source_doc_id
        elif 'id' in document_metadata:
            combined['source_doc_id'] = document_metadata['id']
        elif 'text_hash' in chunk_metadata:
            combined['source_doc_id'] = chunk_metadata['text_hash'][:8]
        else:
            combined['source_doc_id'] = 'unknown'
        
        # Extract known fields
        known_fields = {
            'source_doc_id', 'chunk_index', 'chunk_total', 'text_hash', 
            'chunk_method', 'parent_hash', 'listing_id', 'property_type',
            'bedrooms', 'city', 'state', 'neighborhood_id', 'neighborhood_name',
            'page_id', 'title'
        }
        
        # Separate known fields from extra metadata
        field_data = {}
        extra_data = {}
        
        for key, value in combined.items():
            if key in known_fields:
                field_data[key] = value
            else:
                extra_data[key] = value
        
        # Set extra metadata
        field_data['extra_metadata'] = extra_data
        
        return cls(**field_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for ChromaDB storage.
        
        Returns:
            Dictionary with all fields flattened, excluding None values
        """
        result = {}
        
        # Add main fields
        data = self.model_dump(exclude_none=True, exclude={'extra_metadata'})
        result.update(data)
        
        # Add extra metadata fields
        result.update(self.extra_metadata)
        
        return result


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
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True  # Allow BaseMetadata subclasses


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