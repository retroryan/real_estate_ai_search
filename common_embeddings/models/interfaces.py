"""
Abstract interfaces for the common embeddings module.

These interfaces define contracts for data loading, embedding generation,
and storage operations, ensuring modularity and extensibility.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Generator, Tuple
from pathlib import Path

from llama_index.core import Document
from .metadata import BaseMetadata


class IDataLoader(ABC):
    """
    Abstract interface for data loaders.
    
    Note: Data loaders are implemented in a separate project.
    This interface is provided for type hints and future integration.
    """
    
    @abstractmethod
    def load_documents(self) -> Generator[Document, None, None]:
        """
        Load documents from the data source.
        
        Yields:
            LlamaIndex Document objects with text and metadata
        """
        pass
    
    @abstractmethod
    def get_source_type(self) -> str:
        """
        Get the source type identifier.
        
        Returns:
            Source type string (e.g., "property_json", "wikipedia_db")
        """
        pass
    
    @abstractmethod
    def validate_source(self) -> bool:
        """
        Validate that the data source is accessible and valid.
        
        Returns:
            True if source is valid, False otherwise
        """
        pass


class IEmbeddingProvider(ABC):
    """
    Abstract interface for embedding providers.
    
    All embedding providers must implement this interface.
    """
    
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        pass
    
    @abstractmethod
    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """
        Get the dimension of embeddings produced.
        
        Returns:
            Embedding dimension
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the model name/identifier.
        
        Returns:
            Model name string
        """
        pass


class IVectorStore(ABC):
    """
    Abstract interface for vector storage operations.
    
    Defines the contract for storing and retrieving embeddings.
    """
    
    @abstractmethod
    def create_collection(
        self,
        name: str,
        metadata: Dict[str, Any],
        force_recreate: bool = False
    ) -> None:
        """
        Create or get a collection for storing embeddings.
        
        Args:
            name: Collection name
            metadata: Collection-level metadata
            force_recreate: Delete existing collection if True
        """
        pass
    
    @abstractmethod
    def add_embeddings(
        self,
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """
        Add embeddings to the collection.
        
        Args:
            embeddings: List of embedding vectors
            texts: List of text content
            metadatas: List of metadata dictionaries
            ids: List of unique identifiers
        """
        pass
    
    @abstractmethod
    def get_all(
        self,
        include_embeddings: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve all data from the collection.
        
        Args:
            include_embeddings: Whether to include embedding vectors
            
        Returns:
            Dictionary with ids, embeddings, texts, and metadatas
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Get the total number of embeddings in the collection.
        
        Returns:
            Number of embeddings
        """
        pass
    
    @abstractmethod
    def delete_collection(self, name: str) -> None:
        """
        Delete a collection.
        
        Args:
            name: Collection name to delete
        """
        pass


class ITextProcessor(ABC):
    """
    Abstract interface for text processing operations.
    
    Handles text preparation before embedding generation.
    """
    
    @abstractmethod
    def process_text(self, text: str) -> str:
        """
        Process raw text before embedding.
        
        Args:
            text: Raw text
            
        Returns:
            Processed text
        """
        pass
    
    @abstractmethod
    def create_chunks(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Split text into chunks with metadata.
        
        Args:
            text: Text to chunk
            metadata: Optional base metadata for chunks
            
        Returns:
            List of (chunk_text, chunk_metadata) tuples
        """
        pass


class ICorrelationEngine(ABC):
    """
    Abstract interface for correlation operations.
    
    Handles matching embeddings with source data.
    """
    
    @abstractmethod
    def correlate_embeddings(
        self,
        embeddings_data: Dict[str, Any],
        source_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Correlate embeddings with source data using metadata.
        
        Args:
            embeddings_data: Data from vector store
            source_data: Original source data
            
        Returns:
            List of correlated records
        """
        pass
    
    @abstractmethod
    def validate_correlation(
        self,
        metadata: BaseMetadata
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that metadata contains required correlation fields.
        
        Args:
            metadata: Metadata to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass