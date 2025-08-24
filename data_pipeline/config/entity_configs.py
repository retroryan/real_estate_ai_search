"""
Entity-specific configuration models.

This module provides separate configuration models for each entity type,
removing coupling between different entity processing requirements.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from data_pipeline.config.models import (
    ProviderType,
    ChunkingMethod,
    DataSubsetConfig,
    SubsetConfig,
)


class PropertyPipelineConfig(BaseModel):
    """Configuration specific to property processing pipeline."""
    
    # Data loading
    data_sources: Dict[str, str] = Field(
        description="Property data source paths"
    )
    subset_config: Optional[SubsetConfig] = Field(
        None,
        description="Property-specific data subsetting"
    )
    
    # Processing settings
    enable_price_validation: bool = Field(
        default=True,
        description="Validate property price ranges"
    )
    enable_address_normalization: bool = Field(
        default=True,
        description="Normalize property addresses"
    )
    calculate_derived_fields: bool = Field(
        default=True,
        description="Calculate price_per_sqft and other derived fields"
    )
    
    # Quality thresholds
    min_quality_score: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Minimum quality score for property records"
    )
    max_price_per_sqft: float = Field(
        default=10000.0,
        gt=0,
        description="Maximum reasonable price per square foot"
    )
    
    # Text processing
    text_processing: Dict[str, Any] = Field(
        default_factory=lambda: {
            "include_price": True,
            "include_features": True,
            "max_description_length": 2000
        },
        description="Property-specific text processing settings"
    )
    
    # Embeddings
    embedding_provider: ProviderType = Field(
        default=ProviderType.OLLAMA,
        description="Embedding provider for properties"
    )
    chunking_enabled: bool = Field(
        default=False,
        description="Enable chunking for property descriptions"
    )
    
    # Output destinations
    write_to_chromadb: bool = Field(default=True)
    write_to_elasticsearch: bool = Field(default=True)
    write_to_neo4j: bool = Field(default=True)
    
    # ChromaDB settings
    chromadb_collection: str = Field(
        default="properties_embeddings",
        description="ChromaDB collection name for properties"
    )


class NeighborhoodPipelineConfig(BaseModel):
    """Configuration specific to neighborhood processing pipeline."""
    
    # Data loading
    data_sources: Dict[str, str] = Field(
        description="Neighborhood data source paths"
    )
    subset_config: Optional[SubsetConfig] = Field(
        None,
        description="Neighborhood-specific data subsetting"
    )
    
    # Processing settings
    enable_demographic_validation: bool = Field(
        default=True,
        description="Validate demographic data ranges"
    )
    enable_boundary_processing: bool = Field(
        default=True,
        description="Process neighborhood boundary data"
    )
    normalize_location_names: bool = Field(
        default=True,
        description="Normalize neighborhood and city names"
    )
    
    # Quality thresholds
    min_quality_score: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum quality score for neighborhood records"
    )
    min_demographic_completeness: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum required demographic data completeness"
    )
    
    # Text processing
    text_processing: Dict[str, Any] = Field(
        default_factory=lambda: {
            "include_demographics": True,
            "include_amenities": True,
            "max_description_length": 3000
        },
        description="Neighborhood-specific text processing settings"
    )
    
    # Embeddings
    embedding_provider: ProviderType = Field(
        default=ProviderType.OLLAMA,
        description="Embedding provider for neighborhoods"
    )
    chunking_enabled: bool = Field(
        default=False,
        description="Enable chunking for neighborhood descriptions"
    )
    
    # Output destinations
    write_to_chromadb: bool = Field(default=True)
    write_to_elasticsearch: bool = Field(default=True)
    write_to_neo4j: bool = Field(default=True)
    
    # ChromaDB settings
    chromadb_collection: str = Field(
        default="neighborhoods_embeddings",
        description="ChromaDB collection name for neighborhoods"
    )


class WikipediaPipelineConfig(BaseModel):
    """Configuration specific to Wikipedia article processing pipeline."""
    
    # Data loading
    data_sources: Dict[str, str] = Field(
        description="Wikipedia data source paths (typically SQLite databases)"
    )
    subset_config: Optional[SubsetConfig] = Field(
        None,
        description="Wikipedia-specific data subsetting"
    )
    
    # Processing settings
    enable_location_extraction: bool = Field(
        default=True,
        description="Extract and validate location references"
    )
    enable_confidence_filtering: bool = Field(
        default=True,
        description="Filter articles by confidence scores"
    )
    calculate_relevance_scores: bool = Field(
        default=True,
        description="Calculate location relevance scores"
    )
    
    # Quality thresholds
    min_quality_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum quality score for Wikipedia articles"
    )
    min_confidence_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for location extraction"
    )
    min_relevance_score: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score for articles"
    )
    
    # Text processing
    text_processing: Dict[str, Any] = Field(
        default_factory=lambda: {
            "use_long_summary": True,
            "include_metadata": True,
            "enable_cleaning": False  # Wikipedia content is already clean
        },
        description="Wikipedia-specific text processing settings"
    )
    
    # Embeddings
    embedding_provider: ProviderType = Field(
        default=ProviderType.OLLAMA,
        description="Embedding provider for Wikipedia articles"
    )
    chunking_enabled: bool = Field(
        default=False,
        description="Chunking disabled - Wikipedia summaries are already optimized"
    )
    
    # Output destinations
    write_to_chromadb: bool = Field(default=True)
    write_to_elasticsearch: bool = Field(default=True)
    write_to_neo4j: bool = Field(default=True)
    
    # ChromaDB settings
    chromadb_collection: str = Field(
        default="wikipedia_embeddings",
        description="ChromaDB collection name for Wikipedia articles"
    )
    
    # Wikipedia-specific settings
    required_fields: List[str] = Field(
        default_factory=lambda: ["page_id", "title", "long_summary"],
        description="Required fields for Wikipedia articles"
    )
    location_specificity_levels: List[str] = Field(
        default_factory=lambda: ["city_and_state", "state_only", "city_only", "none"],
        description="Valid location specificity levels"
    )


class EntityPipelineOrchestrator(BaseModel):
    """Orchestrator configuration for managing entity-specific pipelines."""
    
    # Entity pipeline configurations
    property_config: Optional[PropertyPipelineConfig] = None
    neighborhood_config: Optional[NeighborhoodPipelineConfig] = None
    wikipedia_config: Optional[WikipediaPipelineConfig] = None
    
    # Global settings
    parallel_processing: bool = Field(
        default=True,
        description="Process entities in parallel where possible"
    )
    fail_fast: bool = Field(
        default=False,
        description="Stop processing if any entity pipeline fails"
    )
    
    # Shared resources
    spark_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Shared Spark configuration"
    )
    logging_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Shared logging configuration"
    )
    
    # Data subsetting (applies to all entities if individual configs don't override)
    global_subset_config: Optional[DataSubsetConfig] = Field(
        None,
        description="Global data subsetting configuration"
    )
    
    # Output coordination
    coordinate_writes: bool = Field(
        default=True,
        description="Coordinate writes across entities (e.g., neighborhoods before properties)"
    )
    write_order: List[str] = Field(
        default_factory=lambda: ["neighborhoods", "properties", "wikipedia"],
        description="Order for writing entities when coordination is enabled"
    )
    
    def get_enabled_entities(self) -> List[str]:
        """
        Get list of enabled entity types.
        
        Returns:
            List of entity types with configurations
        """
        enabled = []
        if self.property_config:
            enabled.append("property")
        if self.neighborhood_config:
            enabled.append("neighborhood") 
        if self.wikipedia_config:
            enabled.append("wikipedia")
        return enabled
    
    def get_entity_config(self, entity_type: str) -> Optional[BaseModel]:
        """
        Get configuration for a specific entity type.
        
        Args:
            entity_type: Type of entity
            
        Returns:
            Configuration model for the entity type
        """
        entity_type_lower = entity_type.lower()
        
        if entity_type_lower == "property":
            return self.property_config
        elif entity_type_lower == "neighborhood":
            return self.neighborhood_config
        elif entity_type_lower in ["wikipedia", "wikipedia_article"]:
            return self.wikipedia_config
        else:
            return None