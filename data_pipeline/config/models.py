"""
Pydantic models for pipeline configuration.

This module defines all configuration models used throughout the data pipeline,
ensuring type safety and validation for all configuration parameters.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ProviderType(str, Enum):
    """Supported embedding provider types."""
    
    OLLAMA = "ollama"
    OPENAI = "openai"
    VOYAGE = "voyage"
    GEMINI = "gemini"


class ChunkingMethod(str, Enum):
    """Text chunking methods."""
    
    SIMPLE = "simple"
    SEMANTIC = "semantic"
    SENTENCE = "sentence"


class OutputFormat(str, Enum):
    """Supported output formats."""
    
    PARQUET = "parquet"
    JSON = "json"
    CSV = "csv"
    DELTA = "delta"


class SparkConfig(BaseModel):
    """Spark session configuration."""
    
    app_name: str = Field(
        default="RealEstateDataPipeline",
        description="Spark application name"
    )
    master: str = Field(
        default="local[*]",
        description="Spark master URL"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional Spark configuration parameters"
    )
    memory: str = Field(
        default="4g",
        description="Driver memory allocation"
    )
    executor_memory: str = Field(
        default="2g",
        description="Executor memory allocation"
    )
    
    @field_validator("master")
    @classmethod
    def validate_master(cls, v: str) -> str:
        """Validate Spark master URL format."""
        valid_prefixes = ["local", "spark://", "yarn", "k8s://", "mesos://"]
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f"Invalid Spark master URL: {v}")
        return v


class DataSourceConfig(BaseModel):
    """Configuration for a data source."""
    
    path: str = Field(description="Path to the data source")
    format: str = Field(description="Data format (json, jdbc, csv, etc.)")
    enabled: bool = Field(default=True, description="Whether to load this source")
    options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional format-specific options"
    )
    
    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate that path is not empty."""
        if not v:
            raise ValueError("Data source path cannot be empty")
        return v


class EnrichmentConfig(BaseModel):
    """Data enrichment configuration."""
    
    city_abbreviations: Dict[str, str] = Field(
        default_factory=dict,
        description="City abbreviation mappings"
    )
    state_abbreviations: Dict[str, str] = Field(
        default_factory=dict,
        description="State abbreviation mappings"
    )
    normalize_features: bool = Field(
        default=True,
        description="Whether to normalize feature arrays"
    )
    add_derived_fields: bool = Field(
        default=True,
        description="Whether to add computed fields"
    )
    quality_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum quality score threshold"
    )


class EmbeddingConfig(BaseModel):
    """Embedding generation configuration."""
    
    provider: ProviderType = Field(
        default=ProviderType.OLLAMA,
        description="Embedding provider to use"
    )
    model: str = Field(
        default="nomic-embed-text",
        description="Model identifier"
    )
    batch_size: int = Field(
        default=100,
        gt=0,
        description="Batch size for embedding generation"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts"
    )
    timeout: int = Field(
        default=30,
        gt=0,
        description="Request timeout in seconds"
    )
    api_url: Optional[str] = Field(
        default=None,
        description="API endpoint URL"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication"
    )


class ChunkingConfig(BaseModel):
    """Text chunking configuration."""
    
    method: ChunkingMethod = Field(
        default=ChunkingMethod.SIMPLE,
        description="Chunking method to use"
    )
    chunk_size: int = Field(
        default=512,
        gt=0,
        description="Maximum chunk size in characters"
    )
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        description="Character overlap between chunks"
    )
    
    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap(cls, v: int, info) -> int:
        """Ensure overlap is less than chunk size."""
        if "chunk_size" in info.data and v >= info.data["chunk_size"]:
            raise ValueError("Chunk overlap must be less than chunk size")
        return v


class ProcessingConfig(BaseModel):
    """Data processing configuration."""
    
    enable_quality_checks: bool = Field(
        default=True,
        description="Enable data quality validation"
    )
    min_quality_score: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum acceptable quality score"
    )
    cache_intermediate_results: bool = Field(
        default=True,
        description="Cache intermediate DataFrames"
    )
    checkpoint_interval: int = Field(
        default=1000,
        gt=0,
        description="Records between checkpoints"
    )
    parallel_tasks: int = Field(
        default=4,
        gt=0,
        description="Number of parallel processing tasks"
    )


class OutputConfig(BaseModel):
    """Output configuration."""
    
    format: OutputFormat = Field(
        default=OutputFormat.PARQUET,
        description="Output format"
    )
    path: str = Field(
        default="data/processed/unified_dataset",
        description="Output path"
    )
    partitioning: List[str] = Field(
        default_factory=lambda: ["entity_type", "state"],
        description="Partitioning columns"
    )
    compression: str = Field(
        default="snappy",
        description="Compression codec"
    )
    overwrite: bool = Field(
        default=True,
        description="Overwrite existing output"
    )
    
    @field_validator("compression")
    @classmethod
    def validate_compression(cls, v: str) -> str:
        """Validate compression codec."""
        valid_codecs = ["none", "snappy", "gzip", "lz4", "brotli", "zstd"]
        if v.lower() not in valid_codecs:
            raise ValueError(f"Invalid compression codec: {v}")
        return v.lower()


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(
        default="INFO",
        description="Logging level"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    file: Optional[str] = Field(
        default=None,
        description="Log file path"
    )
    console: bool = Field(
        default=True,
        description="Enable console logging"
    )
    
    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid logging level: {v}")
        return v.upper()


class PipelineConfig(BaseModel):
    """Complete pipeline configuration."""
    
    name: str = Field(
        default="unified_real_estate_pipeline",
        description="Pipeline name"
    )
    version: str = Field(
        default="1.0.0",
        description="Pipeline version"
    )
    spark: SparkConfig = Field(
        default_factory=SparkConfig,
        description="Spark configuration"
    )
    data_sources: Dict[str, DataSourceConfig] = Field(
        default_factory=dict,
        description="Data source configurations"
    )
    enrichment: EnrichmentConfig = Field(
        default_factory=EnrichmentConfig,
        description="Enrichment configuration"
    )
    embedding: EmbeddingConfig = Field(
        default_factory=EmbeddingConfig,
        description="Embedding configuration"
    )
    chunking: ChunkingConfig = Field(
        default_factory=ChunkingConfig,
        description="Chunking configuration"
    )
    processing: ProcessingConfig = Field(
        default_factory=ProcessingConfig,
        description="Processing configuration"
    )
    output: OutputConfig = Field(
        default_factory=OutputConfig,
        description="Output configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )