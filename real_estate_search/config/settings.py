"""
Configuration settings using Pydantic for type safety and validation.
Simplified to properly load from .env file.
"""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()


class ElasticsearchSettings(BaseSettings):
    """Elasticsearch connection settings."""
    
    host: str = Field(default="localhost", description="Elasticsearch host")
    port: int = Field(default=9200, ge=1, le=65535, description="Elasticsearch port")
    scheme: str = Field(default="http", pattern="^(http|https)$")
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    retry_on_timeout: bool = Field(default=True)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    # Authentication settings
    username: Optional[str] = Field(default=None, description="Elasticsearch username")
    password: Optional[str] = Field(default=None, description="Elasticsearch password")
    verify_certs: bool = Field(default=True, description="Verify SSL certificates")
    ca_certs: Optional[str] = Field(default=None, description="Path to CA certificate bundle")
    
    def __init__(self):
        """Initialize from environment variables with ES_ prefix."""
        super().__init__(
            host=os.getenv('ES_HOST', 'localhost'),
            port=int(os.getenv('ES_PORT', '9200')),
            scheme=os.getenv('ES_SCHEME', 'http'),
            timeout=int(os.getenv('ES_TIMEOUT', '30')),
            retry_on_timeout=os.getenv('ES_RETRY_ON_TIMEOUT', 'true').lower() == 'true',
            max_retries=int(os.getenv('ES_MAX_RETRIES', '3')),
            username=os.getenv('ES_USERNAME') or os.getenv('ELASTICSEARCH_USERNAME'),
            password=os.getenv('ES_PASSWORD') or os.getenv('ELASTICSEARCH_PASSWORD'),
            verify_certs=os.getenv('ES_VERIFY_CERTS', 'false').lower() == 'true',
            ca_certs=os.getenv('ES_CA_CERTS')
        )
    
    @property
    def url(self) -> str:
        """Get full Elasticsearch URL."""
        return f"{self.scheme}://{self.host}:{self.port}"
    
    @property
    def has_auth(self) -> bool:
        """Check if authentication is configured."""
        return bool(self.username and self.password)


class IndexSettings(BaseSettings):
    """Index configuration settings."""
    
    name: str = Field(default="properties", min_length=1, max_length=255)
    alias: str = Field(default="properties_alias", min_length=1, max_length=255)
    shards: int = Field(default=1, ge=1, le=10)
    replicas: int = Field(default=1, ge=0, le=5)
    refresh_interval: str = Field(default="1s")
    
    def __init__(self):
        """Initialize from environment variables with INDEX_ prefix."""
        super().__init__(
            name=os.getenv('INDEX_NAME', 'properties'),
            alias=os.getenv('INDEX_ALIAS', 'properties_alias'),
            shards=int(os.getenv('INDEX_SHARDS', '1')),
            replicas=int(os.getenv('INDEX_REPLICAS', '1')),
            refresh_interval=os.getenv('INDEX_REFRESH_INTERVAL', '1s')
        )
    
    @field_validator('name', 'alias')
    @classmethod
    def validate_index_name(cls, v: str) -> str:
        """Ensure index names are lowercase."""
        return v.lower()


class SearchSettings(BaseSettings):
    """Search configuration settings."""
    
    default_size: int = Field(default=20, ge=1, le=100)
    max_size: int = Field(default=100, ge=1, le=500)
    default_sort: str = Field(default="relevance")
    highlight_enabled: bool = Field(default=True)
    aggregations_enabled: bool = Field(default=True)
    
    def __init__(self):
        """Initialize from environment variables with SEARCH_ prefix."""
        super().__init__(
            default_size=int(os.getenv('SEARCH_DEFAULT_SIZE', '20')),
            max_size=int(os.getenv('SEARCH_MAX_SIZE', '100')),
            default_sort=os.getenv('SEARCH_DEFAULT_SORT', 'relevance'),
            highlight_enabled=os.getenv('SEARCH_HIGHLIGHT_ENABLED', 'true').lower() == 'true',
            aggregations_enabled=os.getenv('SEARCH_AGGREGATIONS_ENABLED', 'true').lower() == 'true'
        )


class IndexingSettings(BaseSettings):
    """Indexing configuration settings."""
    
    batch_size: int = Field(default=100, ge=1, le=1000)
    parallel_threads: int = Field(default=4, ge=1, le=16)
    refresh_after_index: bool = Field(default=True)
    validate_before_index: bool = Field(default=True)
    
    def __init__(self):
        """Initialize from environment variables with INDEXING_ prefix."""
        super().__init__(
            batch_size=int(os.getenv('INDEXING_BATCH_SIZE', '100')),
            parallel_threads=int(os.getenv('INDEXING_PARALLEL_THREADS', '4')),
            refresh_after_index=os.getenv('INDEXING_REFRESH_AFTER_INDEX', 'true').lower() == 'true',
            validate_before_index=os.getenv('INDEXING_VALIDATE_BEFORE_INDEX', 'true').lower() == 'true'
        )


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    
    level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    structured: bool = Field(default=True, description="Use structured logging")
    
    def __init__(self):
        """Initialize from environment variables with LOG_ prefix."""
        super().__init__(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            format=os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            structured=os.getenv('LOG_STRUCTURED', 'true').lower() == 'true'
        )


class Settings(BaseSettings):
    """Main settings container."""
    
    # Environment
    environment: str = Field(default="development", pattern="^(development|staging|production)$")
    debug: bool = Field(default=False)
    
    # Sub-settings
    elasticsearch: ElasticsearchSettings
    index: IndexSettings
    search: SearchSettings
    indexing: IndexingSettings
    logging: LoggingSettings
    
    def __init__(self):
        """Initialize all settings from environment."""
        super().__init__(
            environment=os.getenv('ENVIRONMENT', 'development'),
            debug=os.getenv('DEBUG', 'false').lower() == 'true',
            elasticsearch=ElasticsearchSettings(),
            index=IndexSettings(),
            search=SearchSettings(),
            indexing=IndexingSettings(),
            logging=LoggingSettings()
        )
    
    @classmethod
    def load(cls) -> 'Settings':
        """Load settings from environment."""
        return cls()


# Global settings instance
settings = Settings.load()