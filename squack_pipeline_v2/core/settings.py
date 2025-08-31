"""Clean pipeline configuration using Pydantic V2."""

import os
import yaml
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from parent .env file
parent_env = Path(__file__).parent.parent.parent / '.env'
if parent_env.exists():
    load_dotenv(parent_env)


class DataSourcesConfig(BaseModel):
    """Data source file paths."""
    properties_files: List[str] = Field(
        default=["real_estate_data/properties_sf.json", "real_estate_data/properties_pc.json"]
    )
    neighborhoods_files: List[str] = Field(
        default=["real_estate_data/neighborhoods_sf.json", "real_estate_data/neighborhoods_pc.json"]
    )
    wikipedia_db_path: str = Field(default="data/wikipedia/wikipedia.db")


class DataConfig(BaseModel):
    """Data processing configuration."""
    input_path: str = Field(default="real_estate_data")
    output_path: str = Field(default="./squack_pipeline_v2/output")
    sample_size: Optional[int] = Field(default=None)


class DuckDBConfig(BaseModel):
    """DuckDB configuration."""
    memory_limit: str = Field(default="8GB")
    threads: int = Field(default=4)
    database_file: str = Field(default="pipeline_v2.duckdb")


class EmbeddingConfig(BaseModel):
    """Embedding configuration."""
    provider: str = Field(default="voyage")
    voyage_model: str = Field(default="voyage-3")
    openai_model: str = Field(default="text-embedding-3-small")
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="nomic-embed-text")
    gemini_model: str = Field(default="models/embedding-001")


class ProcessingConfig(BaseModel):
    """Processing configuration."""
    batch_size: int = Field(default=50)
    max_workers: int = Field(default=2)
    show_progress: bool = Field(default=True)
    rate_limit_delay: float = Field(default=0.1)


class ElasticsearchConfig(BaseModel):
    """Elasticsearch configuration."""
    host: str = Field(default="localhost")
    port: int = Field(default=9200)
    bulk_size: int = Field(default=500)
    timeout: int = Field(default=30)


class Neo4jConfig(BaseModel):
    """Neo4j configuration."""
    enabled: bool = Field(default=False)
    uri: str = Field(default="bolt://localhost:7687")
    username: str = Field(default="neo4j")
    password: str = Field(default=os.getenv("NEO4J_PASSWORD", "password"))
    database: str = Field(default="neo4j")


class OutputConfig(BaseModel):
    """Output configuration."""
    parquet_enabled: bool = Field(default=True)
    parquet_dir: str = Field(default="output/parquet")
    elasticsearch_enabled: bool = Field(default=False)
    elasticsearch: ElasticsearchConfig = Field(default_factory=ElasticsearchConfig)
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO")


class PipelineSettings(BaseSettings):
    """Main pipeline configuration with env variable support."""
    
    model_config = SettingsConfigDict(
        env_file=str(parent_env) if parent_env.exists() else None,
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )
    
    name: str = Field(default="squack_pipeline_v2")
    version: str = Field(default="2.0.0")
    environment: str = Field(default="development")
    
    data_sources: DataSourcesConfig = Field(default_factory=DataSourcesConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    duckdb: DuckDBConfig = Field(default_factory=DuckDBConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None, **overrides) -> "PipelineSettings":
        """Load configuration from YAML with environment variable support.
        
        Args:
            config_path: Path to YAML config file
            **overrides: Direct overrides to apply
            
        Returns:
            Configured PipelineSettings
        """
        # Start with base configuration
        config_data = {}
        
        # Load from YAML if provided
        if config_path and config_path.exists():
            with open(config_path) as f:
                yaml_data = yaml.safe_load(f) or {}
                config_data.update(yaml_data)
        
        # Apply overrides using structured approach
        for key, value in overrides.items():
            # Directly set or update config data
            # Pydantic will handle the proper merging during validation
            config_data[key] = value
        
        return cls(**config_data)
    
    def get_api_key(self) -> Optional[str]:
        """Get API key for configured embedding provider."""
        if self.embedding.provider == "voyage":
            return os.getenv("VOYAGE_API_KEY")
        elif self.embedding.provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        elif self.embedding.provider == "gemini":
            return os.getenv("GOOGLE_API_KEY")
        return None
    
    def get_model_name(self) -> str:
        """Get model name for configured embedding provider."""
        if self.embedding.provider == "voyage":
            return self.embedding.voyage_model
        elif self.embedding.provider == "openai":
            return self.embedding.openai_model
        elif self.embedding.provider == "ollama":
            return self.embedding.ollama_model
        elif self.embedding.provider == "gemini":
            return self.embedding.gemini_model
        return "unknown"