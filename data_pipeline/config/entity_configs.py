"""
Entity-specific configuration models.

This module provides separate configuration models for each entity type,
removing coupling between different entity processing requirements.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from data_pipeline.config.models import (
    ProviderType
)


class PropertyPipelineConfig(BaseModel):
    """Configuration specific to property processing pipeline."""
    
    # Data loading
    data_sources: Dict[str, str] = Field(
        description="Property data source paths"
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