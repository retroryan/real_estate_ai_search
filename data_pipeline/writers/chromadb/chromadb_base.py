"""
Base ChromaDB writer implementation.

This module provides the base ChromaDB writer functionality that is shared
across all entity-specific ChromaDB writers.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional
from abc import abstractmethod

import chromadb
from chromadb.config import Settings
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, collect_list, struct

from data_pipeline.writers.base import DataWriter
from .chromadb_config import ChromaDBWriterConfig

logger = logging.getLogger(__name__)


class BaseChromaDBWriter(DataWriter):
    """
    Base ChromaDB writer with common functionality.
    
    Provides core ChromaDB operations that are shared across
    all entity-specific writers.
    """
    
    def __init__(self, config: ChromaDBWriterConfig):
        """
        Initialize the base ChromaDB writer.
        
        Args:
            config: ChromaDB writer configuration
        """
        super().__init__(config)
        self.config: ChromaDBWriterConfig = config
        self.client = None
        self.collection = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _initialize_client(self) -> bool:
        """
        Initialize ChromaDB client.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client = chromadb.PersistentClient(
                path=self.config.persist_directory,
                settings=Settings(
                    anonymized_telemetry=self.config.anonymized_telemetry
                )
            )
            self.logger.info(f"Initialized ChromaDB client at {self.config.persist_directory}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB client: {e}")
            return False
    
    def _get_or_create_collection(self, name: str, metadata: Dict[str, Any]) -> bool:
        """
        Get or create a ChromaDB collection.
        
        Args:
            name: Collection name
            metadata: Collection metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.config.clear_before_write:
                # Delete existing collection if configured
                try:
                    self.client.delete_collection(name)
                    self.logger.info(f"Deleted existing collection: {name}")
                except Exception:
                    pass  # Collection doesn't exist
            
            # Create or get collection
            self.collection = self.client.get_or_create_collection(
                name=name,
                metadata={
                    **metadata,
                    "distance_metric": self.config.distance_metric,
                    "embedding_dimension": self.config.embedding_dimension
                }
            )
            
            existing_count = self.collection.count()
            self.logger.info(f"Using collection '{name}' with {existing_count} existing embeddings")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create/get collection '{name}': {e}")
            return False
    
    def validate_connection(self) -> bool:
        """
        Validate ChromaDB connection and collection.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Initialize client if not already done
            if self.client is None:
                if not self._initialize_client():
                    return False
            
            # Test connection by listing collections
            collections = self.client.list_collections()
            self.logger.info(f"ChromaDB connection validated, {len(collections)} collections found")
            
            return True
            
        except Exception as e:
            self.logger.error(f"ChromaDB connection validation failed: {e}")
            return False
    
    @abstractmethod
    def _prepare_metadata(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare metadata for a single record.
        
        Must be implemented by entity-specific writers.
        
        Args:
            row: DataFrame row as dictionary
            
        Returns:
            Filtered and processed metadata dictionary
        """
        pass
    
    @abstractmethod
    def _get_collection_metadata(self) -> Dict[str, Any]:
        """
        Get collection-level metadata.
        
        Must be implemented by entity-specific writers.
        
        Returns:
            Collection metadata dictionary
        """
        pass
    
    def _generate_id(self, row: Dict[str, Any], index: int) -> str:
        """
        Generate a unique ID for an embedding.
        
        Can be overridden by entity-specific writers.
        
        Args:
            row: DataFrame row as dictionary
            index: Row index
            
        Returns:
            Unique identifier string
        """
        # Try to use entity-specific ID if available
        for id_field in ["listing_id", "neighborhood_id", "page_id"]:
            if id_field in row and row[id_field] is not None:
                return f"{id_field}_{row[id_field]}"
        
        # Fallback to UUID
        return str(uuid.uuid4())
    
    def _write_batch(self, batch_data: List[Dict[str, Any]]) -> bool:
        """
        Write a batch of embeddings to ChromaDB.
        
        Args:
            batch_data: List of records with embeddings and metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract components
            ids = []
            embeddings = []
            texts = []
            metadatas = []
            
            for i, row in enumerate(batch_data):
                # Skip records without embeddings
                if row.get("embeddings") is None:
                    continue
                
                # Generate ID
                record_id = self._generate_id(row, i)
                ids.append(record_id)
                
                # Extract embedding
                embedding = row["embeddings"]
                if isinstance(embedding, list):
                    embeddings.append(embedding)
                else:
                    self.logger.warning(f"Invalid embedding format for record {record_id}")
                    continue
                
                # Extract text
                text = row.get("embedding_text", "")
                texts.append(text)
                
                # Prepare metadata
                metadata = self._prepare_metadata(row)
                metadatas.append(metadata)
            
            if not ids:
                self.logger.warning("No valid embeddings in batch")
                return True
            
            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            
            self.logger.debug(f"Wrote batch of {len(ids)} embeddings")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write batch: {e}")
            return False
    
    def _convert_metadata_value(self, value: Any) -> Any:
        """
        Convert metadata value to ChromaDB-compatible format.
        
        Args:
            value: Original value
            
        Returns:
            Converted value
        """
        if value is None:
            return None
        elif isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, list):
            # ChromaDB doesn't support list metadata well, convert to string
            return str(value)
        else:
            return str(value)