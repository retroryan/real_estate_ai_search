"""
Unified YAML-based configuration for the entire real estate search system.
Single source of truth replacing dual configuration anti-pattern.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from pathlib import Path
import os


class ElasticsearchConfig(BaseModel):
    """Unified Elasticsearch configuration."""
    host: str = Field(default="localhost", description="Elasticsearch host")
    port: int = Field(default=9200, description="Elasticsearch port")
    
    # Authentication options
    username: Optional[str] = Field(default=None, description="Username for basic auth")
    password: Optional[str] = Field(default=None, description="Password for basic auth")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    cloud_id: Optional[str] = Field(default=None, description="Elastic Cloud ID")
    
    # Index settings
    property_index: str = Field(default="properties", description="Property index name")
    wiki_chunks_index_prefix: str = Field(default="wiki_chunks", description="Wikipedia chunks index prefix")
    wiki_summaries_index_prefix: str = Field(default="wiki_summaries", description="Wikipedia summaries index prefix")
    
    # Performance settings
    batch_size: int = Field(default=100, description="Batch size for bulk operations")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""
    provider: str = Field(default="ollama", description="Embedding provider: ollama, openai, voyage")
    model_name: str = Field(default="nomic-embed-text", description="Model name")
    
    # Provider-specific settings
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama host URL")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    voyage_api_key: Optional[str] = Field(default=None, description="Voyage API key")
    dimension: int = Field(default=768, description="Embedding dimension")
    
    def model_post_init(self, __context):
        """Load API keys from environment if not provided."""
        if self.openai_api_key is None:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if self.voyage_api_key is None:
            self.voyage_api_key = os.getenv("VOYAGE_API_KEY")
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider is supported."""
        valid_providers = {"ollama", "openai", "voyage", "gemini"}
        if v not in valid_providers:
            raise ValueError(f"Provider must be one of {valid_providers}, got {v}")
        return v


class DataConfig(BaseModel):
    """Data paths configuration."""
    wikipedia_db: Path = Field(default=Path("data/wikipedia/wikipedia.db"), description="Wikipedia database path")
    wikipedia_pages_dir: Path = Field(default=Path("data/wikipedia/pages"), description="Wikipedia HTML pages directory")
    properties_dir: Path = Field(default=Path("real_estate_data"), description="Properties JSON directory")
    
    def model_post_init(self, __context):
        """Ensure directories exist."""
        self.wikipedia_pages_dir.mkdir(parents=True, exist_ok=True)
        # Parent dir for wikipedia_db
        self.wikipedia_db.parent.mkdir(parents=True, exist_ok=True)


class ChunkingConfig(BaseModel):
    """Text chunking configuration."""
    chunk_size: int = Field(default=512, gt=0, description="Chunk size in tokens")
    chunk_overlap: int = Field(default=50, ge=0, description="Overlap between chunks")
    
    @field_validator('chunk_overlap')
    @classmethod
    def validate_overlap(cls, v: int, info) -> int:
        """Validate overlap is less than chunk size."""
        if 'chunk_size' in info.data and v >= info.data['chunk_size']:
            raise ValueError(f"Overlap must be less than chunk_size")
        return v


# ApiConfig removed - no longer needed with MCP server


class Config(BaseModel):
    """
    Single unified YAML-based configuration for entire system.
    This replaces both wiki_embed Config and real_estate_search Settings.
    """
    elasticsearch: ElasticsearchConfig = Field(default_factory=ElasticsearchConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    
    # Demo-specific settings
    demo_mode: bool = Field(default=True, description="Running in demo mode")
    force_recreate: bool = Field(default=False, description="Force recreate indices on startup")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    @classmethod
    def from_yaml(cls, path: Optional[Path] = None) -> "Config":
        """Load configuration from YAML file in real_estate_search directory."""
        import yaml
        
        # Default to config.yaml in real_estate_search directory
        if path is None:
            # This module is in real_estate_search/config/
            real_estate_search_root = Path(__file__).parent.parent
            path = real_estate_search_root / "config.yaml"
        
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        
        # Return default config if file doesn't exist
        return cls()
    
    def to_yaml(self, path: Optional[Path] = None):
        """Save configuration to YAML file in real_estate_search directory."""
        import yaml
        
        if path is None:
            # Save to real_estate_search directory by default
            real_estate_search_root = Path(__file__).parent.parent
            path = real_estate_search_root / "config.yaml"
        
        with open(path, 'w') as f:
            # Convert Path objects to strings for YAML serialization
            data = self.model_dump(exclude_none=True)
            data = self._paths_to_strings(data)
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def _paths_to_strings(self, obj: Any) -> Any:
        """Recursively convert Path objects to strings for YAML serialization."""
        if isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: self._paths_to_strings(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._paths_to_strings(v) for v in obj]
        return obj
    
    def get_es_client_config(self) -> Dict[str, Any]:
        """Get Elasticsearch client configuration."""
        es = self.elasticsearch
        
        # Elastic Cloud configuration
        if es.cloud_id:
            config = {
                "cloud_id": es.cloud_id,
                "request_timeout": es.request_timeout
            }
            if es.api_key:
                config["api_key"] = es.api_key
            elif es.username and es.password:
                config["basic_auth"] = (es.username, es.password)
            return config
        
        # Standard Elasticsearch configuration
        else:
            # Build proper URL with http scheme
            url = f"http://{es.host}:{es.port}"
            config = {
                "hosts": [url],
                "request_timeout": es.request_timeout,
                "verify_certs": False  # For demo/dev environments
            }
            
            # Add authentication if provided
            if es.api_key:
                config["api_key"] = es.api_key
            elif es.username and es.password:
                config["basic_auth"] = (es.username, es.password)
                
            return config
    
    def get_wiki_chunks_index(self) -> str:
        """Get the wiki chunks index name with model suffix."""
        return f"{self.elasticsearch.wiki_chunks_index_prefix}_{self.embedding.model_name}"
    
    def get_wiki_summaries_index(self) -> str:
        """Get the wiki summaries index name with model suffix."""
        return f"{self.elasticsearch.wiki_summaries_index_prefix}_{self.embedding.model_name}"