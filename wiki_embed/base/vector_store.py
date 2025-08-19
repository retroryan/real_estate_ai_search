"""
Abstract base classes for vector store implementations.
Clean separation between vector store creation/management and search operations.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class VectorStore(ABC):
    """Abstract base class for vector store creation and management."""
    
    @abstractmethod
    def create_collection(self, name: str, metadata: Dict[str, Any], force_recreate: bool = False) -> None:
        """Create or get collection/index."""
        pass
    
    @abstractmethod
    def add_embeddings(self, embeddings: List[List[float]], texts: List[str], 
                      metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        """Add embeddings to the store."""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """Get total document count."""
        pass
    
    @abstractmethod
    def delete_collection(self, name: str) -> None:
        """Delete collection/index."""
        pass


class VectorSearcher(ABC):
    """Abstract base class for vector search operations."""
    
    @abstractmethod
    def similarity_search(self, query_embedding: List[float], top_k: int) -> Dict[str, Any]:
        """Perform similarity search."""
        pass