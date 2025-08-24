"""
Comprehensive configuration for the entire real estate search system using Pydantic.
Single source of truth with clean constructor injection patterns.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from pathlib import Path
import yaml
import logging
import os

logger = logging.getLogger(__name__)


class ElasticsearchConfig(BaseModel):
    """Elasticsearch configuration with validation."""
    host: str = Field(default="localhost", description="Elasticsearch host")
    port: int = Field(default=9200, description="Elasticsearch port", ge=1, le=65535)
    username: Optional[str] = Field(default=None, description="Username for basic auth")
    password: Optional[str] = Field(default=None, description="Password for basic auth")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    cloud_id: Optional[str] = Field(default=None, description="Elastic Cloud ID")
    property_index: str = Field(default="properties", description="Property index name")
    wiki_chunks_index_prefix: str = Field(default="wiki_chunks", description="Wikipedia chunks index prefix")
    wiki_summaries_index_prefix: str = Field(default="wiki_summaries", description="Wikipedia summaries index prefix")
    batch_size: int = Field(default=100, description="Batch size for bulk operations", gt=0)
    request_timeout: int = Field(default=30, description="Request timeout in seconds", gt=0)
    verify_certs: bool = Field(default=False, description="Verify SSL certificates")


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""
    provider: str = Field(default="ollama", description="Embedding provider")
    model_name: str = Field(default="nomic-embed-text", description="Model name")
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama host URL")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    voyage_api_key: Optional[str] = Field(default=None, description="Voyage API key")
    dimension: int = Field(default=768, description="Embedding dimension", gt=0)
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider is supported."""
        valid_providers = {"ollama", "openai", "voyage", "gemini"}
        if v not in valid_providers:
            raise ValueError(f"Provider must be one of {valid_providers}, got {v}")
        return v
    
    def model_post_init(self, __context):
        """Load API keys from environment if not provided."""
        if self.openai_api_key is None:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if self.voyage_api_key is None:
            self.voyage_api_key = os.getenv("VOYAGE_API_KEY")


class DataConfig(BaseModel):
    """Data paths configuration."""
    wikipedia_db: Path = Field(default=Path("../data/wikipedia/wikipedia.db"))
    wikipedia_pages_dir: Path = Field(default=Path("../data/wikipedia/pages"))
    properties_dir: Path = Field(default=Path("../real_estate_data"))
    
    def model_post_init(self, __context):
        """Ensure directories exist."""
        self.wikipedia_pages_dir.mkdir(parents=True, exist_ok=True)
        self.wikipedia_db.parent.mkdir(parents=True, exist_ok=True)


class ChunkingConfig(BaseModel):
    """Text chunking configuration."""
    chunk_size: int = Field(default=512, description="Chunk size in tokens", gt=0)
    chunk_overlap: int = Field(default=50, description="Overlap between chunks", ge=0)
    
    @field_validator('chunk_overlap')
    @classmethod
    def validate_overlap(cls, v: int, info) -> int:
        """Validate overlap is less than chunk size."""
        if 'chunk_size' in info.data and v >= info.data['chunk_size']:
            raise ValueError(f"Overlap must be less than chunk_size")
        return v


class AppConfig(BaseModel):
    """
    Single comprehensive configuration for entire system.
    All components receive this through constructor injection.
    """
    elasticsearch: ElasticsearchConfig = Field(default_factory=ElasticsearchConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    demo_mode: bool = Field(default=True, description="Running in demo mode")
    force_recreate: bool = Field(default=False, description="Force recreate indices on startup")
    log_level: str = Field(default="INFO", description="Logging level")
    
    @classmethod
    def from_yaml(cls, path: Path = Path("config.yaml")) -> "AppConfig":
        """Load configuration from YAML file."""
        logger.info(f"Loading configuration from {path}")
        
        if not path.exists():
            logger.warning(f"Configuration file {path} not found, using defaults")
            return cls()
        
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        
        config = cls(**data)
        logger.info("Configuration loaded successfully")
        return config
    
    def to_yaml(self, path: Path = Path("config.yaml")):
        """Save configuration to YAML file."""
        logger.info(f"Saving configuration to {path}")
        
        with open(path, 'w') as f:
            data = self.model_dump(exclude_none=True, mode='json')
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        logger.info("Configuration saved successfully")
    
    def get_wiki_chunks_index(self) -> str:
        """Get the wiki chunks index name with model suffix."""
        return f"{self.elasticsearch.wiki_chunks_index_prefix}_{self.embedding.model_name}"
    
    def get_wiki_summaries_index(self) -> str:
        """Get the wiki summaries index name with model suffix."""
        return f"{self.elasticsearch.wiki_summaries_index_prefix}_{self.embedding.model_name}"