"""
Configuration management for the common ingestion module.

Uses YAML configuration with Pydantic models for type-safe configuration.
Follows the pattern from common_embeddings module.
"""

import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator

from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class DataPaths(BaseModel):
    """Configuration for data source paths."""
    
    # Base path for the project
    base_path: Path = Field(
        default=Path("/Users/ryanknight/projects/temporal/real_estate_ai_search"),
        description="Base path for the project"
    )
    
    # Property data paths
    property_data_dir: Path = Field(
        default=Path("real_estate_data"),
        description="Directory containing property JSON files"
    )
    
    # Wikipedia data paths
    wikipedia_db_path: Path = Field(
        default=Path("data/wikipedia/wikipedia.db"),
        description="Path to Wikipedia SQLite database"
    )
    wikipedia_pages_dir: Path = Field(
        default=Path("data/wikipedia/pages"),
        description="Directory containing Wikipedia HTML pages"
    )
    
    @field_validator('base_path')
    @classmethod
    def validate_base_path(cls, v: Path) -> Path:
        """Ensure base path exists."""
        if not v.exists():
            logger.warning(f"Base path does not exist: {v}")
        return v
    
    def get_property_data_path(self) -> Path:
        """Get full path to property data directory."""
        if self.property_data_dir.is_absolute():
            return self.property_data_dir
        return self.base_path / self.property_data_dir
    
    def get_wikipedia_db_path(self) -> Path:
        """Get full path to Wikipedia database."""
        if self.wikipedia_db_path.is_absolute():
            return self.wikipedia_db_path
        return self.base_path / self.wikipedia_db_path
    
    def get_wikipedia_pages_path(self) -> Path:
        """Get full path to Wikipedia pages directory."""
        if self.wikipedia_pages_dir.is_absolute():
            return self.wikipedia_pages_dir
        return self.base_path / self.wikipedia_pages_dir


class ChromaDBConfig(BaseModel):
    """Configuration for ChromaDB connection and collections."""
    
    host: str = Field(
        default="localhost",
        description="ChromaDB host"
    )
    port: int = Field(
        default=8000,
        description="ChromaDB port"
    )
    persist_directory: Optional[Path] = Field(
        default=Path("./data/common_embeddings"),
        description="Directory for persistent ChromaDB storage"
    )
    
    # Collection naming patterns
    property_collection_pattern: str = Field(
        default="property_{model}_v{version}",
        description="Pattern for property embedding collections"
    )
    wikipedia_collection_pattern: str = Field(
        default="wikipedia_{model}_v{version}",
        description="Pattern for Wikipedia embedding collections"
    )
    neighborhood_collection_pattern: str = Field(
        default="neighborhood_{model}_v{version}",
        description="Pattern for neighborhood embedding collections"
    )
    
    # Default models
    default_embedding_model: str = Field(
        default="nomic-embed-text",
        description="Default embedding model name"
    )
    default_provider: str = Field(
        default="ollama",
        description="Default embedding provider"
    )
    
    def get_property_collection_name(self, model: Optional[str] = None, version: str = "1") -> str:
        """Generate property collection name."""
        model = model or self.default_embedding_model
        model_safe = model.replace("-", "_").replace(".", "_")
        return self.property_collection_pattern.format(model=model_safe, version=version)
    
    def get_wikipedia_collection_name(self, model: Optional[str] = None, version: str = "1") -> str:
        """Generate Wikipedia collection name."""
        model = model or self.default_embedding_model
        model_safe = model.replace("-", "_").replace(".", "_")
        return self.wikipedia_collection_pattern.format(model=model_safe, version=version)
    
    def get_neighborhood_collection_name(self, model: Optional[str] = None, version: str = "1") -> str:
        """Generate neighborhood collection name."""
        model = model or self.default_embedding_model
        model_safe = model.replace("-", "_").replace(".", "_")
        return self.neighborhood_collection_pattern.format(model=model_safe, version=version)


class EnrichmentConfig(BaseModel):
    """Configuration for data enrichment operations."""
    
    # City name mappings
    city_abbreviations: Dict[str, str] = Field(
        default={
            "SF": "San Francisco",
            "LA": "Los Angeles",
            "NYC": "New York City",
            "NY": "New York",
            "PC": "Park City",
            "SLC": "Salt Lake City",
            "LV": "Las Vegas",
        },
        description="City abbreviation to full name mappings"
    )
    
    # State code mappings
    state_codes: Dict[str, str] = Field(
        default={
            "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
            "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
            "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
            "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
            "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
            "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
            "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
            "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
            "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
            "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
            "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
            "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
            "WI": "Wisconsin", "WY": "Wyoming"
        },
        description="State code to full name mappings"
    )
    
    # Feature normalization
    normalize_features_to_lowercase: bool = Field(
        default=True,
        description="Convert all features to lowercase"
    )
    deduplicate_features: bool = Field(
        default=True,
        description="Remove duplicate features"
    )
    sort_features: bool = Field(
        default=True,
        description="Sort features alphabetically"
    )


class ProcessingConfig(BaseModel):
    """Configuration for batch processing and performance."""
    
    batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Batch size for processing"
    )
    max_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Maximum parallel workers"
    )
    show_progress: bool = Field(
        default=True,
        description="Show progress indicators"
    )


class LoggingConfig(BaseModel):
    """Configuration for logging."""
    
    level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    track_operations: bool = Field(
        default=True,
        description="Enable operation tracking"
    )
    
    @field_validator('level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper


class MetadataConfig(BaseModel):
    """Configuration for module metadata."""
    
    version: str = Field(
        default="0.1.0",
        description="Module version"
    )
    description: str = Field(
        default="Common data ingestion and enrichment module",
        description="Module description"
    )


class Settings(BaseModel):
    """
    Main configuration settings for the common ingestion module.
    
    Loaded from YAML configuration file with support for environment
    variable overrides.
    """
    
    # Sub-configurations
    data_paths: DataPaths = Field(
        default_factory=DataPaths,
        description="Data source paths configuration"
    )
    chromadb: ChromaDBConfig = Field(
        default_factory=ChromaDBConfig,
        description="ChromaDB configuration"
    )
    enrichment: EnrichmentConfig = Field(
        default_factory=EnrichmentConfig,
        description="Data enrichment configuration"
    )
    
    # Logging configuration
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )
    
    # Processing configuration
    processing: ProcessingConfig = Field(
        default_factory=ProcessingConfig,
        description="Processing and performance configuration"
    )
    
    # Module metadata
    metadata: MetadataConfig = Field(
        default_factory=MetadataConfig,
        description="Module metadata"
    )
    
    @classmethod
    def from_yaml(cls, config_path: str = "common_ingest/config.yaml") -> "Settings":
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Validated Settings instance
        """
        config_file = Path(config_path)
        if not config_file.exists():
            # Return default config if file doesn't exist
            logger.warning(f"Config file not found at {config_path}, using defaults")
            return cls()
        
        try:
            with open(config_file, 'r') as f:
                data = yaml.safe_load(f)
            
            return cls(**data) if data else cls()
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            return cls()
    
    def to_yaml(self, config_path: str = "common_ingest/config.yaml") -> None:
        """
        Save configuration to YAML file.
        
        Args:
            config_path: Path to save YAML configuration
        """
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            yaml.safe_dump(
                self.model_dump(exclude_unset=True),
                f,
                default_flow_style=False,
                sort_keys=False
            )
    


# Singleton instance of settings
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the singleton settings instance.
    
    Returns:
        Settings instance loaded from YAML config
    """
    global _settings
    if _settings is None:
        _settings = Settings.from_yaml()
        logger.info(f"Loaded settings for common_ingest v{_settings.metadata.version}")
    return _settings


def reset_settings() -> None:
    """Reset the settings singleton (mainly for testing)."""
    global _settings
    _settings = None