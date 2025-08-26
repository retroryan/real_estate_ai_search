"""
Configuration models for the embeddings module.

Provides configuration structures for embedding, storage, chunking, and processing.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from pathlib import Path
import os
import yaml
import logging

from .enums import EmbeddingProvider, ChunkingMethod

logger = logging.getLogger(__name__)


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
    
    @field_validator('voyage_api_key')
    @classmethod
    def load_voyage_key(cls, v: Optional[str], info) -> Optional[str]:
        """Load Voyage API key from environment if needed."""
        if info.data.get('provider') == EmbeddingProvider.VOYAGE and not v:
            v = os.getenv('VOYAGE_API_KEY')
            if not v:
                raise ValueError("VOYAGE_API_KEY must be set for Voyage provider")
        return v
    
    @field_validator('openai_api_key')
    @classmethod
    def load_openai_key(cls, v: Optional[str], info) -> Optional[str]:
        """Load OpenAI API key from environment if needed."""
        if info.data.get('provider') == EmbeddingProvider.OPENAI and not v:
            v = os.getenv('OPENAI_API_KEY')
            if not v:
                raise ValueError("OPENAI_API_KEY must be set for OpenAI provider")
        return v
    
    @field_validator('gemini_api_key')
    @classmethod
    def load_gemini_key(cls, v: Optional[str], info) -> Optional[str]:
        """Load Gemini API key from environment if needed."""
        if info.data.get('provider') == EmbeddingProvider.GEMINI and not v:
            v = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
            if not v:
                raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY must be set for Gemini provider")
        return v
    
    @field_validator('cohere_api_key')
    @classmethod
    def load_cohere_key(cls, v: Optional[str], info) -> Optional[str]:
        """Load Cohere API key from environment if needed."""
        if info.data.get('provider') == EmbeddingProvider.COHERE and not v:
            v = os.getenv('COHERE_API_KEY')
            if not v:
                raise ValueError("COHERE_API_KEY must be set for Cohere provider")
        return v
    
    def get_model_identifier(self) -> str:
        """Get a unique identifier for the current model configuration."""
        if self.provider == EmbeddingProvider.VOYAGE:
            return f"voyage_{self.voyage_model.replace('-', '_')}"
        elif self.provider == EmbeddingProvider.OPENAI:
            return f"openai_{self.openai_model.replace('-', '_')}"
        elif self.provider == EmbeddingProvider.OLLAMA:
            return f"ollama_{self.ollama_model.replace('-', '_')}"
        elif self.provider == EmbeddingProvider.GEMINI:
            model_name = self.gemini_model.split('/')[-1].replace('-', '_')
            return f"gemini_{model_name}"
        elif self.provider == EmbeddingProvider.COHERE:
            return f"cohere_{self.cohere_model.replace('-', '_')}"
        else:
            return f"{self.provider.value}_unknown"
    
    def get_embedding_dimension(self) -> int:
        """Get expected embedding dimension for the configured model."""
        # Known dimensions for common models
        dimensions = {
            # Voyage models
            "voyage-3": 1024,
            "voyage-large-2": 1536,
            
            # OpenAI models
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            
            # Ollama models
            "nomic-embed-text": 768,
            "mxbai-embed-large": 1024,
            
            # Gemini models
            "embedding-001": 768,
            
            # Cohere models
            "embed-english-v3.0": 1024,
            "embed-multilingual-v3.0": 1024,
        }
        
        # Get the model name based on provider
        if self.provider == EmbeddingProvider.VOYAGE:
            model = self.voyage_model
        elif self.provider == EmbeddingProvider.OPENAI:
            model = self.openai_model
        elif self.provider == EmbeddingProvider.OLLAMA:
            model = self.ollama_model
        elif self.provider == EmbeddingProvider.GEMINI:
            model = self.gemini_model.split('/')[-1]
        elif self.provider == EmbeddingProvider.COHERE:
            model = self.cohere_model
        else:
            return 768  # Default dimension
        
        # Look up dimension
        for key, dim in dimensions.items():
            if key in model:
                return dim
        
        # Default dimensions by provider
        provider_defaults = {
            EmbeddingProvider.VOYAGE: 1024,
            EmbeddingProvider.OPENAI: 1536,
            EmbeddingProvider.OLLAMA: 768,
            EmbeddingProvider.GEMINI: 768,
            EmbeddingProvider.COHERE: 1024,
        }
        
        return provider_defaults.get(self.provider, 768)


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
        description="Batch size for processing documents during chunking"
    )


class Config(BaseModel):
    """
    Main configuration for the embeddings module.
    
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


class ExtendedConfig(Config):
    """
    Extended configuration for embeddings with chunking and processing.
    
    Extends the base Config with embedding-specific configuration options.
    """
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)


def load_config_from_yaml(config_path: str = "config.yaml"):
    """
    Load configuration from YAML file and create ExtendedConfig instance.
    
    Returns an ExtendedConfig that includes chunking and processing configs.
    """
    config_file = Path(config_path)
    if not config_file.exists():
        logger.info(f"Config file not found at {config_path}, using defaults")
        return ExtendedConfig()
    
    try:
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        if not data:
            logger.info("Empty config file, using defaults")
            return ExtendedConfig()
        
        # Build config dict with all sections
        config_data = {}
        
        # Add embedding config if present
        if 'embedding' in data:
            config_data['embedding'] = data['embedding']
        
        # Add chromadb config if present
        if 'chromadb' in data:
            config_data['chromadb'] = data['chromadb']
        
        # Add chunking config if present
        if 'chunking' in data:
            config_data['chunking'] = ChunkingConfig(**data['chunking'])
        
        # Add processing config if present
        if 'processing' in data:
            config_data['processing'] = ProcessingConfig(**data['processing'])
        
        # Create ExtendedConfig with all data
        config = ExtendedConfig(**config_data)
        
        logger.info(f"Loaded config from {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        logger.info("Using default configuration")
        return ExtendedConfig()


# For backward compatibility, export BaseConfig as an alias
BaseConfig = Config