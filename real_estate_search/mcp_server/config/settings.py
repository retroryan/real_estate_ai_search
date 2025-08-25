"""
MCP Server configuration using Pydantic settings.
Clean, type-safe configuration management.
"""

from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum


class Environment(str, Enum):
    """Application environment."""
    development = "development"
    testing = "testing"
    production = "production"
    demo = "demo"


class ElasticsearchSettings(BaseSettings):
    """Elasticsearch configuration."""
    
    host: str = Field(default="localhost", description="Elasticsearch host")
    port: int = Field(default=9200, description="Elasticsearch port")
    index_name: str = Field(default="properties_demo", description="Index name for properties")
    refresh_on_write: bool = Field(default=True, description="Refresh index on write (demo mode)")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    
    @property
    def url(self) -> str:
        """Get full Elasticsearch URL."""
        return f"http://{self.host}:{self.port}"


class SearchSettings(BaseSettings):
    """Search configuration."""
    
    default_size: int = Field(default=20, description="Default search result size")
    max_size: int = Field(default=100, description="Maximum search result size")
    enable_fuzzy: bool = Field(default=True, description="Enable fuzzy matching")
    
    # Boost factors for different fields
    boost_description: float = Field(default=2.0, description="Description field boost")
    boost_features: float = Field(default=1.5, description="Features field boost")
    boost_amenities: float = Field(default=1.5, description="Amenities field boost")
    boost_location: float = Field(default=1.8, description="Location field boost")


class EnrichmentSettings(BaseSettings):
    """Enrichment configuration."""
    
    wikipedia_enabled: bool = Field(default=True, description="Enable Wikipedia enrichment")
    wikipedia_cache_ttl: int = Field(default=3600, description="Wikipedia cache TTL in seconds")
    market_data_enabled: bool = Field(default=True, description="Enable market data enrichment")
    max_pois: int = Field(default=10, description="Maximum POIs to return")
    poi_radius_miles: float = Field(default=2.0, description="Default POI search radius")


class ServerSettings(BaseSettings):
    """MCP Server configuration."""
    
    name: str = Field(default="real-estate-search", description="Server name")
    version: str = Field(default="1.0.0", description="Server version")
    description: str = Field(
        default="AI-powered real estate search with Wikipedia enrichment",
        description="Server description"
    )
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=False, description="Auto-reload on code changes")


class DemoSettings(BaseSettings):
    """Demo mode configuration."""
    
    enabled: bool = Field(default=True, description="Enable demo mode")
    reset_on_startup: bool = Field(default=True, description="Reset data on startup")
    sample_data_path: str = Field(
        default="./data/demo_properties.json",
        description="Path to sample data"
    )
    enrich_on_load: bool = Field(default=True, description="Enrich data on load")
    max_demo_properties: int = Field(default=100, description="Maximum demo properties")


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False
    )
    
    # Environment
    environment: Environment = Field(
        default=Environment.demo,
        description="Application environment"
    )
    debug: bool = Field(default=False, description="Debug mode")
    
    # Sub-configurations
    elasticsearch: ElasticsearchSettings = Field(default_factory=ElasticsearchSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    enrichment: EnrichmentSettings = Field(default_factory=EnrichmentSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    demo: DemoSettings = Field(default_factory=DemoSettings)
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Logging format (json or text)")
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == Environment.development
    
    @property
    def is_demo(self) -> bool:
        """Check if running in demo mode."""
        return self.environment == Environment.demo or self.demo.enabled
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == Environment.production


# Create singleton settings instance
settings = Settings()