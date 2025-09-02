"""Embedding metadata models using Pydantic."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List


class EmbeddingMetadata(BaseModel):
    """Metadata for embedding generation results."""
    
    model_config = ConfigDict(frozen=True)
    
    entity_type: str = Field(description="Type of entity (property, neighborhood, wikipedia)")
    gold_table: str = Field(description="Gold table containing embeddings")
    records_processed: int = Field(ge=0, description="Number of records processed")
    embeddings_generated: int = Field(ge=0, description="Number of embeddings generated") 
    records_skipped: int = Field(ge=0, description="Number of records skipped (already had embeddings)")
    embedding_dimension: int = Field(default=1024, description="Embedding dimension")
    embedding_model: str = Field(default="voyage-3", description="Embedding model used")