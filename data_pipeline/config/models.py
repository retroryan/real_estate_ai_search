"""
Single, unified Pydantic configuration model for the data pipeline.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ProviderType(str, Enum):
    """Embedding provider types."""
    VOYAGE = "voyage"
    OLLAMA = "ollama"  
    OPENAI = "openai"
    GEMINI = "gemini"
    MOCK = "mock"


class DataSourceConfig(BaseModel):
    """Configuration for a data source."""
    path: str
    format: str
    enabled: bool = True
    options: Dict[str, Any] = Field(default_factory=dict)


class PipelineConfig(BaseModel):
    """Unified pipeline configuration."""
    
    model_config = ConfigDict(extra='allow', validate_assignment=True)
    
    # Pipeline metadata
    name: str = Field(default="real_estate_data_pipeline")
    version: str = Field(default="1.0.0")
    
    # Spark configuration
    app_name: str = Field(default="RealEstateDataPipeline")
    master: str = Field(default="local[*]")
    memory: str = Field(default="4g")
    executor_memory: str = Field(default="2g")
    config: Dict[str, Any] = Field(default_factory=dict)
    
    # Data sources
    data_sources: Dict[str, DataSourceConfig] = Field(
        default_factory=lambda: {
            "properties_sf": DataSourceConfig(
                path="real_estate_data/properties_sf.json",
                format="json",
                enabled=True,
                options={"multiLine": True}
            ),
            "properties_pc": DataSourceConfig(
                path="real_estate_data/properties_pc.json",
                format="json",
                enabled=True,
                options={"multiLine": True}
            ),
            "wikipedia": DataSourceConfig(
                path="data/wikipedia/wikipedia.db",
                format="sqlite",
                enabled=True,
                options={"table": "page_summaries"}
            ),
            "neighborhoods_sf": DataSourceConfig(
                path="real_estate_data/neighborhoods_sf.json",
                format="json",
                enabled=True,
                options={"multiLine": True}
            ),
            "neighborhoods_pc": DataSourceConfig(
                path="real_estate_data/neighborhoods_pc.json",
                format="json",
                enabled=True,
                options={"multiLine": True}
            )
        }
    )
    
    # Embedding configuration
    provider: str = Field(default="voyage")
    batch_size: int = Field(default=100, gt=0)
    
    # Output configuration
    path: str = Field(default="data/processed")
    format: str = Field(default="parquet")
    enabled_destinations: List[str] = Field(default_factory=lambda: ["parquet"])
    
    # Processing
    cache_intermediate_results: bool = Field(default=False)
    parallel_tasks: int = Field(default=4, gt=0)
    enable_quality_checks: bool = Field(default=True)
    
    
    # Writer-specific configurations
    base_path: str = Field(default="data/processed")
    
    # Development/testing
    test_mode: bool = Field(default=False)
    debug_mode: bool = Field(default=False)