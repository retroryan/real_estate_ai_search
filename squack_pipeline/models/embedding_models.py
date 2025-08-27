"""Pydantic models for embedding data structures."""

import json
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class DecimalJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal types."""
    
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class EmbeddingMetadata(BaseModel):
    """Metadata for embedding generation and storage."""
    
    # Generation metadata
    provider: str = Field(description="Embedding provider used")
    model: str = Field(description="Model name used for embeddings")
    dimension: int = Field(description="Embedding vector dimension")
    generation_timestamp: datetime = Field(default_factory=datetime.now, description="When embeddings were generated")
    
    # Processing metadata
    total_nodes: int = Field(description="Total number of nodes processed")
    nodes_with_embeddings: int = Field(description="Number of nodes with successful embeddings")
    success_rate: float = Field(ge=0.0, le=1.0, description="Success rate (0.0 to 1.0)")
    processing_time_seconds: float = Field(ge=0.0, description="Total processing time in seconds")
    
    # Configuration
    chunk_method: Optional[str] = Field(None, description="Text chunking method used")
    chunk_size: Optional[int] = Field(None, description="Chunk size if chunking was used")
    batch_size: int = Field(description="Batch size used for processing")
    
    # File metadata
    output_file_path: str = Field(description="Path to the output Parquet file")
    file_size_bytes: int = Field(description="Size of output file in bytes")
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            Path: str
        }


class EmbeddingNodeData(BaseModel):
    """Data structure for individual embedding nodes."""
    
    node_id: str = Field(description="Unique node identifier")
    text: str = Field(description="Node text content")
    embedding: Optional[List[float]] = Field(None, description="Embedding vector")
    
    # Source metadata
    source_id: Optional[str] = Field(None, description="Source document/property ID")
    source_type: Optional[str] = Field(None, description="Type of source (property, wikipedia, etc.)")
    
    # Processing metadata
    chunk_index: Optional[int] = Field(None, description="Index of chunk within source")
    created_at: datetime = Field(default_factory=datetime.now, description="When node was created")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional node metadata")


class EmbeddingBatch(BaseModel):
    """Complete embedding batch with metadata and nodes."""
    
    metadata: EmbeddingMetadata
    nodes: List[EmbeddingNodeData]
    
    def to_parquet_data(self) -> Dict[str, List[Any]]:
        """Convert to dictionary format suitable for Parquet writing."""
        return {
            'node_id': [node.node_id for node in self.nodes],
            'text': [node.text for node in self.nodes],
            'embedding': [node.embedding for node in self.nodes],
            'source_id': [node.source_id for node in self.nodes],
            'source_type': [node.source_type for node in self.nodes],
            'chunk_index': [node.chunk_index for node in self.nodes],
            'created_at': [node.created_at.isoformat() for node in self.nodes],
            'metadata': [json.dumps(node.metadata, cls=DecimalJSONEncoder) if node.metadata else '{}' for node in self.nodes]
        }
    
    def save_metadata(self, metadata_path: Path) -> None:
        """Save metadata to JSON file."""
        with open(metadata_path, 'w') as f:
            f.write(self.metadata.model_dump_json(indent=2))
    
    @classmethod
    def from_text_nodes(
        cls, 
        nodes: List, 
        provider: str,
        model: str,
        processing_time: float,
        chunk_method: Optional[str] = None,
        chunk_size: Optional[int] = None,
        batch_size: int = 50
    ) -> 'EmbeddingBatch':
        """Create EmbeddingBatch from LlamaIndex TextNodes."""
        from llama_index.core.schema import TextNode
        
        embedding_nodes = []
        nodes_with_embeddings = 0
        dimension = 0
        
        for i, node in enumerate(nodes):
            if isinstance(node, TextNode):
                # Extract embedding if available
                embedding = None
                if hasattr(node, 'embedding') and node.embedding is not None:
                    embedding = node.embedding
                    nodes_with_embeddings += 1
                    if dimension == 0:
                        dimension = len(embedding)
                
                # Extract metadata
                metadata = {}
                if hasattr(node, 'metadata') and node.metadata:
                    metadata = node.metadata
                
                # Create node data
                embedding_nodes.append(EmbeddingNodeData(
                    node_id=node.node_id or f"node_{i}",
                    text=node.text,
                    embedding=embedding,
                    source_id=metadata.get('source_id') or metadata.get('listing_id'),
                    source_type=metadata.get('source_type', 'property'),
                    chunk_index=metadata.get('chunk_index', i),
                    metadata=metadata
                ))
        
        # Create metadata
        success_rate = nodes_with_embeddings / len(nodes) if nodes else 0.0
        
        metadata = EmbeddingMetadata(
            provider=provider,
            model=model,
            dimension=dimension,
            total_nodes=len(nodes),
            nodes_with_embeddings=nodes_with_embeddings,
            success_rate=success_rate,
            processing_time_seconds=processing_time,
            chunk_method=chunk_method,
            chunk_size=chunk_size,
            batch_size=batch_size,
            output_file_path="",  # Will be set when writing
            file_size_bytes=0     # Will be set when writing
        )
        
        return cls(metadata=metadata, nodes=embedding_nodes)