"""
Configuration models for the Property Finder ecosystem.

Provides configuration structures for embedding, storage, and processing.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from pathlib import Path
import os

from .enums import EmbeddingProvider


class EmbeddingConfig(BaseModel):
    """
    Embedding service configuration supporting multiple providers.
    """
    
    provider: EmbeddingProvider = Field(
        default=EmbeddingProvider.OLLAMA,
        description="Embedding provider to use"
    )
    
    # Ollama settings
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL"
    )
    ollama_model: str = Field(
        default="nomic-embed-text",
        description="Ollama model name"
    )
    
    # OpenAI settings
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI model name"
    )
    
    # Gemini settings
    gemini_api_key: Optional[str] = Field(None, description="Google API key")
    gemini_model: str = Field(
        default="models/embedding-001",
        description="Gemini model name"
    )
    
    # Voyage settings
    voyage_api_key: Optional[str] = Field(None, description="Voyage API key")
    voyage_model: str = Field(
        default="voyage-3",
        description="Voyage model name"
    )
    
    # Cohere settings
    cohere_api_key: Optional[str] = Field(None, description="Cohere API key")
    cohere_model: str = Field(
        default="embed-english-v3.0",
        description="Cohere model name"
    )
    
    @field_validator('openai_api_key')
    @classmethod
    def check_openai_key(cls, v: Optional[str], info) -> Optional[str]:
        """Load OpenAI API key from environment if needed."""
        if info.data.get('provider') == EmbeddingProvider.OPENAI and not v:
            v = os.getenv('OPENAI_API_KEY')
            if not v:
                raise ValueError("OPENAI_API_KEY must be set for OpenAI provider")
        return v
    
    @field_validator('gemini_api_key')
    @classmethod
    def check_gemini_key(cls, v: Optional[str], info) -> Optional[str]:
        """Load Gemini API key from environment if needed."""
        if info.data.get('provider') == EmbeddingProvider.GEMINI and not v:
            v = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
            if not v:
                raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY must be set for Gemini provider")
        return v
    
    @field_validator('voyage_api_key')
    @classmethod
    def check_voyage_key(cls, v: Optional[str], info) -> Optional[str]:
        """Load Voyage API key from environment if needed."""
        if info.data.get('provider') == EmbeddingProvider.VOYAGE and not v:
            v = os.getenv('VOYAGE_API_KEY')
            if not v:
                raise ValueError("VOYAGE_API_KEY must be set for Voyage provider")
        return v
    
    @field_validator('cohere_api_key')
    @classmethod
    def check_cohere_key(cls, v: Optional[str], info) -> Optional[str]:
        """Load Cohere API key from environment if needed."""
        if info.data.get('provider') == EmbeddingProvider.COHERE and not v:
            v = os.getenv('COHERE_API_KEY')
            if not v:
                raise ValueError("COHERE_API_KEY must be set for Cohere provider")
        return v


class ChromaDBConfig(BaseModel):
    """
    ChromaDB configuration with flexible collection naming patterns.
    
    Supports both local file storage and remote ChromaDB server.
    """
    
    # Server configuration (for future remote support)
    host: str = Field(
        default="localhost",
        description="ChromaDB host (for remote server)"
    )
    port: int = Field(
        default=8000,
        description="ChromaDB port (for remote server)"
    )
    persist_directory: str = Field(
        default="./data/common_embeddings",
        description="Local storage directory"
    )
    
    # Collection naming patterns by entity type
    property_collection_pattern: str = Field(
        default="property_{model}_v{version}",
        description="Naming pattern for property collections"
    )
    wikipedia_collection_pattern: str = Field(
        default="wikipedia_{model}_v{version}",
        description="Naming pattern for Wikipedia collections"
    )
    neighborhood_collection_pattern: str = Field(
        default="neighborhood_{model}_v{version}",
        description="Naming pattern for neighborhood collections"
    )
    
    @field_validator('persist_directory')
    @classmethod
    def ensure_directory_exists(cls, v: str) -> str:
        """Create directory if it doesn't exist."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)


class Config(BaseModel):
    """
    Main configuration for the Property Finder ecosystem.
    
    This is the root configuration that contains all sub-configurations.
    """
    
    embedding: EmbeddingConfig = Field(
        default_factory=EmbeddingConfig,
        description="Embedding provider configuration"
    )
    chromadb: ChromaDBConfig = Field(
        default_factory=ChromaDBConfig,
        description="ChromaDB storage configuration"
    )
    
    # Metadata version for tracking
    metadata_version: str = Field(
        default="1.0",
        description="Version of metadata schema"
    )