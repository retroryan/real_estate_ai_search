"""Configuration schemas and validation using Pydantic V2."""

from enum import Enum
from typing import Dict, Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Environment(str, Enum):
    """Pipeline environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LogLevel(str, Enum):
    """Log level options."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CompressionType(str, Enum):
    """Parquet compression types."""
    NONE = "none"
    SNAPPY = "snappy"
    GZIP = "gzip"
    LZ4 = "lz4"
    ZSTD = "zstd"


class MedallionTier(str, Enum):
    """Data quality tiers in medallion architecture."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class ProcessingMode(str, Enum):
    """Pipeline processing modes."""
    BATCH = "batch"
    INCREMENTAL = "incremental"
    FULL = "full"


class ValidationConfig(BaseModel):
    """Data validation configuration."""
    
    model_config = ConfigDict(strict=True)
    
    check_nulls: bool = Field(default=True, description="Check for null values")
    check_duplicates: bool = Field(default=True, description="Check for duplicate records")
    check_schema: bool = Field(default=True, description="Validate schema compliance")
    min_completeness: float = Field(default=0.9, ge=0, le=1, description="Minimum data completeness")
    max_error_rate: float = Field(default=0.01, ge=0, le=1, description="Maximum acceptable error rate")


class PerformanceConfig(BaseModel):
    """Performance tuning configuration."""
    
    model_config = ConfigDict(strict=True)
    
    chunk_size: int = Field(default=10000, gt=0, description="Processing chunk size")
    parallel_workers: int = Field(default=4, ge=1, description="Number of parallel workers")
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_ttl_seconds: int = Field(default=3600, gt=0, description="Cache TTL in seconds")
    memory_fraction: float = Field(default=0.8, gt=0, le=1, description="Fraction of memory to use")


class OutputSchema(BaseModel):
    """Output file schema configuration."""
    
    model_config = ConfigDict(strict=True)
    
    properties_columns: Dict[str, str] = Field(
        default_factory=lambda: {
            "listing_id": "string",
            "neighborhood_id": "string",
            "listing_price": "double",
            "bedrooms": "integer",
            "bathrooms": "double",
            "square_feet": "integer",
            "price_per_sqft": "double",
            "description_embedding": "list<double>",
        },
        description="Properties table schema"
    )
    
    neighborhoods_columns: Dict[str, str] = Field(
        default_factory=lambda: {
            "neighborhood_id": "string",
            "name": "string",
            "city": "string",
            "median_home_price": "double",
            "description_embedding": "list<double>",
        },
        description="Neighborhoods table schema"
    )
    
    wikipedia_columns: Dict[str, str] = Field(
        default_factory=lambda: {
            "page_id": "integer",
            "title": "string",
            "content": "string",
            "embedding": "list<double>",
        },
        description="Wikipedia articles table schema"
    )


class RuntimeConfig(BaseModel):
    """Runtime configuration that can be modified during execution."""
    
    model_config = ConfigDict(
        strict=True,
        validate_assignment=True
    )
    
    processing_mode: ProcessingMode = Field(default=ProcessingMode.BATCH)
    current_tier: Optional[MedallionTier] = None
    checkpoint_enabled: bool = Field(default=True)
    checkpoint_interval: int = Field(default=1000, gt=0)
    progress_tracking: bool = Field(default=True)
    
    # Runtime statistics
    records_processed: int = Field(default=0, ge=0)
    errors_encountered: int = Field(default=0, ge=0)
    warnings_raised: int = Field(default=0, ge=0)
    
    @field_validator('current_tier')
    @classmethod
    def validate_tier_progression(cls, v: Optional[MedallionTier], info) -> Optional[MedallionTier]:
        """Ensure medallion tier progression is valid."""
        # This would contain logic to ensure tiers progress correctly
        return v
    
    def increment_processed(self, count: int = 1) -> None:
        """Increment processed record counter."""
        self.records_processed += count
    
    def increment_errors(self, count: int = 1) -> None:
        """Increment error counter."""
        self.errors_encountered += count
    
    def increment_warnings(self, count: int = 1) -> None:
        """Increment warning counter."""
        self.warnings_raised += count