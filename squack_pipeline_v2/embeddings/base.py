"""Base embedding provider interface.

Uses Pydantic models for API validation only, following DuckDB best practices.
"""

from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel, Field, ConfigDict


class EmbeddingRequest(BaseModel):
    """Request model for embedding generation."""
    
    model_config = ConfigDict(frozen=True)
    
    texts: List[str] = Field(description="Texts to embed")
    model_name: str = Field(description="Model to use for embeddings")


class EmbeddingResponse(BaseModel):
    """Response model for embedding generation."""
    
    model_config = ConfigDict(frozen=True)
    
    embeddings: List[List[float]] = Field(description="Generated embeddings")
    model_name: str = Field(description="Model used")
    dimension: int = Field(description="Embedding dimension")
    token_count: int = Field(default=0, description="Total tokens processed")


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers.
    
    Providers generate embeddings for text via external APIs.
    Pydantic models are used only for API validation.
    """
    
    def __init__(self, api_key: str, model_name: str, dimension: int):
        """Initialize provider.
        
        Args:
            api_key: API key for the provider
            model_name: Model to use for embeddings
            dimension: Expected embedding dimension
        """
        self.api_key = api_key
        self.model_name = model_name
        self.dimension = dimension
    
    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> EmbeddingResponse:
        """Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            EmbeddingResponse with generated embeddings
        """
        pass
    
    @abstractmethod
    def get_batch_size(self) -> int:
        """Get recommended batch size for this provider.
        
        Returns:
            Recommended batch size
        """
        pass
    
    def validate_request(self, texts: List[str]) -> EmbeddingRequest:
        """Validate and create embedding request.
        
        Args:
            texts: Texts to embed
            
        Returns:
            Validated EmbeddingRequest
        """
        return EmbeddingRequest(
            texts=texts,
            model_name=self.model_name
        )