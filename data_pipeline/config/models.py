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


class WikipediaConfig(BaseModel):
    """Wikipedia data source configuration."""
    path: str
    enabled: bool = True


class LocationsConfig(BaseModel):
    """Locations data source configuration."""
    path: str
    enabled: bool = True


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
    
    # Data sources - Simple lists of paths
    properties: List[str] = Field(
        default_factory=lambda: [
            "real_estate_data/properties_sf.json",
            "real_estate_data/properties_pc.json"
        ]
    )
    
    neighborhoods: List[str] = Field(
        default_factory=lambda: [
            "real_estate_data/neighborhoods_sf.json",
            "real_estate_data/neighborhoods_pc.json"
        ]
    )
    
    wikipedia: WikipediaConfig = Field(
        default_factory=lambda: WikipediaConfig(
            path="data/wikipedia/wikipedia.db",
            enabled=True
        )
    )
    
    locations: LocationsConfig = Field(
        default_factory=lambda: LocationsConfig(
            path="real_estate_data/locations.json",
            enabled=True
        )
    )
    
    # Embedding configuration
    provider: str = Field(default="voyage")
    batch_size: int = Field(default=100, gt=0)
    
    # Output configuration
    path: str = Field(default="data/processed")
    format: str = Field(default="parquet")
    enabled_destinations: List[str] = Field(default_factory=lambda: ["parquet"])
    
    # Writer-specific configurations
    base_path: str = Field(default="data/processed")