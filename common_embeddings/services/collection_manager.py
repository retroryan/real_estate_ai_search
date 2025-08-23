"""
Collection manager for organizing embeddings by entity type.

Provides high-level management of ChromaDB collections with proper naming
and separation by entity types.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from ..models.config import Config
from ..models.enums import EntityType
from ..models.statistics import CollectionInfo
from ..storage.chromadb_store import ChromaDBStore
from ..utils.logging import get_logger


logger = get_logger(__name__)


class CollectionManager:
    """
    Manages ChromaDB collections with separation by entity type.
    
    Creates separate collections for properties, neighborhoods, and Wikipedia articles
    to enable better organization and querying.
    """
    
    def __init__(self, config: Config):
        """
        Initialize collection manager.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.store = ChromaDBStore(config.chromadb)
        
    def get_collection_name(self, entity_type: EntityType, model_identifier: str, version: str = "1") -> str:
        """
        Generate collection name using configured patterns.
        
        Args:
            entity_type: Type of entity (property, neighborhood, etc.)
            model_identifier: Embedding model identifier
            version: Collection version (default: "1")
            
        Returns:
            Collection name string formatted with the appropriate pattern
        """
        # Clean model identifier for collection names
        clean_model = model_identifier.replace('-', '_').replace('.', '_')
        
        # Select pattern based on entity type
        if entity_type == EntityType.PROPERTY:
            pattern = self.config.chromadb.property_collection_pattern
        elif entity_type == EntityType.NEIGHBORHOOD:
            pattern = self.config.chromadb.neighborhood_collection_pattern
        elif entity_type in [EntityType.WIKIPEDIA_ARTICLE, EntityType.WIKIPEDIA_SUMMARY]:
            pattern = self.config.chromadb.wikipedia_collection_pattern
        else:
            # Fallback pattern for unknown entity types
            pattern = "{entity}_{model}_v{version}"
            return pattern.format(
                entity=entity_type.value.lower(),
                model=clean_model,
                version=version
            )
        
        # Format the pattern
        return pattern.format(model=clean_model, version=version)
    
    def create_collection_for_entity(
        self,
        entity_type: EntityType,
        model_identifier: str,
        force_recreate: bool = False,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create or get collection for specific entity type.
        
        Args:
            entity_type: Type of entity
            model_identifier: Embedding model identifier
            force_recreate: Whether to delete existing collection
            additional_metadata: Additional metadata for collection
            
        Returns:
            Collection name that was created/retrieved
        """
        collection_name = self.get_collection_name(entity_type, model_identifier)
        
        # Base metadata
        metadata = {
            "entity_type": entity_type.value,
            "model": model_identifier,
            "created_by": "common_embeddings",
            "created_at": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        # Add additional metadata
        if additional_metadata:
            metadata.update(additional_metadata)
        
        logger.info(f"Creating collection '{collection_name}' for {entity_type.value}")
        
        self.store.create_collection(
            name=collection_name,
            metadata=metadata,
            force_recreate=force_recreate
        )
        
        return collection_name
    
    def store_embeddings_by_entity(
        self,
        entity_type: EntityType,
        model_identifier: str,
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        force_recreate: bool = False
    ) -> str:
        """
        Store embeddings in entity-specific collection.
        
        Args:
            entity_type: Type of entity
            model_identifier: Embedding model identifier
            embeddings: List of embedding vectors
            texts: List of text content
            metadatas: List of metadata dictionaries
            ids: List of unique identifiers
            force_recreate: Whether to recreate collection
            
        Returns:
            Collection name where embeddings were stored
        """
        collection_name = self.create_collection_for_entity(
            entity_type, model_identifier, force_recreate
        )
        
        # Switch to the collection
        self.store.create_collection(collection_name, {}, False)  # Don't recreate
        
        # Store embeddings
        self.store.add_embeddings(embeddings, texts, metadatas, ids)
        
        logger.info(f"Stored {len(embeddings)} embeddings in collection '{collection_name}'")
        return collection_name
    
    # Removed dead methods: get_collections_by_entity() and get_statistics()
    # These contained stub implementations and were not used anywhere in the codebase
    
    def get_entity_collection_info(self, entity_type: EntityType, model_identifier: str) -> CollectionInfo:
        """
        Get information about a specific entity collection.
        
        Args:
            entity_type: Type of entity
            model_identifier: Embedding model identifier
            
        Returns:
            CollectionInfo with structured collection information
        """
        collection_name = self.get_collection_name(entity_type, model_identifier)
        
        try:
            # Switch to collection
            self.store.create_collection(collection_name, {}, False)
            count = self.store.count()
            
            return CollectionInfo(
                collection_name=collection_name,
                entity_type=entity_type,
                model=model_identifier,
                count=count,
                exists=True
            )
        except Exception as e:
            logger.warning(f"Collection '{collection_name}' not found: {e}")
            return CollectionInfo(
                collection_name=collection_name,
                entity_type=entity_type,
                model=model_identifier,
                count=0,
                exists=False
            )