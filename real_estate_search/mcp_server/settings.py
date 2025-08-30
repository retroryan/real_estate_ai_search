"""Configuration settings for MCP Server using Pydantic."""

from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

# Load environment variables from parent .env file
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)


class ElasticsearchConfig(BaseModel):
    """Elasticsearch connection configuration."""
    
    model_config = ConfigDict(extra='forbid')
    
    host: str = Field(default="localhost", description="Elasticsearch host")
    port: int = Field(default=9200, description="Elasticsearch port")
    username: Optional[str] = Field(default=None, description="Elasticsearch username")
    password: Optional[str] = Field(default=None, description="Elasticsearch password")
    api_key: Optional[str] = Field(default=None, description="Elasticsearch API key")
    cloud_id: Optional[str] = Field(default=None, description="Elasticsearch cloud ID")
    
    property_index: str = Field(default="properties", description="Property index name")
    wiki_chunks_index_prefix: str = Field(default="wiki_chunks", description="Wikipedia chunks index prefix")
    wiki_summaries_index_prefix: str = Field(default="wiki_summaries", description="Wikipedia summaries index prefix")
    
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    verify_certs: bool = Field(default=False, description="Verify SSL certificates")
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v
    
    @property
    def url(self) -> str:
        """Get the Elasticsearch URL."""
        return f"http://{self.host}:{self.port}"


class EmbeddingConfig(BaseModel):
    """Embedding service configuration."""
    
    model_config = ConfigDict(extra='forbid')
    
    provider: Literal["voyage", "openai", "gemini", "ollama"] = Field(
        default="voyage",
        description="Embedding provider"
    )
    model_name: str = Field(default="voyage-3", description="Model name")
    dimension: int = Field(default=1024, description="Embedding dimension")
    api_key: Optional[str] = Field(default=None, description="API key for embedding service")
    batch_size: int = Field(default=10, description="Batch size for embedding generation")
    timeout_seconds: float = Field(default=30.0, description="Timeout for embedding requests")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    
    @field_validator('dimension')
    @classmethod
    def validate_dimension(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"Dimension must be positive, got {v}")
        return v
    
    @field_validator('batch_size')
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        if not 1 <= v <= 100:
            raise ValueError(f"Batch size must be between 1 and 100, got {v}")
        return v


class SearchConfig(BaseModel):
    """Search configuration."""
    
    model_config = ConfigDict(extra='forbid')
    
    default_size: int = Field(default=20, description="Default number of results")
    max_size: int = Field(default=100, description="Maximum number of results")
    default_sort: Literal["relevance", "date", "price"] = Field(
        default="relevance",
        description="Default sort order"
    )
    highlight_enabled: bool = Field(default=True, description="Enable highlighting")
    aggregations_enabled: bool = Field(default=True, description="Enable aggregations")
    enable_fuzzy: bool = Field(default=True, description="Enable fuzzy matching")
    
    # Hybrid search weights
    vector_weight: float = Field(default=0.5, description="Weight for vector search")
    text_weight: float = Field(default=0.5, description="Weight for text search")
    
    @field_validator('default_size')
    @classmethod
    def validate_default_size(cls, v: int, info) -> int:
        if v <= 0:
            raise ValueError(f"Default size must be positive, got {v}")
        return v
    
    @field_validator('vector_weight', 'text_weight')
    @classmethod
    def validate_weights(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError(f"Weight must be between 0 and 1, got {v}")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    model_config = ConfigDict(extra='forbid')
    
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    structured: bool = Field(default=False, description="Use structured logging")
    file_path: Optional[Path] = Field(default=None, description="Log file path")


class TransportConfig(BaseModel):
    """Transport configuration."""
    
    model_config = ConfigDict(extra='forbid')
    
    mode: Literal["stdio", "http", "streamable-http"] = Field(
        default="http",
        description="Transport mode"
    )
    host: str = Field(default="localhost", description="Host for HTTP transport")
    port: int = Field(default=8000, description="Port for HTTP transport")
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v


class MCPServerConfig(BaseSettings):
    """Main MCP Server configuration."""
    
    model_config = ConfigDict(
        env_prefix="MCP_",
        env_nested_delimiter="__",
        extra='forbid',
        validate_default=True
    )
    
    # Sub-configurations
    elasticsearch: ElasticsearchConfig = Field(default_factory=ElasticsearchConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    transport: TransportConfig = Field(default_factory=TransportConfig)
    
    # Server settings
    server_name: str = Field(default="real-estate-search-mcp", description="Server name")
    server_version: str = Field(default="0.1.0", description="Server version")
    debug: bool = Field(default=False, description="Debug mode")
    
    def model_post_init(self, __context) -> None:
        """Post-initialization to load API keys from environment."""
        self._load_api_keys()
    
    def _load_api_keys(self):
        """Load API keys from environment variables using model_copy."""
        # Load embedding API key based on provider
        embedding_updates = {}
        if self.embedding.provider == "voyage" and not self.embedding.api_key:
            if api_key := os.getenv("VOYAGE_API_KEY"):
                embedding_updates["api_key"] = api_key
        elif self.embedding.provider == "openai" and not self.embedding.api_key:
            if api_key := os.getenv("OPENAI_API_KEY"):
                embedding_updates["api_key"] = api_key
        elif self.embedding.provider == "gemini" and not self.embedding.api_key:
            if api_key := os.getenv("GOOGLE_API_KEY"):
                embedding_updates["api_key"] = api_key
        
        if embedding_updates:
            self.embedding = self.embedding.model_copy(update=embedding_updates)
        
        # Load Elasticsearch credentials
        es_updates = {}
        if not self.elasticsearch.username:
            if username := os.getenv("ES_USERNAME"):
                es_updates["username"] = username
        if not self.elasticsearch.password:
            if password := os.getenv("ES_PASSWORD"):
                es_updates["password"] = password
        if not self.elasticsearch.api_key:
            if api_key := os.getenv("ELASTICSEARCH_API_KEY"):
                es_updates["api_key"] = api_key
        if not self.elasticsearch.cloud_id:
            if cloud_id := os.getenv("ELASTICSEARCH_CLOUD_ID"):
                es_updates["cloud_id"] = cloud_id
        
        if es_updates:
            self.elasticsearch = self.elasticsearch.model_copy(update=es_updates)
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> "MCPServerConfig":
        """Load configuration from YAML file."""
        import yaml
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)
    
    @classmethod
    def from_env(cls) -> "MCPServerConfig":
        """Load configuration from environment variables."""
        return cls()