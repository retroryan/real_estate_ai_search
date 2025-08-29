"""Entity-specific configuration for pipeline processing."""

from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from enum import Enum

from squack_pipeline.models import EntityType


class ValidationLevel(str, Enum):
    """Validation strictness levels."""
    STRICT = "strict"
    NORMAL = "normal"
    LENIENT = "lenient"


class ValidationRules(BaseModel):
    """Validation rules for entity data."""
    
    required_fields: List[str] = Field(
        default_factory=list,
        description="Fields that must be present"
    )
    
    nullable_fields: List[str] = Field(
        default_factory=list,
        description="Fields that can be null"
    )
    
    validation_level: ValidationLevel = Field(
        default=ValidationLevel.NORMAL,
        description="Overall validation strictness"
    )
    
    min_record_size: int = Field(
        default=100,
        ge=0,
        description="Minimum bytes per record"
    )
    
    max_record_size: int = Field(
        default=1048576,  # 1MB
        gt=0,
        description="Maximum bytes per record"
    )
    
    allow_duplicates: bool = Field(
        default=False,
        description="Whether to allow duplicate records"
    )
    
    duplicate_key_fields: List[str] = Field(
        default_factory=list,
        description="Fields to use for duplicate detection"
    )


class ProcessingOptions(BaseModel):
    """Processing options for entity pipeline."""
    
    enable_deduplication: bool = Field(
        default=True,
        description="Enable deduplication in Silver tier"
    )
    
    enable_validation: bool = Field(
        default=True,
        description="Enable validation in Silver tier"
    )
    
    enable_enrichment: bool = Field(
        default=True,
        description="Enable enrichment in Gold tier"
    )
    
    enable_normalization: bool = Field(
        default=True,
        description="Enable field normalization"
    )
    
    batch_size: int = Field(
        default=1000,
        gt=0,
        description="Records per processing batch"
    )
    
    parallel_workers: int = Field(
        default=4,
        gt=0,
        le=32,
        description="Number of parallel workers"
    )
    
    error_threshold: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Maximum error rate before stopping"
    )
    
    sample_validation_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Fraction of records to validate in detail"
    )


class EntityEmbeddingConfig(BaseModel):
    """Embedding configuration for entity."""
    
    enabled: bool = Field(
        default=True,
        description="Whether to generate embeddings"
    )
    
    text_fields: List[str] = Field(
        default_factory=list,
        description="Fields to include in embedding text"
    )
    
    metadata_fields: List[str] = Field(
        default_factory=list,
        description="Fields to include as metadata"
    )
    
    excluded_metadata_keys: Set[str] = Field(
        default_factory=lambda: {
            "entity_id", "chunk_index", "processing_version"
        },
        description="Metadata keys to exclude from embeddings"
    )
    
    max_text_length: int = Field(
        default=8000,
        gt=0,
        description="Maximum text length for embedding"
    )
    
    chunking_enabled: bool = Field(
        default=False,
        description="Whether to chunk long documents"
    )
    
    chunk_size: int = Field(
        default=1000,
        gt=0,
        description="Size of text chunks if chunking enabled"
    )
    
    chunk_overlap: int = Field(
        default=200,
        ge=0,
        description="Overlap between chunks"
    )


class OutputPreferences(BaseModel):
    """Output preferences for entity processing."""
    
    output_format: str = Field(
        default="parquet",
        description="Output format (parquet, json, csv)"
    )
    
    compression: Optional[str] = Field(
        default="snappy",
        description="Compression type for output files"
    )
    
    include_embeddings: bool = Field(
        default=True,
        description="Include embeddings in output"
    )
    
    include_metadata: bool = Field(
        default=True,
        description="Include metadata in output"
    )
    
    partition_by: List[str] = Field(
        default_factory=list,
        description="Fields to partition output by"
    )
    
    sort_by: List[str] = Field(
        default_factory=list,
        description="Fields to sort output by"
    )
    
    max_file_size: int = Field(
        default=134217728,  # 128MB
        gt=0,
        description="Maximum output file size in bytes"
    )


class EntityConfig(BaseModel):
    """Complete configuration for an entity type."""
    
    entity_type: EntityType = Field(
        ...,
        description="Type of entity this config applies to"
    )
    
    validation_rules: ValidationRules = Field(
        default_factory=ValidationRules,
        description="Validation rules for the entity"
    )
    
    processing_options: ProcessingOptions = Field(
        default_factory=ProcessingOptions,
        description="Processing options for the entity"
    )
    
    embedding_config: EntityEmbeddingConfig = Field(
        default_factory=EntityEmbeddingConfig,
        description="Embedding configuration for the entity"
    )
    
    output_preferences: OutputPreferences = Field(
        default_factory=OutputPreferences,
        description="Output preferences for the entity"
    )
    
    custom_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Entity-specific custom settings"
    )


class PipelineEntityConfigs(BaseModel):
    """Configuration for all entities in the pipeline."""
    
    properties: EntityConfig = Field(
        default_factory=lambda: EntityConfig(
            entity_type=EntityType.PROPERTY,
            validation_rules=ValidationRules(
                required_fields=["listing_id", "price", "address"],
                duplicate_key_fields=["listing_id"]
            ),
            processing_options=ProcessingOptions(
                batch_size=500,
                enable_enrichment=True
            ),
            embedding_config=EntityEmbeddingConfig(
                text_fields=["description", "amenities", "features"],
                metadata_fields=["price", "bedrooms", "bathrooms", "square_feet"]
            ),
            output_preferences=OutputPreferences(
                partition_by=["city", "property_type"],
                sort_by=["price"]
            )
        ),
        description="Configuration for property entities"
    )
    
    neighborhoods: EntityConfig = Field(
        default_factory=lambda: EntityConfig(
            entity_type=EntityType.NEIGHBORHOOD,
            validation_rules=ValidationRules(
                required_fields=["neighborhood_id", "name", "city"],
                duplicate_key_fields=["neighborhood_id"]
            ),
            processing_options=ProcessingOptions(
                batch_size=100,
                enable_enrichment=True
            ),
            embedding_config=EntityEmbeddingConfig(
                text_fields=["name", "description", "characteristics"],
                metadata_fields=["population", "median_income", "walkability_score"]
            ),
            output_preferences=OutputPreferences(
                partition_by=["city", "state"],
                sort_by=["name"]
            )
        ),
        description="Configuration for neighborhood entities"
    )
    
    wikipedia: EntityConfig = Field(
        default_factory=lambda: EntityConfig(
            entity_type=EntityType.WIKIPEDIA,
            validation_rules=ValidationRules(
                required_fields=["page_id", "title", "content"],
                duplicate_key_fields=["page_id"]
            ),
            processing_options=ProcessingOptions(
                batch_size=200,
                enable_enrichment=False
            ),
            embedding_config=EntityEmbeddingConfig(
                text_fields=["title", "summary", "content"],
                metadata_fields=["categories", "relevance_score"],
                chunking_enabled=True,
                chunk_size=1500,
                chunk_overlap=300
            ),
            output_preferences=OutputPreferences(
                partition_by=["language"],
                sort_by=["relevance_score"]
            )
        ),
        description="Configuration for Wikipedia entities"
    )
    
    def get_config(self, entity_type: EntityType) -> EntityConfig:
        """Get configuration for a specific entity type.
        
        Args:
            entity_type: The entity type to get config for
            
        Returns:
            EntityConfig for the specified type
            
        Raises:
            ValueError: If entity type is not configured
        """
        if entity_type == EntityType.PROPERTY:
            return self.properties
        elif entity_type == EntityType.NEIGHBORHOOD:
            return self.neighborhoods
        elif entity_type == EntityType.WIKIPEDIA:
            return self.wikipedia
        else:
            raise ValueError(f"No configuration for entity type: {entity_type}")
    
    def update_config(self, entity_type: EntityType, config: EntityConfig) -> None:
        """Update configuration for a specific entity type.
        
        Args:
            entity_type: The entity type to update
            config: New configuration
        """
        if entity_type == EntityType.PROPERTY:
            self.properties = config
        elif entity_type == EntityType.NEIGHBORHOOD:
            self.neighborhoods = config
        elif entity_type == EntityType.WIKIPEDIA:
            self.wikipedia = config
        else:
            raise ValueError(f"Cannot update config for entity type: {entity_type}")


class EntityConfigLoader:
    """Loader for entity configurations from various sources."""
    
    @staticmethod
    def from_dict(config_dict: Dict[str, Any]) -> PipelineEntityConfigs:
        """Load entity configs from a dictionary.
        
        Args:
            config_dict: Dictionary with entity configurations
            
        Returns:
            PipelineEntityConfigs instance
        """
        return PipelineEntityConfigs(**config_dict)
    
    @staticmethod
    def from_yaml(yaml_path: str) -> PipelineEntityConfigs:
        """Load entity configs from a YAML file.
        
        Args:
            yaml_path: Path to YAML configuration file
            
        Returns:
            PipelineEntityConfigs instance
        """
        import yaml
        from pathlib import Path
        
        with open(Path(yaml_path), 'r') as f:
            config_dict = yaml.safe_load(f)
        
        # Extract entity_configs section if present
        if "entity_configs" in config_dict:
            config_dict = config_dict["entity_configs"]
        
        return EntityConfigLoader.from_dict(config_dict)
    
    @staticmethod
    def merge_configs(
        base_config: PipelineEntityConfigs,
        override_config: Dict[str, Any]
    ) -> PipelineEntityConfigs:
        """Merge configurations with overrides.
        
        Args:
            base_config: Base configuration
            override_config: Overrides to apply
            
        Returns:
            Merged PipelineEntityConfigs
        """
        # Convert base to dict
        base_dict = base_config.model_dump()
        
        # Deep merge with overrides
        def deep_merge(base: dict, override: dict) -> dict:
            for key, value in override.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = deep_merge(base[key], value)
                else:
                    base[key] = value
            return base
        
        merged_dict = deep_merge(base_dict, override_config)
        
        return PipelineEntityConfigs(**merged_dict)