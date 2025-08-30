"""
Pydantic configuration models for the data pipeline.

This module defines all configuration structures using Pydantic models
with validation and clear documentation.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    VOYAGE = "voyage"
    OPENAI = "openai"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    MOCK = "mock"


class OutputFormat(str, Enum):
    """Supported output formats."""
    PARQUET = "parquet"
    JSON = "json"
    CSV = "csv"


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
    driver_memory: str = Field(
        default="4g",
        description="Driver memory allocation"
    )
    executor_memory: str = Field(
        default="2g",
        description="Executor memory allocation"
    )
    
    def to_spark_conf(self) -> Dict[str, str]:
        """Convert to Spark configuration dictionary."""
        conf = {}
        
        # Add connector JARs if they exist
        jar_paths = []
        
        # Neo4j connector JAR (use 2.12 version for Spark 3.5 compatibility)
        neo4j_jar_path = "lib/neo4j-connector-apache-spark_2.12-5.3.0_for_spark_3.jar"
        if os.path.exists(neo4j_jar_path):
            jar_paths.append(neo4j_jar_path)
        
        # Elasticsearch connector JAR (Spark 3.x + Scala 2.12 compatible)
        es_jar_path = "lib/elasticsearch-spark-30_2.12-9.0.0.jar"
        if os.path.exists(es_jar_path):
            jar_paths.append(es_jar_path)
        
        if jar_paths:
            conf["spark.jars"] = ",".join(jar_paths)
        
        if not self.master.startswith("local"):
            conf["spark.driver.memory"] = self.driver_memory
            conf["spark.executor.memory"] = self.executor_memory
        return conf


class DataSourceConfig(BaseModel):
    """Configuration for data sources."""
    
    properties_files: List[str] = Field(
        default_factory=lambda: [
            "real_estate_data/properties_sf.json",
            "real_estate_data/properties_pc.json"
        ],
        description="List of property data files"
    )
    neighborhoods_files: List[str] = Field(
        default_factory=lambda: [
            "real_estate_data/neighborhoods_sf.json",
            "real_estate_data/neighborhoods_pc.json"
        ],
        description="List of neighborhood data files"
    )
    wikipedia_db_path: str = Field(
        default="data/wikipedia/wikipedia.db",
        description="Path to Wikipedia SQLite database"
    )
    locations_file: str = Field(
        default="real_estate_data/locations.json",
        description="Path to locations data file"
    )
    
    @field_validator("properties_files", "neighborhoods_files")
    @classmethod
    def validate_file_lists(cls, v: List[str]) -> List[str]:
        """Ensure file lists are not empty."""
        if not v:
            raise ValueError("File list cannot be empty")
        return v


class ParquetOutputConfig(BaseModel):
    """Configuration for Parquet output."""
    
    base_path: str = Field(
        default="data/processed",
        description="Base path for Parquet files"
    )
    compression: str = Field(
        default="snappy",
        description="Compression codec for Parquet files"
    )
    partition_columns: Optional[List[str]] = Field(
        default=None,
        description="Columns to use for partitioning"
    )


class Neo4jOutputConfig(BaseModel):
    """Configuration for Neo4j output."""
    
    uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI"
    )
    database: str = Field(
        default="neo4j",
        description="Neo4j database name"
    )
    username: str = Field(
        default="neo4j",
        description="Neo4j username"
    )
    # Password comes from environment variable NEO4J_PASSWORD


class ElasticsearchOutputConfig(BaseModel):
    """Configuration for Elasticsearch output."""
    
    hosts: List[str] = Field(
        default_factory=lambda: ["localhost:9200"],
        description="Elasticsearch host addresses"
    )
    username: Optional[str] = Field(
        default=None,
        description="Elasticsearch username"
    )
    bulk_size: int = Field(
        default=1000,
        description="Bulk index batch size"
    )
    # Password comes from environment variable ES_PASSWORD


class OutputConfig(BaseModel):
    """Configuration for all output destinations."""
    
    enabled_destinations: List[str] = Field(
        default_factory=lambda: ["parquet"],
        description="List of enabled output destinations"
    )
    parquet: ParquetOutputConfig = Field(
        default_factory=ParquetOutputConfig,
        description="Parquet output configuration"
    )
    neo4j: Optional[Neo4jOutputConfig] = Field(
        default=None,
        description="Neo4j output configuration"
    )
    elasticsearch: Optional[ElasticsearchOutputConfig] = Field(
        default=None,
        description="Elasticsearch output configuration"
    )
    
    @field_validator("enabled_destinations")
    @classmethod
    def validate_destinations(cls, v: List[str]) -> List[str]:
        """Validate that enabled destinations are supported."""
        valid_destinations = {"parquet", "neo4j", "elasticsearch"}
        invalid = set(v) - valid_destinations
        if invalid:
            raise ValueError(f"Invalid destinations: {invalid}")
        return v
    
    def get_neo4j_spark_conf(self) -> Dict[str, str]:
        """Get Neo4j Spark configuration if enabled."""
        if "neo4j" not in self.enabled_destinations or not self.neo4j:
            return {}
        
        return {
            "neo4j.url": self.neo4j.uri,
            "neo4j.authentication.basic.username": self.neo4j.username,
            "neo4j.authentication.basic.password": os.environ.get('NEO4J_PASSWORD', ''),
            "neo4j.database": self.neo4j.database
        }
    
    def get_elasticsearch_spark_conf(self) -> Dict[str, str]:
        """Get Elasticsearch Spark configuration if enabled."""
        if "elasticsearch" not in self.enabled_destinations or not self.elasticsearch:
            return {}
        
        conf = {
            "es.nodes": ",".join(self.elasticsearch.hosts),
            "es.batch.size.entries": str(self.elasticsearch.bulk_size),
            "es.write.operation": "upsert",
            "es.mapping.id": "id",
            "es.batch.write.retry.count": "3",
            "es.batch.write.retry.wait": "10s",
            "es.http.timeout": "2m",
            "es.http.retries": "3",
            "es.scroll.keepalive": "10m",
            "es.error.handler.log.error.message": "true",
            "es.error.handler.log.error.reason": "true"
        }
        
        if self.elasticsearch.username:
            conf["es.net.http.auth.user"] = self.elasticsearch.username
            password = os.environ.get('ES_PASSWORD', '')
            if password:
                conf["es.net.http.auth.pass"] = password
        
        return conf


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""
    
    provider: EmbeddingProvider = Field(
        default=EmbeddingProvider.MOCK,
        description="Embedding provider to use"
    )
    model_name: Optional[str] = Field(
        default=None,
        description="Model name for the embedding provider"
    )
    batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Batch size for embedding generation"
    )
    dimension: Optional[int] = Field(
        default=None,
        description="Embedding vector dimension"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for the embedding provider (loaded from environment)"
    )
    
    @model_validator(mode='after')
    def load_api_key_from_environment(self):
        """Load API key from environment variables at startup ONLY if not already set."""
        # If api_key is already set (e.g., from deserialization), don't check environment
        if self.api_key:
            return self
            
        # Only load from environment if not set (initial config load)
        if self.provider == EmbeddingProvider.VOYAGE:
            self.api_key = os.environ.get("VOYAGE_API_KEY")
            if not self.api_key:
                raise ValueError("VOYAGE_API_KEY environment variable required for Voyage provider")
        elif self.provider == EmbeddingProvider.OPENAI:
            self.api_key = os.environ.get("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY environment variable required for OpenAI provider")
        elif self.provider == EmbeddingProvider.GEMINI:
            self.api_key = os.environ.get("GEMINI_API_KEY")
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY environment variable required for Gemini provider")
        return self


class PipelineConfig(BaseModel):
    """Root configuration model for the data pipeline."""
    
    name: str = Field(
        default="real_estate_data_pipeline",
        description="Pipeline name"
    )
    version: str = Field(
        default="1.0.0",
        description="Pipeline version"
    )
    sample_size: Optional[int] = Field(
        default=None,
        ge=1,
        description="Number of records to sample from each source (for testing)"
    )
    spark: SparkConfig = Field(
        default_factory=SparkConfig,
        description="Spark configuration"
    )
    data_sources: DataSourceConfig = Field(
        default_factory=DataSourceConfig,
        description="Data source configuration"
    )
    output: OutputConfig = Field(
        default_factory=OutputConfig,
        description="Output configuration"
    )
    embedding: EmbeddingConfig = Field(
        default_factory=EmbeddingConfig,
        description="Embedding configuration"
    )
    
    @field_validator("sample_size")
    @classmethod
    def validate_sample_size(cls, v: Optional[int]) -> Optional[int]:
        """Validate sample size if provided."""
        if v is not None and v < 1:
            raise ValueError("Sample size must be positive")
        return v
    
    @model_validator(mode='after')
    def validate_output_configs(self):
        """Ensure output configurations exist for enabled destinations."""
        if "neo4j" in self.output.enabled_destinations and not self.output.neo4j:
            self.output.neo4j = Neo4jOutputConfig()
        if "elasticsearch" in self.output.enabled_destinations and not self.output.elasticsearch:
            self.output.elasticsearch = ElasticsearchOutputConfig()
        return self
    
    def get_spark_configs(self) -> Dict[str, str]:
        """Get all Spark configuration including Neo4j and Elasticsearch if enabled."""
        configs = self.spark.to_spark_conf()
        configs.update(self.output.get_neo4j_spark_conf())
        configs.update(self.output.get_elasticsearch_spark_conf())
        return configs
    
    def resolve_paths(self, base_dir: Optional[Path] = None) -> None:
        """
        Resolve relative paths to absolute paths.
        
        Args:
            base_dir: Base directory for relative paths (defaults to current directory)
        """
        if base_dir is None:
            base_dir = Path.cwd()
        
        # Resolve data source paths
        self.data_sources.properties_files = [
            str(base_dir / p) if not Path(p).is_absolute() else p
            for p in self.data_sources.properties_files
        ]
        self.data_sources.neighborhoods_files = [
            str(base_dir / p) if not Path(p).is_absolute() else p
            for p in self.data_sources.neighborhoods_files
        ]
        self.data_sources.wikipedia_db_path = (
            str(base_dir / self.data_sources.wikipedia_db_path)
            if not Path(self.data_sources.wikipedia_db_path).is_absolute()
            else self.data_sources.wikipedia_db_path
        )
        self.data_sources.locations_file = (
            str(base_dir / self.data_sources.locations_file)
            if not Path(self.data_sources.locations_file).is_absolute()
            else self.data_sources.locations_file
        )
        
        # Resolve output paths
        if not Path(self.output.parquet.base_path).is_absolute():
            self.output.parquet.base_path = str(base_dir / self.output.parquet.base_path)