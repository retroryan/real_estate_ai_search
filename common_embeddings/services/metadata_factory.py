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
from ..models.metadata import ChunkMetadata
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
        chunk_metadata: Dict[str, Any],
        entity_type: EntityType,
        source_type: SourceType,
        source_file: str,
        embedding: List[float]
    ) -> BaseMetadata:
        """
        Create appropriate metadata object for the entity type.
        
        Args:
            chunk_metadata: Chunk-level metadata dictionary
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
        chunk_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create common base fields for all metadata objects.
        
        Args:
            entity_type: Entity type
            source_type: Source type  
            source_file: Source file path
            embedding: Embedding vector
            chunk_metadata: Chunk metadata dictionary
            
        Returns:
            Dictionary of common base fields
        """
        # Generate unique embedding ID
        embedding_id = f"{chunk_metadata.get('text_hash', 'unknown')}_{entity_type.value}"
        
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
            "text_hash": chunk_metadata.get('text_hash', ''),
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
        chunk_metadata: Dict[str, Any], 
        base_fields: Dict[str, Any]
    ) -> PropertyMetadata:
        """
        Create PropertyMetadata object.
        
        Args:
            chunk_metadata: Chunk metadata dictionary
            base_fields: Common base fields
            
        Returns:
            PropertyMetadata object with validation
        """
        return PropertyMetadata(
            listing_id=chunk_metadata.get('listing_id', ''),
            source_file_index=chunk_metadata.get('source_file_index'),
            **base_fields
        )
    
    def _create_neighborhood_metadata(
        self, 
        chunk_metadata: Dict[str, Any], 
        base_fields: Dict[str, Any]
    ) -> NeighborhoodMetadata:
        """
        Create NeighborhoodMetadata object.
        
        Args:
            chunk_metadata: Chunk metadata dictionary
            base_fields: Common base fields
            
        Returns:
            NeighborhoodMetadata object with validation
        """
        return NeighborhoodMetadata(
            neighborhood_id=chunk_metadata.get('neighborhood_id', ''),
            neighborhood_name=chunk_metadata.get('neighborhood_name', ''),
            source_file_index=chunk_metadata.get('source_file_index'),
            **base_fields
        )
    
    def _create_wikipedia_metadata(
        self, 
        chunk_metadata: Dict[str, Any], 
        base_fields: Dict[str, Any]
    ) -> WikipediaMetadata:
        """
        Create WikipediaMetadata object.
        
        Args:
            chunk_metadata: Chunk metadata dictionary
            base_fields: Common base fields
            
        Returns:
            WikipediaMetadata object with validation
        """
        # Handle chunking metadata if present
        chunk_meta = self._create_chunk_metadata(chunk_metadata)
        
        return WikipediaMetadata(
            page_id=chunk_metadata.get('page_id', 0),
            article_id=chunk_metadata.get('article_id'),
            has_summary=chunk_metadata.get('has_summary', False),
            chunk_metadata=chunk_meta,
            title=chunk_metadata.get('title', 'Unknown'),
            **base_fields
        )
    
    def _create_chunk_metadata(self, chunk_metadata: Dict[str, Any]) -> Optional[ChunkMetadata]:
        """
        Create ChunkMetadata object if chunk information is present.
        
        Args:
            chunk_metadata: Chunk metadata dictionary
            
        Returns:
            ChunkMetadata object or None if not applicable
        """
        chunk_total = chunk_metadata.get('chunk_total', 1)
        
        # Only create chunk metadata for multi-chunk documents
        if chunk_total <= 1:
            return None
        
        return ChunkMetadata(
            chunk_index=chunk_metadata.get('chunk_index', 0),
            chunk_total=chunk_total,
            parent_id=str(chunk_metadata.get('page_id', '')),
            start_position=chunk_metadata.get('start_position', 0),
            end_position=chunk_metadata.get('end_position', len(chunk_metadata.get('text', ''))),
            token_count=chunk_metadata.get('token_count'),
            overlap_previous=chunk_metadata.get('overlap_previous'),
            overlap_next=chunk_metadata.get('overlap_next')
        )