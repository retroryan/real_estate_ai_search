"""Configuration management using Pydantic V2 BaseSettings."""

import os
import yaml
from enum import Enum
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from parent .env file if it exists
parent_env = Path(__file__).parent.parent.parent / '.env'
if parent_env.exists():
    load_dotenv(parent_env)


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    VOYAGE = "voyage"
    OPENAI = "openai"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    MOCK = "mock"


class ChunkingMethod(str, Enum):
    """Supported text chunking methods."""
    SIMPLE = "simple"
    SEMANTIC = "semantic"
    SENTENCE = "sentence"
    NONE = "none"


class DuckDBConfig(BaseSettings):
    """DuckDB configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix='DUCKDB_',
        str_strip_whitespace=True
    )
    
    memory_limit: str = Field(default="8GB", description="Memory limit for DuckDB")
    threads: int = Field(default=4, ge=1, description="Number of threads for DuckDB")
    database_path: str = Field(default=":memory:", description="Path to DuckDB database file")
    enable_progress_bar: bool = Field(default=True, description="Show progress bars")
    preserve_insertion_order: bool = Field(default=True, description="Preserve data insertion order")


class ParquetConfig(BaseSettings):
    """Parquet output configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix='PARQUET_',
        str_strip_whitespace=True
    )
    
    compression: str = Field(default="snappy", description="Compression algorithm")
    row_group_size: int = Field(default=122880, gt=0, description="Row group size")
    use_dictionary: bool = Field(default=True, description="Use dictionary encoding")
    per_thread_output: bool = Field(default=False, description="Write one file per thread")


class EmbeddingConfig(BaseModel):
    """Embedding generation configuration following common_embeddings patterns."""
    
    provider: EmbeddingProvider = Field(default=EmbeddingProvider.VOYAGE, description="Embedding provider")
    
    # Model settings
    voyage_model: str = Field(default="voyage-3", description="Voyage model name")
    openai_model: str = Field(default="text-embedding-3-small", description="OpenAI model name")
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    ollama_model: str = Field(default="nomic-embed-text", description="Ollama model name")
    gemini_model: str = Field(default="models/embedding-001", description="Gemini model name")
    
    # Mock settings (for testing)
    mock_dimension: int = Field(default=1024, description="Mock embedding dimension")
    
    @property
    def voyage_api_key(self) -> Optional[str]:
        """Get Voyage API key from environment variable."""
        return os.getenv('VOYAGE_API_KEY')
    
    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from environment variable."""
        return os.getenv('OPENAI_API_KEY')
    
    @property
    def gemini_api_key(self) -> Optional[str]:
        """Get Gemini API key from environment variable."""
        return os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')


class DataSourcesConfig(BaseModel):
    """Data source paths configuration."""
    properties_files: List[Path] = Field(
        default=[
            Path("real_estate_data/properties_sf.json"),
            Path("real_estate_data/properties_pc.json")
        ],
        description="List of property JSON files"
    )
    neighborhoods_files: List[Path] = Field(
        default=[
            Path("real_estate_data/neighborhoods_sf.json"),
            Path("real_estate_data/neighborhoods_pc.json")
        ],
        description="List of neighborhood JSON files"
    )
    wikipedia_db_path: Path = Field(
        default=Path("data/wikipedia/wikipedia.db"),
        description="Path to Wikipedia SQLite database"
    )
    locations_file: Path = Field(
        default=Path("real_estate_data/locations.json"),
        description="Path to locations JSON file"
    )


class DataConfig(BaseSettings):
    """Data paths and processing configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix='DATA_',
        str_strip_whitespace=True
    )
    
    input_path: Path = Field(default=Path("real_estate_data"), description="Input data directory")
    output_path: Path = Field(default=Path("squack_pipeline_output"), description="Output directory")
    sample_size: Optional[int] = Field(default=None, ge=1, description="Sample size for testing")


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix='LOG_',
        str_strip_whitespace=True
    )
    
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
        description="Log format string"
    )
    serialize: bool = Field(default=False, description="Serialize logs to JSON")
    log_file: Optional[Path] = Field(default=None, description="Log file path")
    rotation: str = Field(default="100 MB", description="Log rotation size")
    retention: str = Field(default="10 days", description="Log retention period")


class ProcessingConfig(BaseModel):
    """Processing and performance configuration."""
    
    batch_size: int = Field(default=50, ge=1, le=1000, description="Batch size for processing")
    max_workers: int = Field(default=2, ge=1, le=10, description="Maximum worker threads")
    show_progress: bool = Field(default=True, description="Show progress bars")
    rate_limit_delay: float = Field(default=0.1, ge=0, description="Delay between API calls")
    
    # Embedding processing options
    generate_embeddings: bool = Field(default=True, description="Generate embeddings")
    
    # Chunking options
    enable_chunking: bool = Field(default=True, description="Enable text chunking")
    chunk_method: ChunkingMethod = Field(default=ChunkingMethod.SEMANTIC, description="Chunking method")
    chunk_size: int = Field(default=800, ge=128, le=2048, description="Maximum chunk size in tokens")
    chunk_overlap: int = Field(default=100, ge=0, le=500, description="Overlap between chunks")
    
    # Semantic chunking parameters
    breakpoint_percentile: int = Field(default=90, ge=50, le=99, description="Breakpoint percentile")
    buffer_size: int = Field(default=2, ge=1, le=10, description="Buffer size for semantic chunking")


class ElasticsearchConfig(BaseModel):
    """Elasticsearch output configuration."""
    
    host: str = Field(default="localhost", description="Elasticsearch host")
    port: int = Field(default=9200, ge=1, le=65535, description="Elasticsearch port")
    bulk_size: int = Field(default=500, ge=1, le=10000, description="Bulk operation size")
    username: Optional[str] = Field(default="elastic", description="Elasticsearch username")
    timeout: int = Field(default=30, ge=1, description="Request timeout in seconds")
    
    @property
    def password(self) -> Optional[str]:
        """Get Elasticsearch password from environment variable."""
        return os.getenv('ELASTICSEARCH_PASSWORD')


class MedallionConfig(BaseModel):
    """Medallion architecture configuration."""
    
    enable_silver: bool = Field(default=True, description="Enable Silver tier processing")
    enable_gold: bool = Field(default=True, description="Enable Gold tier processing")
    enable_enrichment: bool = Field(default=True, description="Enable data enrichment")
    
    # Data quality thresholds
    min_completeness: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum data completeness")
    max_null_ratio: float = Field(default=0.3, ge=0.0, le=1.0, description="Maximum null ratio")


class OutputConfig(BaseModel):
    """Output destinations configuration."""
    
    enabled_destinations: List[str] = Field(
        default=["parquet"],
        description="List of enabled output destinations (parquet, elasticsearch)"
    )
    elasticsearch: Optional[ElasticsearchConfig] = Field(
        default=None,
        description="Elasticsearch configuration"
    )
    
    @field_validator('enabled_destinations')
    @classmethod
    def validate_destinations(cls, v: List[str]) -> List[str]:
        """Validate output destinations."""
        valid_destinations = {"parquet", "elasticsearch"}
        invalid = set(v) - valid_destinations
        if invalid:
            raise ValueError(f"Invalid destinations: {invalid}. Must be one of {valid_destinations}")
        return v


class PipelineSettings(BaseSettings):
    """Main pipeline configuration."""
    
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / '.env'),
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )
    
    # Pipeline metadata
    pipeline_name: str = Field(default="SQUACK Pipeline", description="Pipeline name")
    pipeline_version: str = Field(default="1.0.0", description="Pipeline version")
    environment: str = Field(default="development", description="Environment name")
    
    # Sub-configurations
    duckdb: DuckDBConfig = Field(default_factory=DuckDBConfig)
    parquet: ParquetConfig = Field(default_factory=ParquetConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    medallion: MedallionConfig = Field(default_factory=MedallionConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    data_sources: DataSourcesConfig = Field(default_factory=DataSourcesConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    
    # Metadata versioning
    metadata_version: str = Field(default="1.0", description="Configuration metadata version")
    
    # Processing options
    validate_output: bool = Field(default=True, description="Validate output data")
    fail_fast: bool = Field(default=False, description="Stop on first error")
    dry_run: bool = Field(default=False, description="Run without writing output")
    
    def model_post_init(self, __context) -> None:
        """Post-initialization validation and setup."""
        # Create output directory if it doesn't exist
        if not self.dry_run:
            self.data.output_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize Elasticsearch config if needed
        if "elasticsearch" in self.output.enabled_destinations and self.output.elasticsearch is None:
            self.output.elasticsearch = ElasticsearchConfig()
    
    @classmethod
    def load_from_yaml(cls, yaml_path: Path | str = "config.yaml") -> "PipelineSettings":
        """Load settings from a YAML file following common_embeddings patterns."""
        config_file = Path(yaml_path)
        
        if not config_file.exists():
            # Return default configuration if file doesn't exist
            return cls()
        
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        # Build config dict with all sections, handling nested structure
        config_data = {}
        
        # Basic pipeline fields
        for field in ['name', 'version', 'environment', 'metadata_version']:
            if field in data:
                config_data[field.replace('name', 'pipeline_name').replace('version', 'pipeline_version')] = data[field]
        
        # Nested configuration sections
        nested_sections = ['duckdb', 'parquet', 'embedding', 'processing', 'medallion', 'data', 'data_sources', 'logging', 'output']
        for section in nested_sections:
            if section in data:
                config_data[section] = data[section]
        
        # Processing options
        for field in ['validate_output', 'fail_fast', 'dry_run']:
            if field in data:
                config_data[field] = data[field]
        
        return cls(**config_data)
    
    def to_yaml(self, yaml_path: Path) -> None:
        """Save settings to a YAML file."""
        import yaml
        
        config_dict = self.model_dump()
        with open(yaml_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)