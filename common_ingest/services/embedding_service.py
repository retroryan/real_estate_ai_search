"""
Embedding service for interfacing with ChromaDB.

Provides methods to retrieve embeddings from ChromaDB collections,
supporting bulk operations and filtering by entity type.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from property_finder_models import EmbeddingData

from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class EmbeddingService:
    """
    Service for retrieving embeddings from ChromaDB.
    
    Provides bulk retrieval methods and entity filtering capabilities.
    """
    
    def __init__(self, chromadb_path: str):
        """
        Initialize embedding service with ChromaDB client.
        
        Args:
            chromadb_path: Path to ChromaDB persistent storage
        """
        self.chromadb_path = chromadb_path
        self.client = chromadb.PersistentClient(path=chromadb_path)
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