"""
Service layer for the common embeddings module.

Provides high-level services for managing embeddings and collections.
"""

from .collection_manager import CollectionManager
from .metadata_factory import MetadataFactory
from .batch_storage import BatchStorageManager, BatchStorageStats, StorageBatch

__all__ = [
    "CollectionManager",
    "MetadataFactory", 
    "BatchStorageManager",
    "BatchStorageStats",
    "StorageBatch",
]