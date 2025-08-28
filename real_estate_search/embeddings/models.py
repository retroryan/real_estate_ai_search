"""
Embedding configuration models for real estate search.

Simplified, focused configuration for query embeddings using Voyage AI.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum
import os


class EmbeddingProvider(str, Enum):
    """Supported embedding provider - focused on Voyage for demo."""
    VOYAGE = "voyage"


class EmbeddingConfig(BaseModel):
    """
    Embedding configuration for query embeddings.
    
    Simplified configuration focused on Voyage AI for demo purposes.
    Matches the configuration used by data_pipeline for consistency.
    """
    
    provider: EmbeddingProvider = Field(
        default=EmbeddingProvider.VOYAGE,
        description="Embedding provider (Voyage for demo)"
    )
    
    model_name: str = Field(
        default="voyage-3",
        description="Voyage model name"
    )
    
    dimension: int = Field(
        default=1024,
        description="Embedding dimension"
    )
    
    api_key: Optional[str] = Field(
        default=None,
        description="Voyage API key"
    )
    
    # Processing settings
    timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Timeout for API calls"
    )
    
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retries for failed requests"
    )
    
    @field_validator('api_key', mode='before')
    @classmethod
    def load_api_key(cls, v: Optional[str]) -> Optional[str]:
        """Load Voyage API key from environment if not provided."""
        if not v:
            v = os.getenv('VOYAGE_API_KEY')
            # Note: We don't raise an error here because the key might be loaded
            # via AppConfig from .env file. The service will validate when initialized.
        return v
    
    def get_model_identifier(self) -> str:
        """Get a unique identifier for the model configuration."""
        return f"{self.provider.value}_{self.model_name.replace('-', '_')}"