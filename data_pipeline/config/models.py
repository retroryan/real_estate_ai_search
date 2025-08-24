"""
Enhanced Pydantic models for pipeline configuration.

This module defines comprehensive configuration models for the data pipeline,
with support for data subsetting, flexible embedding models, and advanced options.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import os

from pydantic import BaseModel, Field, field_validator


class ProviderType(str, Enum):
    """Supported embedding provider types."""
    
    OLLAMA = "ollama"
    OPENAI = "openai"
    VOYAGE = "voyage"
    GEMINI = "gemini"
    MOCK = "mock"


class ChunkingMethod(str, Enum):
    """Text chunking methods."""
    
    SIMPLE = "simple"
    SEMANTIC = "semantic"
    SENTENCE = "sentence"
    NONE = "none"


class OutputFormat(str, Enum):
    """Supported output formats."""
    
    PARQUET = "parquet"
    JSON = "json"
    CSV = "csv"
    DELTA = "delta"


class DataSubsetConfig(BaseModel):
    """Configuration for data subsetting during testing."""
    
    enabled: bool = Field(
        default=False,
        description="Enable data subsetting for testing"
    )
    sample_size: int = Field(
        default=50,
        ge=1,
        description="Number of records to sample from each source"
    )
    sample_method: str = Field(
        default="head",
        description="Sampling method: head, random, stratified"
    )
    random_seed: int = Field(
        default=42,
        description="Random seed for reproducible sampling"
    )
    properties_limit: int = Field(
        default=20,
        description="Maximum properties per city"
    )
    neighborhoods_limit: int = Field(
        default=10,
        description="Maximum neighborhoods per city"
    )
    wikipedia_limit: int = Field(
        default=30,
        description="Maximum Wikipedia articles"
    )
    location_filters: Dict[str, List[str]] = Field(
        default_factory=lambda: {"cities": [], "states": []},
        description="Filter by specific locations"
    )


class SubsetConfig(BaseModel):
    """Source-specific subset configuration."""
    
    max_records: Optional[int] = Field(
        default=None,
        description="Maximum records for this source"
    )
    filter_expression: Optional[str] = Field(
        default=None,
        description="SQL WHERE clause for filtering"
    )


class ModelConfig(BaseModel):
    """Configuration for a specific embedding model."""
    
    model: str = Field(description="Model name or identifier")
    api_key: Optional[str] = Field(
        default=None,
        description="API key (can use ${ENV_VAR} syntax)"
    )
    base_url: Optional[str] = Field(
        default=None,
        description="Base URL for API endpoint"
    )
    dimension: int = Field(
        default=768,
        description="Embedding dimension"
    )
    
    def get_api_key(self) -> Optional[str]:
        """Resolve API key from environment if needed."""
        if self.api_key and self.api_key.startswith("${") and self.api_key.endswith("}"):
            env_var = self.api_key[2:-1]
            return os.getenv(env_var)
        return self.api_key


class ModelsConfig(BaseModel):
    """Configuration for all available embedding models."""
    
    voyage: Optional[ModelConfig] = Field(
        default=None,
        description="Voyage AI configuration"
    )
    ollama: Optional[ModelConfig] = Field(
        default=None,
        description="Ollama configuration"
    )
    openai: Optional[ModelConfig] = Field(
        default=None,
        description="OpenAI configuration"
    )
    gemini: Optional[ModelConfig] = Field(
        default=None,
        description="Gemini configuration"
    )


class SemanticChunkingConfig(BaseModel):
    """Configuration for semantic chunking."""
    
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
    format: str = Field(description="Data format (json, sqlite, csv, etc.)")
    enabled: bool = Field(default=True, description="Whether to load this source")
    options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional format-specific options"
    )
    subset_config: Optional[SubsetConfig] = Field(
        default=None,
        description="Source-specific subset configuration"
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
        description="Normalize feature arrays"
    )
    deduplicate_features: bool = Field(
        default=True,
        description="Remove duplicate features"
    )
    sort_features: bool = Field(
        default=True,
        description="Sort features alphabetically"
    )
    add_derived_fields: bool = Field(
        default=True,
        description="Add computed fields"
    )
    calculate_price_per_sqft: bool = Field(
        default=True,
        description="Calculate price per square foot"
    )
    calculate_days_on_market: bool = Field(
        default=True,
        description="Calculate days on market"
    )
    quality_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum quality score threshold"
    )
    min_required_fields: int = Field(
        default=5,
        description="Minimum required fields for quality"
    )
    validate_addresses: bool = Field(
        default=True,
        description="Validate address completeness"
    )


class EmbeddingConfig(BaseModel):
    """Embedding generation configuration."""
    
    provider: ProviderType = Field(
        default=ProviderType.VOYAGE,
        description="Embedding provider to use"
    )
    models: Optional[ModelsConfig] = Field(
        default=None,
        description="Model configurations by provider"
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
    rate_limit_delay: float = Field(
        default=0.0,
        ge=0.0,
        description="Delay between API calls in seconds"
    )
    skip_existing: bool = Field(
        default=False,
        description="Skip if embeddings already exist"
    )
    force_regenerate: bool = Field(
        default=False,
        description="Force regeneration even if exists"
    )
    process_empty_text: bool = Field(
        default=False,
        description="Process records with empty text"
    )
    
    def get_model_config(self) -> Optional[ModelConfig]:
        """Get the model configuration for the selected provider."""
        if not self.models:
            return None
        
        provider_map = {
            ProviderType.VOYAGE: self.models.voyage,
            ProviderType.OLLAMA: self.models.ollama,
            ProviderType.OPENAI: self.models.openai,
            ProviderType.GEMINI: self.models.gemini,
        }
        return provider_map.get(self.provider)


class ChunkingConfig(BaseModel):
    """Text chunking configuration."""
    
    enabled: bool = Field(
        default=True,
        description="Enable text chunking"
    )
    method: ChunkingMethod = Field(
        default=ChunkingMethod.SIMPLE,
        description="Chunking method to use"
    )
    chunk_size: int = Field(
        default=512,
        gt=0,
        description="Maximum chunk size"
    )
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        description="Overlap between chunks"
    )
    respect_sentence_boundaries: bool = Field(
        default=True,
        description="Respect sentence boundaries when chunking"
    )
    min_chunk_size: int = Field(
        default=100,
        gt=0,
        description="Minimum chunk size"
    )
    max_chunk_size: int = Field(
        default=1000,
        gt=0,
        description="Maximum chunk size"
    )
    semantic: Optional[SemanticChunkingConfig] = Field(
        default=None,
        description="Semantic chunking configuration"
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
        description="Enable data quality checks"
    )
    min_quality_score: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum quality score threshold"
    )
    drop_low_quality: bool = Field(
        default=False,
        description="Drop records below quality threshold"
    )
    cache_intermediate_results: bool = Field(
        default=False,
        description="Cache intermediate DataFrames"
    )
    checkpoint_interval: int = Field(
        default=1000,
        gt=0,
        description="Checkpoint interval for fault tolerance"
    )
    parallel_tasks: int = Field(
        default=4,
        gt=0,
        description="Number of parallel tasks"
    )
    broadcast_join_threshold: int = Field(
        default=10485760,
        description="Broadcast join threshold in bytes"
    )
    adaptive_execution: bool = Field(
        default=True,
        description="Enable adaptive query execution"
    )
    continue_on_error: bool = Field(
        default=True,
        description="Continue processing on errors"
    )
    max_error_percentage: float = Field(
        default=10.0,
        ge=0.0,
        le=100.0,
        description="Maximum error percentage before stopping"
    )


class PartitioningConfig(BaseModel):
    """Output partitioning configuration."""
    
    enabled: bool = Field(
        default=True,
        description="Enable output partitioning"
    )
    columns: List[str] = Field(
        default_factory=lambda: ["source_entity", "state"],
        description="Partitioning columns"
    )
    max_partitions: int = Field(
        default=100,
        gt=0,
        description="Maximum number of partitions"
    )


class OutputConfig(BaseModel):
    """Output configuration."""
    
    format: OutputFormat = Field(
        default=OutputFormat.PARQUET,
        description="Output format"
    )
    path: str = Field(
        default="data/processed/entity_datasets",
        description="Output path"
    )
    partitioning: PartitioningConfig = Field(
        default_factory=PartitioningConfig,
        description="Partitioning configuration"
    )
    compression: str = Field(
        default="snappy",
        description="Compression codec"
    )
    overwrite: bool = Field(
        default=True,
        description="Overwrite existing output"
    )
    coalesce_files: bool = Field(
        default=True,
        description="Coalesce small files"
    )
    target_file_size_mb: int = Field(
        default=128,
        gt=0,
        description="Target file size in MB"
    )
    merge_schema: bool = Field(
        default=True,
        description="Merge schema on write"
    )
    enforce_schema: bool = Field(
        default=False,
        description="Enforce strict schema"
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
    console: bool = Field(
        default=True,
        description="Enable console logging"
    )
    file: Optional[str] = Field(
        default="logs/pipeline.log",
        description="Log file path"
    )
    max_file_size_mb: int = Field(
        default=100,
        gt=0,
        description="Maximum log file size in MB"
    )
    backup_count: int = Field(
        default=5,
        ge=0,
        description="Number of backup log files"
    )
    log_execution_time: bool = Field(
        default=True,
        description="Log execution times"
    )
    log_memory_usage: bool = Field(
        default=True,
        description="Log memory usage"
    )
    log_record_counts: bool = Field(
        default=True,
        description="Log record counts"
    )
    
    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}")
        return v.upper()


class MonitoringConfig(BaseModel):
    """Configuration for monitoring and metrics."""
    
    enabled: bool = Field(
        default=True,
        description="Enable monitoring"
    )
    metrics_interval_seconds: int = Field(
        default=10,
        description="Metrics collection interval"
    )
    track_metrics: List[str] = Field(
        default_factory=lambda: [
            "records_processed",
            "embeddings_generated",
            "processing_time",
            "memory_usage",
            "error_rate"
        ],
        description="Metrics to track"
    )
    alerts: Dict[str, Union[int, float]] = Field(
        default_factory=lambda: {
            "max_memory_usage_gb": 8,
            "max_processing_time_minutes": 30,
            "max_error_rate_percentage": 5
        },
        description="Alert thresholds"
    )


class DevelopmentConfig(BaseModel):
    """Configuration for development and testing."""
    
    test_mode: bool = Field(
        default=False,
        description="Enable test mode with minimal data"
    )
    test_record_limit: int = Field(
        default=10,
        description="Record limit in test mode"
    )
    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    verbose_logging: bool = Field(
        default=False,
        description="Enable verbose logging"
    )
    save_intermediate_results: bool = Field(
        default=False,
        description="Save intermediate processing results"
    )
    enable_profiling: bool = Field(
        default=False,
        description="Enable performance profiling"
    )
    profile_output_path: str = Field(
        default="profiles/",
        description="Path for profiling output"
    )
    validate_inputs: bool = Field(
        default=True,
        description="Validate input data"
    )
    validate_outputs: bool = Field(
        default=True,
        description="Validate output data"
    )
    schema_inference_sample_size: int = Field(
        default=1000,
        description="Sample size for schema inference"
    )


class MetadataConfig(BaseModel):
    """Pipeline metadata configuration."""
    
    name: str = Field(
        default="real_estate_data_pipeline",
        description="Pipeline name"
    )
    version: str = Field(
        default="1.0.0",
        description="Pipeline version"
    )
    description: str = Field(
        default="Apache Spark-based data pipeline for real estate and Wikipedia data processing",
        description="Pipeline description"
    )


class FeatureFlagsConfig(BaseModel):
    """Feature flags for experimental features."""
    
    enable_smart_chunking: bool = Field(
        default=False,
        description="Enable intelligent text chunking"
    )
    enable_adaptive_batching: bool = Field(
        default=False,
        description="Enable adaptive batch sizing"
    )
    enable_incremental_processing: bool = Field(
        default=False,
        description="Enable incremental data processing"
    )
    enable_data_lineage_tracking: bool = Field(
        default=False,
        description="Enable data lineage tracking"
    )
    enable_cost_optimization: bool = Field(
        default=True,
        description="Enable cost optimization features"
    )


class ModelComparisonConfig(BaseModel):
    """Configuration for model comparison and A/B testing."""
    
    enabled: bool = Field(
        default=False,
        description="Enable model comparison"
    )
    models_to_compare: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of models to compare"
    )
    comparison_metrics: List[str] = Field(
        default_factory=lambda: [
            "embedding_quality",
            "processing_speed",
            "cost_per_embedding"
        ],
        description="Metrics for comparison"
    )
    output_comparison_report: bool = Field(
        default=True,
        description="Generate comparison report"
    )
    report_path: str = Field(
        default="reports/model_comparison.json",
        description="Path for comparison report"
    )


class Neo4jConfig(BaseModel):
    """Neo4j writer configuration."""
    
    enabled: bool = Field(
        default=True,
        description="Whether Neo4j writer is enabled"
    )
    uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI"
    )
    username: str = Field(
        default="neo4j",
        description="Neo4j username"
    )
    password: Optional[str] = Field(
        default=None,
        description="Neo4j password (can use ${NEO4J_PASSWORD} syntax)"
    )
    database: str = Field(
        default="neo4j",
        description="Neo4j database name"
    )
    transaction_size: int = Field(
        default=1000,
        gt=0,
        description="Transaction batch size"
    )
    clear_before_write: bool = Field(
        default=True,
        description="Clear database before writing"
    )
    
    def get_password(self) -> Optional[str]:
        """Resolve password from environment if needed."""
        if self.password and self.password.startswith("${") and self.password.endswith("}"):
            env_var = self.password[2:-1]
            return os.getenv(env_var)
        return self.password


class ElasticsearchConfig(BaseModel):
    """Elasticsearch writer configuration."""
    
    enabled: bool = Field(
        default=True,
        description="Whether Elasticsearch writer is enabled"
    )
    hosts: List[str] = Field(
        default_factory=lambda: ["localhost:9200"],
        description="Elasticsearch host addresses"
    )
    username: Optional[str] = Field(
        default=None,
        description="Elasticsearch username"
    )
    password: Optional[str] = Field(
        default=None,
        description="Elasticsearch password (can use ${ES_PASSWORD} syntax)"
    )
    index_prefix: str = Field(
        default="realestate",
        description="Prefix for index names"
    )
    bulk_size: int = Field(
        default=500,
        gt=0,
        description="Bulk operation size"
    )
    clear_before_write: bool = Field(
        default=True,
        description="Clear indices before writing"
    )
    
    def get_password(self) -> Optional[str]:
        """Resolve password from environment if needed."""
        if self.password and self.password.startswith("${") and self.password.endswith("}"):
            env_var = self.password[2:-1]
            return os.getenv(env_var)
        return self.password


class ParquetWriterConfig(BaseModel):
    """Enhanced Parquet writer configuration."""
    
    enabled: bool = Field(
        default=True,
        description="Whether Parquet writer is enabled"
    )
    path: str = Field(
        default="data/processed/entity_datasets",
        description="Output path for Parquet files"
    )
    partitioning_columns: List[str] = Field(
        default_factory=lambda: ["source_entity"],
        description="Columns to use for partitioning"
    )
    compression: str = Field(
        default="snappy",
        description="Compression codec"
    )
    mode: str = Field(
        default="overwrite",
        description="Write mode (overwrite, append, etc.)"
    )


class OutputDestinationsConfig(BaseModel):
    """Multi-destination output configuration."""
    
    enabled_destinations: List[str] = Field(
        default_factory=lambda: ["parquet"],
        description="List of enabled output destinations"
    )
    parquet: ParquetWriterConfig = Field(
        default_factory=ParquetWriterConfig,
        description="Parquet writer configuration"
    )
    neo4j: Neo4jConfig = Field(
        default_factory=Neo4jConfig,
        description="Neo4j writer configuration"
    )
    elasticsearch: ElasticsearchConfig = Field(
        default_factory=ElasticsearchConfig,
        description="Elasticsearch writer configuration"
    )


class EnvironmentConfig(BaseModel):
    """Environment-specific configuration overrides."""
    
    spark: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Spark configuration overrides"
    )
    data_subset: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Data subset configuration overrides"
    )
    embedding: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Embedding configuration overrides"
    )
    output: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Output configuration overrides"
    )
    logging: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Logging configuration overrides"
    )


class PipelineConfig(BaseModel):
    """Main pipeline configuration."""
    
    # Metadata
    metadata: MetadataConfig = Field(
        default_factory=MetadataConfig,
        description="Pipeline metadata"
    )
    
    # Core configurations
    spark: SparkConfig = Field(
        default_factory=SparkConfig,
        description="Spark configuration"
    )
    data_subset: DataSubsetConfig = Field(
        default_factory=DataSubsetConfig,
        description="Data subsetting configuration for testing"
    )
    data_sources: Dict[str, DataSourceConfig] = Field(
        default_factory=dict,
        description="Data source configurations"
    )
    enrichment: EnrichmentConfig = Field(
        default_factory=EnrichmentConfig,
        description="Data enrichment configuration"
    )
    embedding: EmbeddingConfig = Field(
        default_factory=EmbeddingConfig,
        description="Embedding generation configuration"
    )
    chunking: ChunkingConfig = Field(
        default_factory=ChunkingConfig,
        description="Text chunking configuration"
    )
    processing: ProcessingConfig = Field(
        default_factory=ProcessingConfig,
        description="Processing configuration"
    )
    output: OutputConfig = Field(
        default_factory=OutputConfig,
        description="Output configuration"
    )
    output_destinations: OutputDestinationsConfig = Field(
        default_factory=OutputDestinationsConfig,
        description="Multi-destination output configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )
    monitoring: MonitoringConfig = Field(
        default_factory=MonitoringConfig,
        description="Monitoring configuration"
    )
    development: DevelopmentConfig = Field(
        default_factory=DevelopmentConfig,
        description="Development and testing configuration"
    )
    
    # Advanced features
    feature_flags: FeatureFlagsConfig = Field(
        default_factory=FeatureFlagsConfig,
        description="Feature flags"
    )
    model_comparison: ModelComparisonConfig = Field(
        default_factory=ModelComparisonConfig,
        description="Model comparison configuration"
    )
    
    # Environment-specific configurations
    environments: Dict[str, EnvironmentConfig] = Field(
        default_factory=dict,
        description="Environment-specific overrides"
    )
    
    
    def apply_environment_overrides(self, environment: str) -> None:
        """Apply environment-specific configuration overrides."""
        if environment in self.environments:
            env_config = self.environments[environment]
            
            # Apply overrides for each configuration section
            if env_config.spark:
                for key, value in env_config.spark.items():
                    setattr(self.spark, key, value)
            
            if env_config.data_subset:
                for key, value in env_config.data_subset.items():
                    setattr(self.data_subset, key, value)
            
            if env_config.embedding:
                for key, value in env_config.embedding.items():
                    setattr(self.embedding, key, value)
            
            if env_config.output:
                for key, value in env_config.output.items():
                    setattr(self.output, key, value)
            
            if env_config.logging:
                for key, value in env_config.logging.items():
                    setattr(self.logging, key, value)