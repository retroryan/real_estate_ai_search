"""
Batch storage manager for efficient ChromaDB operations.

Handles batching of embeddings for optimal storage performance
with proper error handling and statistics tracking.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from pydantic import BaseModel

from ..models import BaseMetadata, EntityType, SourceType
from ..storage.chromadb_store import ChromaDBStore
from ..utils import get_logger

logger = get_logger(__name__)


class BatchStorageStats(BaseModel):
    """Statistics for batch storage operations."""
    
    embeddings_stored: int = 0
    batches_processed: int = 0
    errors: int = 0
    failed_embeddings: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total = self.embeddings_stored + self.failed_embeddings
        return (self.embeddings_stored / total * 100) if total > 0 else 0.0


@dataclass
class StorageBatch:
    """Container for a batch of embeddings ready for storage."""
    
    embeddings: List[List[float]] = field(default_factory=list)
    texts: List[str] = field(default_factory=list)
    metadatas: List[Dict[str, Any]] = field(default_factory=list)
    ids: List[str] = field(default_factory=list)
    
    def add_item(
        self,
        embedding: List[float],
        text: str,
        metadata: Dict[str, Any],
        item_id: str
    ) -> None:
        """Add an item to the batch."""
        self.embeddings.append(embedding)
        self.texts.append(text)
        self.metadatas.append(metadata)
        self.ids.append(item_id)
    
    def size(self) -> int:
        """Get the current batch size."""
        return len(self.embeddings)
    
    def clear(self) -> None:
        """Clear all items from the batch."""
        self.embeddings.clear()
        self.texts.clear()
        self.metadatas.clear()
        self.ids.clear()
    
    def is_empty(self) -> bool:
        """Check if batch is empty."""
        return len(self.embeddings) == 0


class BatchStorageManager:
    """
    Manages batch storage of embeddings to ChromaDB.
    
    Provides efficient batching with configurable batch sizes,
    error handling, and comprehensive statistics tracking.
    """
    
    def __init__(
        self,
        store: ChromaDBStore,
        batch_size: int = 100,
        auto_flush: bool = True
    ):
        """
        Initialize batch storage manager.
        
        Args:
            store: ChromaDB store instance
            batch_size: Maximum items per batch
            auto_flush: Whether to automatically flush batches when full
        """
        self.store = store
        self.batch_size = batch_size
        self.auto_flush = auto_flush
        
        # Current batch and statistics
        self._current_batch = StorageBatch()
        self._stats = BatchStorageStats()
        
        # Collection context
        self._current_collection: Optional[str] = None
    
    def prepare_collection(
        self,
        collection_name: str,
        entity_type: EntityType,
        source_type: SourceType,
        model_identifier: str,
        force_recreate: bool = False
    ) -> None:
        """
        Prepare ChromaDB collection for storage.
        
        Args:
            collection_name: Name of the collection
            entity_type: Type of entity being stored
            source_type: Source data type
            model_identifier: Model identifier
            force_recreate: Whether to recreate existing collection
        """
        try:
            self.store.create_collection(
                name=collection_name,
                metadata={
                    "entity_type": entity_type.value,
                    "source_type": source_type.value,
                    "model": model_identifier,
                    "created_by": "common_embeddings"
                },
                force_recreate=force_recreate
            )
            self._current_collection = collection_name
            logger.info(f"Prepared collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to prepare collection {collection_name}: {e}")
            raise
    
    def add_embedding(
        self,
        embedding: List[float],
        text: str,
        metadata: BaseMetadata,
        text_hash: str,
        chunk_index: int = 0
    ) -> None:
        """
        Add an embedding to the current batch.
        
        Args:
            embedding: Embedding vector
            text: Original text
            metadata: Pydantic metadata object
            text_hash: Hash of the text content
            chunk_index: Index of chunk (for unique ID generation)
        """
        if not self._current_collection:
            logger.warning("No collection prepared for storage")
            return
        
        # Convert Pydantic model to dict for ChromaDB
        metadata_dict = metadata.model_dump()
        
        # Validate that metadata is flat (no nested dicts/objects)
        for key, value in metadata_dict.items():
            if isinstance(value, dict):
                logger.warning(f"Nested dict found in metadata field '{key}' - this will be stringified by ChromaDB")
            elif hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, type(None))):
                logger.warning(f"Object found in metadata field '{key}' - this will be stringified by ChromaDB")
        
        # Debug: Log the metadata fields for troubleshooting
        logger.debug(f"Storing metadata with fields: {list(metadata_dict.keys())}")
        
        # Generate unique ID
        item_id = self._generate_item_id(text_hash, chunk_index)
        
        # Add to current batch
        self._current_batch.add_item(
            embedding=embedding,
            text=text,
            metadata=metadata_dict,
            item_id=item_id
        )
        
        # Auto-flush if batch is full
        if self.auto_flush and self._current_batch.size() >= self.batch_size:
            self.flush_batch()
    
    def flush_batch(self) -> bool:
        """
        Flush the current batch to storage.
        
        Returns:
            True if successful, False if errors occurred
        """
        if self._current_batch.is_empty():
            return True
        
        if not self._current_collection:
            logger.error("No collection prepared for batch flush")
            return False
        
        try:
            self.store.add_embeddings(
                embeddings=self._current_batch.embeddings,
                texts=self._current_batch.texts,
                metadatas=self._current_batch.metadatas,
                ids=self._current_batch.ids
            )
            
            # Update statistics
            batch_size = self._current_batch.size()
            self._stats.embeddings_stored += batch_size
            self._stats.batches_processed += 1
            
            logger.info(f"Stored batch of {batch_size} embeddings to {self._current_collection}")
            
            # Clear the batch
            self._current_batch.clear()
            return True
            
        except Exception as e:
            # Update error statistics
            batch_size = self._current_batch.size()
            self._stats.errors += 1
            self._stats.failed_embeddings += batch_size
            
            logger.error(f"Failed to store batch of {batch_size} embeddings: {e}")
            
            # Clear the failed batch to prevent retry loops
            self._current_batch.clear()
            return False
    
    def finalize(self) -> BatchStorageStats:
        """
        Finalize storage by flushing any remaining batch.
        
        Returns:
            Final storage statistics
        """
        if not self._current_batch.is_empty():
            self.flush_batch()
        
        return self._stats.model_copy()
    
    def get_statistics(self) -> BatchStorageStats:
        """
        Get current storage statistics.
        
        Returns:
            Current statistics
        """
        return self._stats.model_copy()
    
    def _generate_item_id(self, text_hash: str, chunk_index: int) -> str:
        """
        Generate a unique ID for storage.
        
        Args:
            text_hash: Hash of the text content
            chunk_index: Index of the chunk
            
        Returns:
            Unique ID string
        """
        return f"{text_hash}_{chunk_index}"
    
    @property
    def current_batch_size(self) -> int:
        """Get size of current batch."""
        return self._current_batch.size()
    
    @property
    def is_batch_full(self) -> bool:
        """Check if current batch is full."""
        return self._current_batch.size() >= self.batch_size