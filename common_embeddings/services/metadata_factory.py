"""
Metadata factory for creating entity-specific metadata objects.

Provides a clean separation of concerns by extracting metadata creation
logic from the main pipeline, following the Factory pattern.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models import (
    BaseMetadata,
    PropertyMetadata,
    NeighborhoodMetadata,
    WikipediaMetadata,
    EntityType,
    SourceType,
    EmbeddingProvider,
    Config
)
from ..models.processing import ProcessingChunkMetadata
from ..utils import get_logger

logger = get_logger(__name__)


class MetadataFactory:
    """
    Factory for creating entity-specific metadata objects.
    
    Centralizes metadata creation logic and ensures consistency
    across different entity types with proper Pydantic validation.
    """
    
    def __init__(self, config: Config, model_identifier: str):
        """
        Initialize metadata factory.
        
        Args:
            config: Pipeline configuration
            model_identifier: Identifier for the embedding model
        """
        self.config = config
        self.model_identifier = model_identifier
    
    def create_metadata(
        self,
        chunk_metadata: ProcessingChunkMetadata,
        entity_type: EntityType,
        source_type: SourceType,
        source_file: str,
        embedding: List[float]
    ) -> BaseMetadata:
        """
        Create appropriate metadata object for the entity type.
        
        Args:
            chunk_metadata: ProcessingChunkMetadata Pydantic model
            entity_type: Type of entity being processed
            source_type: Source data type
            source_file: Path to source file
            embedding: Generated embedding vector
            
        Returns:
            Appropriate Pydantic metadata object for the entity type
            
        Raises:
            ValueError: If entity_type is not supported
        """
        # Create common base fields
        base_fields = self._create_base_fields(
            entity_type, source_type, source_file, embedding, chunk_metadata
        )
        
        # Debug: log base fields to understand what's being created  
        logger.debug(f"Creating metadata with base_fields keys: {list(base_fields.keys())}")
        logger.debug(f"entity_type value: {entity_type} (type: {type(entity_type)})")
        logger.debug(f"source_type value: {source_type} (type: {type(source_type)})")
        logger.debug(f"embedding_provider value: {self.config.embedding.provider} (type: {type(self.config.embedding.provider)})")
        
        # Create entity-specific metadata using factory pattern
        if entity_type == EntityType.PROPERTY:
            return self._create_property_metadata(chunk_metadata, base_fields)
        elif entity_type == EntityType.NEIGHBORHOOD:
            return self._create_neighborhood_metadata(chunk_metadata, base_fields)
        elif entity_type in [EntityType.WIKIPEDIA_ARTICLE, EntityType.WIKIPEDIA_SUMMARY]:
            result = self._create_wikipedia_metadata(chunk_metadata, base_fields)
            logger.debug(f"Created Wikipedia metadata with fields: {list(result.model_dump().keys())}")
            return result
        else:
            # Fallback to base metadata for unknown entity types
            logger.warning(f"Unknown entity type {entity_type}, using base metadata")
            return BaseMetadata(
                entity_type=entity_type,
                **base_fields
            )
    
    def _create_base_fields(
        self,
        entity_type: EntityType,
        source_type: SourceType,
        source_file: str,
        embedding: List[float],
        chunk_metadata: ProcessingChunkMetadata
    ) -> Dict[str, Any]:
        """
        Create common base fields for all metadata objects.
        
        Args:
            entity_type: Entity type
            source_type: Source type  
            source_file: Source file path
            embedding: Embedding vector
            chunk_metadata: ProcessingChunkMetadata Pydantic model
            
        Returns:
            Dictionary of common base fields
        """
        # Generate unique embedding ID
        embedding_id = f"{chunk_metadata.text_hash}_{entity_type.value}"
        
        return {
            "embedding_id": embedding_id,
            "entity_type": entity_type,
            "source_type": source_type,
            "source_file": source_file,
            "source_collection": self._create_collection_name(entity_type),
            "source_timestamp": datetime.utcnow(),
            "embedding_model": self.model_identifier,
            "embedding_provider": self.config.embedding.provider,
            "embedding_dimension": len(embedding),
            "embedding_version": self.config.metadata_version,
            "text_hash": chunk_metadata.text_hash,
        }
    
    def _create_collection_name(self, entity_type: EntityType) -> str:
        """
        Create collection name for the entity type.
        
        Args:
            entity_type: Entity type
            
        Returns:
            Collection name string
        """
        version_suffix = self.config.metadata_version.replace('.', '')
        return f"{entity_type.value}_{self.model_identifier}_v{version_suffix}"
    
    def _create_property_metadata(
        self, 
        chunk_metadata: ProcessingChunkMetadata, 
        base_fields: Dict[str, Any]
    ) -> PropertyMetadata:
        """
        Create PropertyMetadata object.
        
        Args:
            chunk_metadata: ProcessingChunkMetadata Pydantic model
            base_fields: Common base fields
            
        Returns:
            PropertyMetadata object with validation
        """
        return PropertyMetadata(
            listing_id=chunk_metadata.listing_id or '',
            source_file_index=chunk_metadata.source_file_index,
            **base_fields
        )
    
    def _create_neighborhood_metadata(
        self, 
        chunk_metadata: ProcessingChunkMetadata, 
        base_fields: Dict[str, Any]
    ) -> NeighborhoodMetadata:
        """
        Create NeighborhoodMetadata object.
        
        Args:
            chunk_metadata: ProcessingChunkMetadata Pydantic model
            base_fields: Common base fields
            
        Returns:
            NeighborhoodMetadata object with validation
        """
        return NeighborhoodMetadata(
            neighborhood_id=chunk_metadata.neighborhood_id or '',
            neighborhood_name=chunk_metadata.neighborhood_name or '',
            source_file_index=chunk_metadata.source_file_index,
            **base_fields
        )
    
    def _create_wikipedia_metadata(
        self, 
        chunk_metadata: ProcessingChunkMetadata, 
        base_fields: Dict[str, Any]
    ) -> WikipediaMetadata:
        """
        Create WikipediaMetadata object with flat chunk fields.
        
        Args:
            chunk_metadata: ProcessingChunkMetadata Pydantic model
            base_fields: Common base fields
            
        Returns:
            WikipediaMetadata object with flat fields for ChromaDB
        """
        # Create parent_id from page_id if multi-chunk document
        parent_id = None
        if chunk_metadata.chunk_total > 1:
            parent_id = str(chunk_metadata.page_id or '')
        
        return WikipediaMetadata(
            page_id=chunk_metadata.page_id or 0,
            article_id=chunk_metadata.article_id or 0,  # Required field for correlation
            title=chunk_metadata.title or 'Unknown',
            # Flat chunk fields for direct ChromaDB access
            chunk_index=chunk_metadata.chunk_index,
            chunk_total=chunk_metadata.chunk_total,
            chunk_parent_id=parent_id,
            chunk_start_position=chunk_metadata.start_position,
            chunk_end_position=chunk_metadata.end_position,
            **base_fields
        )
    
