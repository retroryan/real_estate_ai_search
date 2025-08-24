"""
Embedding service for interfacing with ChromaDB.

Provides methods to retrieve embeddings from ChromaDB collections,
supporting bulk operations and filtering by entity type.
"""

import logging
import re
from typing import Dict, List, Optional, Any
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from property_finder_models import EmbeddingData

from ..utils.logger import setup_logger
from ..utils.config import ChromaDBConfig

logger = setup_logger(__name__)


class EmbeddingService:
    """
    Service for retrieving embeddings from ChromaDB.
    
    Provides bulk retrieval methods, collection discovery, and entity filtering capabilities.
    """
    
    def __init__(self, chromadb_path: str, chromadb_config: Optional[ChromaDBConfig] = None):
        """
        Initialize embedding service with ChromaDB client.
        
        Args:
            chromadb_path: Path to ChromaDB persistent storage
            chromadb_config: Optional ChromaDB configuration for collection patterns
        """
        self.chromadb_path = chromadb_path
        self.client = chromadb.PersistentClient(path=chromadb_path)
        self.config = chromadb_config
        
        # Cache for bulk-loaded embeddings (simple in-memory maps)
        self._property_cache: Dict[str, Dict[str, List[EmbeddingData]]] = {}
        self._neighborhood_cache: Dict[str, Dict[str, List[EmbeddingData]]] = {}
        self._wikipedia_cache: Dict[str, Dict[int, List[EmbeddingData]]] = {}
        
        logger.info(f"Initialized EmbeddingService with ChromaDB path: {chromadb_path}")
    
    def get_collection(self, collection_name: str) -> Optional[Collection]:
        """
        Get a ChromaDB collection by name.
        
        Args:
            collection_name: Name of the collection to retrieve
            
        Returns:
            Collection object if exists, None otherwise
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            logger.debug(f"Retrieved collection: {collection_name}")
            return collection
        except Exception as e:
            logger.warning(f"Collection '{collection_name}' not found: {e}")
            return None
    
    def get_embeddings_by_ids(
        self,
        collection_name: str,
        entity_ids: List[str],
        include_vectors: bool = False
    ) -> Dict[str, List[EmbeddingData]]:
        """
        Retrieve embeddings for specific entity IDs.
        
        Args:
            collection_name: Name of the ChromaDB collection
            entity_ids: List of entity IDs to retrieve embeddings for
            include_vectors: Whether to include embedding vectors in response
            
        Returns:
            Dictionary mapping entity IDs to their embeddings
        """
        logger.debug(f"Retrieving embeddings for {len(entity_ids)} entities from {collection_name}")
        
        collection = self.get_collection(collection_name)
        if not collection:
            logger.error(f"Collection '{collection_name}' not found")
            return {}
        
        result: Dict[str, List[EmbeddingData]] = {}
        
        try:
            # Build metadata filter for entity IDs
            # ChromaDB supports $or and $in operators for filtering
            where_clause = {
                "$or": [
                    {"listing_id": {"$in": entity_ids}},
                    {"neighborhood_id": {"$in": entity_ids}},
                    {"page_id": {"$in": [str(id) for id in entity_ids]}}
                ]
            }
            
            # Retrieve from ChromaDB
            include = ["metadatas", "documents"]
            if include_vectors:
                include.append("embeddings")
            
            results = collection.get(
                where=where_clause,
                include=include
            )
            
            # Process results and group by entity ID
            for i, metadata in enumerate(results.get("metadatas", [])):
                if not metadata:
                    continue
                
                # Determine entity ID from metadata
                entity_id = (
                    metadata.get("listing_id") or
                    metadata.get("neighborhood_id") or
                    str(metadata.get("page_id", ""))
                )
                
                if entity_id:
                    if entity_id not in result:
                        result[entity_id] = []
                    
                    # Create EmbeddingData object
                    embedding_data = EmbeddingData(
                        embedding_id=results["ids"][i] if "ids" in results else f"emb_{i}",
                        vector=results["embeddings"][i] if include_vectors and "embeddings" in results else None,
                        metadata=metadata,
                        chunk_index=metadata.get("chunk_index")
                    )
                    result[entity_id].append(embedding_data)
            
            logger.info(f"Retrieved embeddings for {len(result)} entities")
            return result
            
        except Exception as e:
            logger.error(f"Failed to retrieve embeddings: {e}")
            return {}
    
    def get_all_embeddings(
        self,
        collection_name: str,
        entity_type: Optional[str] = None,
        include_vectors: bool = False,
        limit: Optional[int] = None
    ) -> List[EmbeddingData]:
        """
        Get all embeddings from a collection with optional filtering.
        
        Args:
            collection_name: Name of the ChromaDB collection
            entity_type: Optional entity type filter (property, neighborhood, wikipedia_article)
            include_vectors: Whether to include embedding vectors
            limit: Maximum number of embeddings to retrieve
            
        Returns:
            List of EmbeddingData objects
        """
        logger.debug(f"Retrieving all embeddings from {collection_name}, entity_type={entity_type}")
        
        collection = self.get_collection(collection_name)
        if not collection:
            logger.error(f"Collection '{collection_name}' not found")
            return []
        
        embeddings = []
        
        try:
            # Build where clause for entity type filtering
            where_clause = {"entity_type": {"$eq": entity_type}} if entity_type else None
            
            # Determine what to include
            include = ["metadatas", "documents"]
            if include_vectors:
                include.append("embeddings")
            
            # Retrieve from ChromaDB
            results = collection.get(
                where=where_clause,
                include=include,
                limit=limit
            )
            
            # Convert to EmbeddingData objects
            for i in range(len(results.get("ids", []))):
                embedding_data = EmbeddingData(
                    embedding_id=results["ids"][i],
                    vector=results["embeddings"][i] if include_vectors and "embeddings" in results else None,
                    metadata=results["metadatas"][i] if "metadatas" in results else {},
                    chunk_index=results["metadatas"][i].get("chunk_index") if "metadatas" in results else None
                )
                embeddings.append(embedding_data)
            
            logger.info(f"Retrieved {len(embeddings)} embeddings from {collection_name}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to retrieve all embeddings: {e}")
            return []
    
    def list_collections(self) -> List[str]:
        """
        List all available ChromaDB collections.
        
        Returns:
            List of collection names
        """
        try:
            collections = self.client.list_collections()
            collection_names = [col.name for col in collections]
            logger.info(f"Found {len(collection_names)} collections")
            return collection_names
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
    
    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.
        
        Args:
            collection_name: Name of the collection to check
            
        Returns:
            True if collection exists, False otherwise
        """
        return collection_name in self.list_collections()
    
    def find_collections_by_pattern(self, entity_type: str, model: Optional[str] = None) -> List[str]:
        """
        Find collections matching the entity type and optional model pattern.
        
        Uses config patterns to discover available collections.
        
        Args:
            entity_type: Type of entity (property, neighborhood, wikipedia)
            model: Optional model name to filter by
            
        Returns:
            List of matching collection names, sorted by version (latest first)
        """
        all_collections = self.list_collections()
        
        # Build pattern based on entity type
        if entity_type == "property":
            pattern = r"property_(\w+)_v(\d+)"
        elif entity_type == "neighborhood":
            pattern = r"neighborhood_(\w+)_v(\d+)"
        elif entity_type == "wikipedia":
            pattern = r"wikipedia_(\w+)_v(\d+)"
        else:
            logger.warning(f"Unknown entity type: {entity_type}")
            return []
        
        matching = []
        for collection_name in all_collections:
            match = re.match(pattern, collection_name)
            if match:
                collection_model = match.group(1)
                version = int(match.group(2))
                
                # Filter by model if specified
                if model:
                    model_safe = model.replace("-", "_").replace(".", "_")
                    if collection_model != model_safe:
                        continue
                
                matching.append((collection_name, version))
        
        # Sort by version (latest first) and return names only
        matching.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in matching]
    
    def get_latest_collection(self, entity_type: str, model: Optional[str] = None) -> Optional[str]:
        """
        Get the latest collection for an entity type and optional model.
        
        Args:
            entity_type: Type of entity (property, neighborhood, wikipedia)
            model: Optional model name
            
        Returns:
            Name of the latest collection or None if not found
        """
        collections = self.find_collections_by_pattern(entity_type, model)
        if collections:
            logger.info(f"Found latest collection for {entity_type}: {collections[0]}")
            return collections[0]
        
        # Try using config to generate expected name
        if self.config:
            if entity_type == "property":
                expected = self.config.get_property_collection_name(model)
            elif entity_type == "neighborhood":
                expected = self.config.get_neighborhood_collection_name(model)
            elif entity_type == "wikipedia":
                expected = self.config.get_wikipedia_collection_name(model)
            else:
                expected = None
            
            if expected and self.collection_exists(expected):
                logger.info(f"Found collection using config pattern: {expected}")
                return expected
        
        logger.warning(f"No collection found for {entity_type} with model {model}")
        return None
    
    def bulk_load_property_embeddings(
        self, 
        collection_name: Optional[str] = None,
        force_reload: bool = False
    ) -> Dict[str, List[EmbeddingData]]:
        """
        Load all property embeddings into memory for fast correlation.
        
        Uses collection.get() to load entire collection at once.
        
        Args:
            collection_name: Optional collection name, will auto-discover if not provided
            force_reload: Force reload even if cached
            
        Returns:
            Dictionary mapping listing_id to list of EmbeddingData
        """
        # Use cache if available and not forcing reload
        if collection_name in self._property_cache and not force_reload:
            logger.debug(f"Using cached property embeddings from {collection_name}")
            return self._property_cache[collection_name]
        
        # Auto-discover collection if not specified
        if not collection_name:
            collection_name = self.get_latest_collection("property")
            if not collection_name:
                logger.warning("No property collection found")
                return {}
        
        logger.info(f"Bulk loading property embeddings from {collection_name}")
        
        collection = self.get_collection(collection_name)
        if not collection:
            return {}
        
        try:
            # Get ALL items from collection at once
            results = collection.get(include=["metadatas", "embeddings", "documents"])
            
            # Build lookup map by listing_id
            embeddings_map: Dict[str, List[EmbeddingData]] = {}
            
            for i, metadata in enumerate(results.get("metadatas", [])):
                if not metadata:
                    continue
                
                # Direct field access - no parsing needed!
                listing_id = metadata.get("listing_id")
                if not listing_id:
                    continue
                
                if listing_id not in embeddings_map:
                    embeddings_map[listing_id] = []
                
                # Create EmbeddingData with flat field access
                embedding = EmbeddingData(
                    embedding_id=results["ids"][i],
                    vector=results.get("embeddings", [None])[i],
                    metadata=metadata,
                    chunk_index=metadata.get("chunk_index", 0)  # Direct int access
                )
                embeddings_map[listing_id].append(embedding)
            
            # Sort chunks for each listing
            for listing_id in embeddings_map:
                embeddings_map[listing_id].sort(key=lambda e: e.chunk_index or 0)
            
            # Cache the results
            self._property_cache[collection_name] = embeddings_map
            
            logger.info(f"Loaded {len(embeddings_map)} property embeddings from {collection_name}")
            return embeddings_map
            
        except Exception as e:
            logger.error(f"Failed to bulk load property embeddings: {e}")
            return {}
    
    def bulk_load_neighborhood_embeddings(
        self,
        collection_name: Optional[str] = None,
        force_reload: bool = False
    ) -> Dict[str, List[EmbeddingData]]:
        """
        Load all neighborhood embeddings into memory for fast correlation.
        
        Args:
            collection_name: Optional collection name, will auto-discover if not provided
            force_reload: Force reload even if cached
            
        Returns:
            Dictionary mapping neighborhood_id to list of EmbeddingData
        """
        # Use cache if available
        if collection_name in self._neighborhood_cache and not force_reload:
            logger.debug(f"Using cached neighborhood embeddings from {collection_name}")
            return self._neighborhood_cache[collection_name]
        
        # Auto-discover collection if not specified
        if not collection_name:
            collection_name = self.get_latest_collection("neighborhood")
            if not collection_name:
                logger.warning("No neighborhood collection found")
                return {}
        
        logger.info(f"Bulk loading neighborhood embeddings from {collection_name}")
        
        collection = self.get_collection(collection_name)
        if not collection:
            return {}
        
        try:
            # Get ALL items from collection at once
            results = collection.get(include=["metadatas", "embeddings", "documents"])
            
            # Build lookup map by neighborhood_id
            embeddings_map: Dict[str, List[EmbeddingData]] = {}
            
            for i, metadata in enumerate(results.get("metadatas", [])):
                if not metadata:
                    continue
                
                # Direct field access
                neighborhood_id = metadata.get("neighborhood_id")
                if not neighborhood_id:
                    continue
                
                if neighborhood_id not in embeddings_map:
                    embeddings_map[neighborhood_id] = []
                
                embedding = EmbeddingData(
                    embedding_id=results["ids"][i],
                    vector=results.get("embeddings", [None])[i],
                    metadata=metadata,
                    chunk_index=metadata.get("chunk_index", 0)
                )
                embeddings_map[neighborhood_id].append(embedding)
            
            # Sort chunks
            for neighborhood_id in embeddings_map:
                embeddings_map[neighborhood_id].sort(key=lambda e: e.chunk_index or 0)
            
            # Cache the results
            self._neighborhood_cache[collection_name] = embeddings_map
            
            logger.info(f"Loaded {len(embeddings_map)} neighborhood embeddings from {collection_name}")
            return embeddings_map
            
        except Exception as e:
            logger.error(f"Failed to bulk load neighborhood embeddings: {e}")
            return {}
    
    def bulk_load_wikipedia_embeddings(
        self,
        collection_name: Optional[str] = None,
        force_reload: bool = False
    ) -> Dict[int, List[EmbeddingData]]:
        """
        Load all Wikipedia embeddings into memory for fast correlation.
        
        Properly handles multi-chunk documents using flat chunk_index field.
        
        Args:
            collection_name: Optional collection name, will auto-discover if not provided
            force_reload: Force reload even if cached
            
        Returns:
            Dictionary mapping page_id (int) to list of EmbeddingData
        """
        # Use cache if available
        if collection_name in self._wikipedia_cache and not force_reload:
            logger.debug(f"Using cached Wikipedia embeddings from {collection_name}")
            return self._wikipedia_cache[collection_name]
        
        # Auto-discover collection if not specified
        if not collection_name:
            collection_name = self.get_latest_collection("wikipedia")
            if not collection_name:
                logger.warning("No Wikipedia collection found")
                return {}
        
        logger.info(f"Bulk loading Wikipedia embeddings from {collection_name}")
        
        collection = self.get_collection(collection_name)
        if not collection:
            return {}
        
        try:
            # Get ALL items from collection at once
            results = collection.get(include=["metadatas", "embeddings", "documents"])
            
            # Build lookup map by page_id
            embeddings_map: Dict[int, List[EmbeddingData]] = {}
            
            for i, metadata in enumerate(results.get("metadatas", [])):
                if not metadata:
                    continue
                
                # Direct field access - all fields are flat now!
                page_id = metadata.get("page_id")
                if page_id is None:
                    continue
                
                # Ensure page_id is int
                try:
                    page_id = int(page_id)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid page_id: {page_id}")
                    continue
                
                if page_id not in embeddings_map:
                    embeddings_map[page_id] = []
                
                # Direct access to flat chunk fields
                embedding = EmbeddingData(
                    embedding_id=results["ids"][i],
                    vector=results.get("embeddings", [None])[i],
                    metadata=metadata,
                    chunk_index=metadata.get("chunk_index", 0)  # Direct int access!
                )
                embeddings_map[page_id].append(embedding)
            
            # Sort chunks for each page by chunk_index
            for page_id in embeddings_map:
                embeddings_map[page_id].sort(key=lambda e: e.chunk_index or 0)
            
            # Cache the results
            self._wikipedia_cache[collection_name] = embeddings_map
            
            # Log statistics
            total_embeddings = sum(len(chunks) for chunks in embeddings_map.values())
            multi_chunk_pages = sum(1 for chunks in embeddings_map.values() if len(chunks) > 1)
            
            logger.info(f"Loaded {total_embeddings} embeddings for {len(embeddings_map)} Wikipedia pages")
            if multi_chunk_pages:
                logger.info(f"Found {multi_chunk_pages} pages with multiple chunks")
            
            return embeddings_map
            
        except Exception as e:
            logger.error(f"Failed to bulk load Wikipedia embeddings: {e}")
            return {}