"""
Configuration models for the common embeddings module.

These models define the configuration structure for embedding generation,
storage, and processing, following patterns from wiki_embed and real_estate_embed.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from pathlib import Path
import os

from .enums import EmbeddingProvider, ChunkingMethod


class EmbeddingConfig(BaseModel):
    """
    Embedding service configuration supporting multiple providers.
    
    Adapted from wiki_embed and real_estate_embed patterns.
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
    
    @validator('openai_api_key', pre=True, always=True)
    def check_openai_key(cls, v, values):
        """Load OpenAI API key from environment if needed."""
        if values.get('provider') == EmbeddingProvider.OPENAI and not v:
            v = os.getenv('OPENAI_API_KEY')
            if not v:
                raise ValueError("OPENAI_API_KEY must be set for OpenAI provider")
        return v
    
    @validator('gemini_api_key', pre=True, always=True)
    def check_gemini_key(cls, v, values):
        """Load Gemini API key from environment if needed."""
        if values.get('provider') == EmbeddingProvider.GEMINI and not v:
            v = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
            if not v:
                raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY must be set for Gemini provider")
        return v
    
    @validator('voyage_api_key', pre=True, always=True)
    def check_voyage_key(cls, v, values):
        """Load Voyage API key from environment if needed."""
        if values.get('provider') == EmbeddingProvider.VOYAGE and not v:
            v = os.getenv('VOYAGE_API_KEY')
            if not v:
                raise ValueError("VOYAGE_API_KEY must be set for Voyage provider")
        return v
    
    @validator('cohere_api_key', pre=True, always=True)
    def check_cohere_key(cls, v, values):
        """Load Cohere API key from environment if needed."""
        if values.get('provider') == EmbeddingProvider.COHERE and not v:
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
    
    @validator('persist_directory')
    def ensure_directory_exists(cls, v):
        """Create directory if it doesn't exist."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    
    # Legacy support - map old 'path' to 'persist_directory'
    @property
    def path(self) -> str:
        """Backward compatibility for path attribute."""
        return self.persist_directory


class ChunkingConfig(BaseModel):
    """
    Configuration for text chunking strategies.
    
    Follows LlamaIndex best practices for node parsing.
    """
    
    method: ChunkingMethod = Field(
        default=ChunkingMethod.SEMANTIC,
        description="Chunking method to use"
    )
    
    # Simple chunking parameters
    chunk_size: int = Field(
        default=800,
        ge=128,
        le=2048,
        description="Maximum chunk size in tokens"
    )
    chunk_overlap: int = Field(
        default=100,
        ge=0,
        le=200,
        description="Overlap between chunks"
    )
    
    # Semantic chunking parameters
    breakpoint_percentile: int = Field(
        default=90,
        ge=50,
        le=99,
        description="Percentile for semantic breakpoints"
    )
    buffer_size: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Buffer size for semantic chunking"
    )
    
    # Processing options
    split_oversized_chunks: bool = Field(
        default=False,
        description="Split chunks exceeding max size"
    )
    max_chunk_size: int = Field(
        default=1000,
        ge=200,
        le=2000,
        description="Maximum size for any chunk"
    )


class ProcessingConfig(BaseModel):
    """
    Configuration for batch processing and performance.
    """
    
    batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Batch size for processing"
    )
    max_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Maximum parallel workers"
    )
    show_progress: bool = Field(
        default=True,
        description="Show progress indicators"
    )
    rate_limit_delay: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Delay between API calls in seconds"
    )
    document_batch_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Batch size for processing documents during chunking (for progress visibility)"
    )


class Config(BaseModel):
    """
    Main configuration for the common embeddings module.
    
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
    chunking: ChunkingConfig = Field(
        default_factory=ChunkingConfig,
        description="Text chunking configuration"
    )
    processing: ProcessingConfig = Field(
        default_factory=ProcessingConfig,
        description="Processing and performance configuration"
    )
    
    # Metadata version for tracking
    metadata_version: str = Field(
        default="1.0",
        description="Version of metadata schema"
    )
    
    @classmethod
    def from_yaml(cls, config_path: str = "common_embeddings/config.yaml") -> "Config":
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Validated Config instance
        """
        import yaml
        
        config_file = Path(config_path)
        if not config_file.exists():
            # Return default config if file doesn't exist
            return cls()
        
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(**data) if data else cls()
    
    def to_yaml(self, config_path: str = "common_embeddings/config.yaml") -> None:
        """
        Save configuration to YAML file.
        
        Args:
            config_path: Path to save YAML configuration
        """
        import yaml
        
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            yaml.safe_dump(
                self.dict(exclude_unset=True),
                f,
                default_flow_style=False,
                sort_keys=False
            )