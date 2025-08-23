"""
Service layer for the common embeddings module.

Provides high-level services for managing embeddings and collections.
"""

from .collection_manager import CollectionManager

__all__ = [
    "CollectionManager",
]