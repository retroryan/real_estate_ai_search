"""
Unified configuration for the entire real estate search system using Pydantic.
Single source of truth with clean constructor injection patterns.
Supports both environment variables and YAML configuration.
"""

from typing import Optional, Dict, Any, Literal
from pathlib import Path
from pydantic import BaseModel, Field, computed_field, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os
import yaml
import logging
from enum import Enum
from real_estate_search.embeddings.models import EmbeddingConfig
import dspy

# Load environment variables from .env file
# Try parent directory first (where main .env typically lives)
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Fall back to default behavior

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Application environment enumeration."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    DEMO = "demo"


class ElasticsearchConfig(BaseSettings):
    """
    Elasticsearch configuration with comprehensive validation.
    Handles both standard Elasticsearch and Elastic Cloud connections.
    """
    
    model_config = SettingsConfigDict(
        env_prefix='ES_',  # Use ES_ prefix for env vars
        validate_default=True,
        validate_assignment=True,
        use_enum_values=True,
        str_strip_whitespace=True,
        case_sensitive=False,
        extra='ignore'
    )
    
    # Connection settings
    host: str = Field(
        default="localhost",
        min_length=1,
        description="Elasticsearch host"
    )
    port: int = Field(
        default=9200,
        ge=1,
        le=65535,
        description="Elasticsearch port"
    )
    scheme: Literal["http", "https"] = Field(
        default="http",
        description="Connection scheme"
    )
    
    # Authentication - ES_USERNAME and ES_PASSWORD will be automatically loaded
    username: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Username for basic auth"
    )
    password: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Password for basic auth"
    )
    api_key: Optional[str] = Field(
        default=None,
        min_length=1,
        description="API key for authentication"
    )
    cloud_id: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Elastic Cloud ID"
    )
    
    # Security settings
    verify_certs: bool = Field(
        default=False,
        description="Verify SSL certificates"
    )
    ca_certs: Optional[Path] = Field(
        default=None,
        description="Path to CA certificate bundle"
    )
    
    # Connection behavior
    request_timeout: int = Field(
        default=30,
        gt=0,
        le=300,
        description="Request timeout in seconds"
    )
    retry_on_timeout: bool = Field(
        default=True,
        description="Retry requests on timeout"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retries"
    )
    
    @computed_field
    @property
    def url(self) -> str:
        """Compute full Elasticsearch URL."""
        return f"{self.scheme}://{self.host}:{self.port}"
    
    @computed_field
    @property
    def has_auth(self) -> bool:
        """Check if authentication is configured."""
        return bool((self.username and self.password) or self.api_key or self.cloud_id)
    
    def get_client_config(self) -> Dict[str, Any]:
        """
        Generate Elasticsearch client configuration dictionary.
        Returns configuration ready for Elasticsearch client initialization.
        """
        if self.cloud_id:
            # Elastic Cloud configuration
            config: Dict[str, Any] = {
                "cloud_id": self.cloud_id,
                "request_timeout": self.request_timeout,
                "retry_on_timeout": self.retry_on_timeout,
                "max_retries": self.max_retries
            }
            
            # Add authentication
            if self.api_key:
                config["api_key"] = self.api_key
            elif self.username and self.password:
                config["basic_auth"] = (self.username, self.password)
        else:
            # Standard Elasticsearch configuration
            config = {
                "hosts": [self.url],
                "request_timeout": self.request_timeout,
                "verify_certs": self.verify_certs,
                "retry_on_timeout": self.retry_on_timeout,
                "max_retries": self.max_retries
            }
            
            # Add CA certificates if provided
            if self.ca_certs:
                config["ca_certs"] = str(self.ca_certs)
            
            # Add authentication
            if self.api_key:
                config["api_key"] = self.api_key
            elif self.username and self.password:
                config["basic_auth"] = (self.username, self.password)
        
        return config


class IndexConfig(BaseModel):
    """
    Index configuration settings with validation.
    Defines Elasticsearch index properties.
    """
    
    model_config = ConfigDict(
        validate_default=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    name: str = Field(
        default="properties",
        min_length=1,
        max_length=255,
        description="Index name"
    )
    alias: str = Field(
        default="properties_alias",
        min_length=1,
        max_length=255,
        description="Index alias"
    )
    shards: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of primary shards"
    )
    replicas: int = Field(
        default=1,
        ge=0,
        le=5,
        description="Number of replica shards"
    )
    refresh_interval: str = Field(
        default="1s",
        description="Index refresh interval"
    )


class SearchConfig(BaseModel):
    """
    Search configuration settings with comprehensive validation.
    Controls search behavior and result ranking.
    """
    
    model_config = ConfigDict(
        validate_default=True,
        validate_assignment=True
    )
    
    # Result size settings
    default_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Default number of results"
    )
    max_size: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Maximum allowed result size"
    )
    
    # Search behavior
    default_sort: Literal["relevance", "price_asc", "price_desc", "date"] = Field(
        default="relevance",
        description="Default sort order"
    )
    highlight_enabled: bool = Field(
        default=True,
        description="Enable search result highlighting"
    )
    aggregations_enabled: bool = Field(
        default=True,
        description="Enable search aggregations"
    )
    enable_fuzzy: bool = Field(
        default=True,
        description="Enable fuzzy matching"
    )
    
    # Field boost factors for relevance tuning
    boost_description: float = Field(
        default=2.0,
        ge=0.0,
        le=10.0,
        description="Description field boost factor"
    )
    boost_features: float = Field(
        default=1.5,
        ge=0.0,
        le=10.0,
        description="Features field boost factor"
    )
    boost_amenities: float = Field(
        default=1.5,
        ge=0.0,
        le=10.0,
        description="Amenities field boost factor"
    )
    boost_location: float = Field(
        default=1.8,
        ge=0.0,
        le=10.0,
        description="Location field boost factor"
    )
    
    @computed_field
    @property
    def boost_fields(self) -> Dict[str, float]:
        """Get all boost fields as a dictionary."""
        return {
            "description": self.boost_description,
            "features": self.boost_features,
            "amenities": self.boost_amenities,
            "location": self.boost_location
        }


class IndexingConfig(BaseModel):
    """
    Indexing configuration settings with validation.
    Controls bulk indexing behavior and performance.
    """
    
    model_config = ConfigDict(
        validate_default=True,
        validate_assignment=True
    )
    
    batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Documents per batch"
    )
    parallel_threads: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Number of parallel indexing threads"
    )
    refresh_after_index: bool = Field(
        default=True,
        description="Refresh index after bulk operations"
    )
    validate_before_index: bool = Field(
        default=True,
        description="Validate documents before indexing"
    )
    
    @computed_field
    @property
    def bulk_size_bytes(self) -> int:
        """Calculate approximate bulk size in bytes (assuming ~1KB per doc)."""
        return self.batch_size * 1024


class LoggingConfig(BaseModel):
    """
    Logging configuration settings with validation.
    Controls application logging behavior.
    """
    
    model_config = ConfigDict(
        validate_default=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        min_length=1,
        description="Log message format"
    )
    structured: bool = Field(
        default=True,
        description="Use structured JSON logging"
    )
    
    @computed_field
    @property
    def log_level_int(self) -> int:
        """Get numeric log level for Python logging."""
        levels = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50
        }
        return levels[self.level]


class DSPyConfig(BaseModel):
    """
    DSPy configuration for language model integration.
    Supports OpenRouter, OpenAI, Anthropic, and local models.
    """
    
    model_config = ConfigDict(
        validate_default=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    # Model configuration
    model: str = Field(
        default="openrouter/openai/gpt-4o-mini",
        description="LLM model identifier (e.g., 'openrouter/openai/gpt-4o-mini')"
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for generation"
    )
    max_tokens: int = Field(
        default=2000,
        ge=100,
        le=50000,
        description="Maximum output tokens"
    )
    
    # API configuration
    openrouter_api_key: Optional[str] = Field(
        default=None,
        description="OpenRouter API key"
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key"
    )
    
    # Caching and performance
    cache_enabled: bool = Field(
        default=True,
        description="Enable LLM response caching"
    )
    
    # DSPy adapter selection
    use_json_adapter: bool = Field(
        default=True,
        description="Use JSONAdapter for better structured output support"
    )
    
    def initialize_dspy(self) -> dspy.LM:
        """
        Initialize DSPy with the configured LLM.
        
        Returns:
            Configured DSPy LM instance
            
        Raises:
            ValueError: If required API key is missing
        """
        logger.info(f"Initializing DSPy with model: {self.model}")
        
        # Configure LLM kwargs
        llm_kwargs = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "cache": self.cache_enabled,
        }
        
        # Add API key based on model provider
        if self.model.startswith("openrouter/"):
            if not self.openrouter_api_key:
                raise ValueError("OpenRouter API key required for OpenRouter models")
            # DSPy will use OPENROUTER_API_KEY from environment
            os.environ["OPENROUTER_API_KEY"] = self.openrouter_api_key
        elif self.model.startswith("openai/") or self.model.startswith("gpt"):
            if not self.openai_api_key:
                raise ValueError("OpenAI API key required for OpenAI models")
            os.environ["OPENAI_API_KEY"] = self.openai_api_key
        elif self.model.startswith("anthropic/") or self.model.startswith("claude"):
            if not self.anthropic_api_key:
                raise ValueError("Anthropic API key required for Anthropic models")
            os.environ["ANTHROPIC_API_KEY"] = self.anthropic_api_key
        
        try:
            # Create LM instance
            llm = dspy.LM(model=self.model, **llm_kwargs)
            
            # Configure DSPy with adapter
            if self.use_json_adapter:
                try:
                    from dspy.adapters import JSONAdapter
                    adapter = JSONAdapter()
                    dspy.configure(lm=llm, adapter=adapter)
                    logger.info(f"DSPy configured with JSONAdapter for model: {self.model}")
                except ImportError:
                    # Fallback to default adapter
                    dspy.configure(lm=llm)
                    logger.info(f"DSPy configured with default adapter for model: {self.model}")
            else:
                dspy.configure(lm=llm)
                logger.info(f"DSPy configured with default adapter for model: {self.model}")
            
            return llm
            
        except Exception as e:
            logger.error(f"Failed to initialize DSPy: {e}")
            raise
    
    @classmethod
    def from_env(cls) -> "DSPyConfig":
        """
        Create DSPyConfig from environment variables.
        
        Returns:
            DSPyConfig instance populated from environment
        """
        return cls(
            model=os.getenv("LLM_MODEL", "openrouter/openai/gpt-4o-mini"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            use_json_adapter=os.getenv("USE_JSON_ADAPTER", "true").lower() == "true"
        )


class DataConfig(BaseModel):
    """
    Data paths configuration with validation.
    Manages data storage locations.
    """
    
    model_config = ConfigDict(
        validate_default=True,
        validate_assignment=True
    )
    
    wikipedia_db: Path = Field(
        default=Path("../data/wikipedia/wikipedia.db"),
        description="Wikipedia database path"
    )
    
    @computed_field
    @property
    def wikipedia_db_exists(self) -> bool:
        """Check if Wikipedia database file exists."""
        return self.wikipedia_db.exists()


class AppConfig(BaseSettings):
    """
    Main application configuration using Pydantic Settings.
    Central configuration for the entire real estate search system.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
        validate_default=True,
        validate_assignment=True
    )
    
    # Environment settings
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment"
    )
    debug: bool = Field(
        default=False,
        description="Debug mode"
    )
    demo_mode: bool = Field(
        default=True,
        description="Demo mode with sample data"
    )
    
    # Sub-configurations - ElasticsearchConfig will load its own env vars
    elasticsearch: ElasticsearchConfig = Field(
        default_factory=ElasticsearchConfig,
        description="Elasticsearch configuration"
    )
    
    index: IndexConfig = Field(
        default_factory=lambda: IndexConfig(
            name=os.getenv('INDEX_NAME', 'properties'),
            alias=os.getenv('INDEX_ALIAS', 'properties_alias'),
            shards=int(os.getenv('INDEX_SHARDS', '1')),
            replicas=int(os.getenv('INDEX_REPLICAS', '1')),
            refresh_interval=os.getenv('INDEX_REFRESH_INTERVAL', '1s')
        ),
        description="Index configuration"
    )
    
    search: SearchConfig = Field(
        default_factory=lambda: SearchConfig(
            default_size=int(os.getenv('SEARCH_DEFAULT_SIZE', '20')),
            max_size=int(os.getenv('SEARCH_MAX_SIZE', '100')),
            default_sort=os.getenv('SEARCH_DEFAULT_SORT', 'relevance'),  # type: ignore
            highlight_enabled=os.getenv('SEARCH_HIGHLIGHT_ENABLED', 'true').lower() == 'true',
            aggregations_enabled=os.getenv('SEARCH_AGGREGATIONS_ENABLED', 'true').lower() == 'true',
            enable_fuzzy=os.getenv('SEARCH_ENABLE_FUZZY', 'true').lower() == 'true',
            boost_description=float(os.getenv('SEARCH_BOOST_DESCRIPTION', '2.0')),
            boost_features=float(os.getenv('SEARCH_BOOST_FEATURES', '1.5')),
            boost_amenities=float(os.getenv('SEARCH_BOOST_AMENITIES', '1.5')),
            boost_location=float(os.getenv('SEARCH_BOOST_LOCATION', '1.8'))
        ),
        description="Search configuration"
    )
    
    indexing: IndexingConfig = Field(
        default_factory=lambda: IndexingConfig(
            batch_size=int(os.getenv('INDEXING_BATCH_SIZE', '100')),
            parallel_threads=int(os.getenv('INDEXING_PARALLEL_THREADS', '4')),
            refresh_after_index=os.getenv('INDEXING_REFRESH_AFTER_INDEX', 'true').lower() == 'true',
            validate_before_index=os.getenv('INDEXING_VALIDATE_BEFORE_INDEX', 'true').lower() == 'true'
        ),
        description="Indexing configuration"
    )
    
    logging: LoggingConfig = Field(
        default_factory=lambda: LoggingConfig(
            level=os.getenv('LOG_LEVEL', 'INFO'),  # type: ignore
            format=os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            structured=os.getenv('LOG_STRUCTURED', 'true').lower() == 'true'
        ),
        description="Logging configuration"
    )
    
    data: DataConfig = Field(
        default_factory=lambda: DataConfig(
            wikipedia_db=Path(os.getenv('DATA_WIKIPEDIA_DB', '../data/wikipedia/wikipedia.db'))
        ),
        description="Data paths configuration"
    )
    
    # Embedding configuration for semantic search
    embedding: EmbeddingConfig = Field(
        default_factory=lambda: EmbeddingConfig(
            api_key=os.getenv('VOYAGE_API_KEY')
        ),
        description="Embedding configuration for query processing"
    )
    
    # DSPy configuration for LLM integration
    dspy_config: DSPyConfig = Field(
        default_factory=DSPyConfig.from_env,
        description="DSPy configuration for language model integration"
    )
    
    @computed_field
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT
    
    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION
    
    @computed_field
    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.environment == Environment.STAGING
    
    @computed_field
    @property
    def is_demo(self) -> bool:
        """Check if running in demo mode."""
        return self.environment == Environment.DEMO or self.demo_mode
    
    @classmethod
    def load(cls) -> "AppConfig":
        """
        Load configuration from environment variables and .env file.
        
        Returns:
            Configured AppConfig instance
        """
        return cls()
    
    @classmethod
    def from_yaml(cls, path: Path = Path("config.yaml")) -> "AppConfig":
        """
        Load configuration from YAML file with environment variable override.
        
        Args:
            path: Path to YAML configuration file
            
        Returns:
            Configured AppConfig instance
        """
        logger.info(f"Loading configuration from {path}")
        
        if not path.exists():
            logger.warning(f"Configuration file {path} not found, using defaults with env overrides")
            return cls()
        
        try:
            with open(path) as f:
                yaml_data = yaml.safe_load(f) or {}
            
            # Convert environment string to enum if present
            if 'environment' in yaml_data and isinstance(yaml_data['environment'], str):
                yaml_data['environment'] = Environment(yaml_data['environment'])
            
            # Handle elasticsearch config specially to merge with env vars
            if 'elasticsearch' in yaml_data:
                # Create ElasticsearchConfig which will merge YAML with env vars
                yaml_data['elasticsearch'] = ElasticsearchConfig(**yaml_data['elasticsearch'])
            
            # Create config with YAML data
            config = cls(**yaml_data)
            logger.info("Configuration loaded successfully from YAML")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {path}: {e}")
            raise
    
    def save_yaml(self, path: Path = Path("config.yaml")) -> None:
        """
        Save current configuration to YAML file.
        
        Args:
            path: Path where YAML file will be saved
        """
        logger.info(f"Saving configuration to {path}")
        
        try:
            with open(path, 'w') as f:
                # Export with computed fields excluded and proper serialization
                data = self.model_dump(
                    exclude={'is_development', 'is_production', 'is_staging', 'is_demo'},
                    exclude_unset=False,
                    exclude_defaults=False,
                    mode='python'
                )
                
                # Convert Environment enum to string
                if 'environment' in data:
                    data['environment'] = data['environment'].value
                
                yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)
            
            logger.info("Configuration saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save configuration to {path}: {e}")
            raise
    
    def get_elasticsearch_client_config(self) -> Dict[str, Any]:
        """
        Get Elasticsearch client configuration.
        Convenience method that delegates to elasticsearch config.
        
        Returns:
            Elasticsearch client configuration dictionary
        """
        return self.elasticsearch.get_client_config()