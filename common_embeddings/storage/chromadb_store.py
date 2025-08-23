"""
ChromaDB storage implementation for embeddings.

Adapted from wiki_embed and real_estate_embed ChromaDB implementations
with enhanced support for correlation metadata.
"""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

from ..models.interfaces import IVectorStore
from ..models.config import ChromaDBConfig
from ..models.exceptions import StorageError
from ..utils.logging import get_logger
from ..utils.validation import validate_collection_name, validate_metadata_fields


logger = get_logger(__name__)


class ChromaDBStore(IVectorStore):
    """
    ChromaDB implementation for centralized embedding storage.
    
    Supports bulk export via collection.get() for downstream correlation.
    """
    
    def __init__(self, config: ChromaDBConfig):
        """
        Initialize ChromaDB store.
        
        Args:
            config: ChromaDB configuration
        """
        self.config = config
        self.client = None
        self.collection = None
        self.collection_name = None
        
        # Initialize client
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize ChromaDB client."""
        try:
            self.client = chromadb.PersistentClient(
                path=self.config.path,
                settings=Settings(anonymized_telemetry=False)
            )
            logger.info(f"Initialized ChromaDB client at {self.config.path}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise StorageError(f"ChromaDB initialization failed: {e}")
    
    def create_collection(
        self,
        name: str,
        metadata: Dict[str, Any],
        force_recreate: bool = False
    ) -> None:
        """
        Create or get a collection for storing embeddings.
        
        Args:
            name: Collection name (must follow pattern)
            metadata: Collection-level metadata
            force_recreate: Delete existing collection if True
        """
        # Validate collection name format
        is_valid, error = validate_collection_name(name)
        if not is_valid:
            logger.warning(f"Collection name validation failed: {error}")
            # Continue anyway for flexibility
        
        self.collection_name = name
        
        # Handle force recreation
        if force_recreate:
            try:
                self.client.delete_collection(name)
                logger.info(f"Deleted existing collection: {name}")
            except Exception:
                pass  # Collection doesn't exist
        
        # Create or get collection
        try:
            self.collection = self.client.get_or_create_collection(
                name=name,
                metadata=metadata
            )
            logger.info(f"Using collection: {name} with {self.collection.count()} existing embeddings")
        except Exception as e:
            logger.error(f"Failed to create/get collection: {e}")
            raise StorageError(f"Collection creation failed: {e}")
    
    def add_embeddings(
        self,
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """
        Add embeddings to the collection with validation.
        
        Args:
            embeddings: List of embedding vectors
            texts: List of text content
            metadatas: List of metadata dictionaries
            ids: List of unique identifiers
        """
        if not self.collection:
            raise StorageError("No collection selected. Call create_collection first.")
        
        # Validate metadata
        for i, metadata in enumerate(metadatas):
            is_valid, error = validate_metadata_fields(metadata)
            if not is_valid:
                logger.warning(f"Metadata validation failed for item {i}: {error}")
        
        # Add to collection
        try:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            logger.info(f"Added {len(embeddings)} embeddings to collection {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to add embeddings: {e}")
            raise StorageError(f"Failed to store embeddings: {e}")
    
    def get_all(
        self,
        include_embeddings: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve all data from the collection for bulk export.
        
        This is the key method for downstream services to extract
        all embeddings and metadata for correlation.
        
        Args:
            include_embeddings: Whether to include embedding vectors
            
        Returns:
            Dictionary with ids, embeddings, documents, and metadatas
        """
        if not self.collection:
            raise StorageError("No collection selected.")
        
        # Determine what to include
        include = ["documents", "metadatas"]
        if include_embeddings:
            include.append("embeddings")
        
        try:
            # Get all data from collection
            results = self.collection.get(include=include)
            
            logger.info(
                f"Retrieved {len(results.get('ids', []))} items from {self.collection_name}"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve data: {e}")
            raise StorageError(f"Failed to get collection data: {e}")
    
    def query(
        self,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query collection for similar embeddings.
        
        Args:
            query_embeddings: Query embedding vectors
            n_results: Number of results to return
            where: Optional metadata filter
            
        Returns:
            Query results with ids, distances, documents, and metadatas
        """
        if not self.collection:
            raise StorageError("No collection selected.")
        
        try:
            results = self.collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where
            )
            return results
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise StorageError(f"Query failed: {e}")
    
    def count(self) -> int:
        """
        Get the total number of embeddings in the collection.
        
        Returns:
            Number of embeddings
        """
        if not self.collection:
            return 0
        
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Failed to get count: {e}")
            return 0
    
    def delete_collection(self, name: str) -> None:
        """
        Delete a collection.
        
        Args:
            name: Collection name to delete
        """
        try:
            self.client.delete_collection(name)
            logger.info(f"Deleted collection: {name}")
            
            if self.collection_name == name:
                self.collection = None
                self.collection_name = None
                
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise StorageError(f"Failed to delete collection: {e}")
    
    def list_collections(self) -> List[str]:
        """
        List all available collections.
        
        Returns:
            List of collection names
        """
        try:
            collections = self.client.list_collections()
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
    
    def get_collection_metadata(self, name: str) -> Dict[str, Any]:
        """
        Get metadata for a collection.
        
        Args:
            name: Collection name
            
        Returns:
            Collection metadata
        """
        try:
            collection = self.client.get_collection(name)
            return collection.metadata or {}
        except Exception as e:
            logger.error(f"Failed to get collection metadata: {e}")
            return {}