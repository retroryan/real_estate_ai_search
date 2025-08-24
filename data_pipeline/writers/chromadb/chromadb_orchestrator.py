"""
ChromaDB writer orchestrator for entity-specific embedding storage.

This module provides a single orchestrator that routes entity-specific
DataFrames with embeddings to appropriate ChromaDB collections.
"""

import logging
from typing import Any, Dict, List

import chromadb
from chromadb.config import Settings
from pyspark.sql import DataFrame, SparkSession

from data_pipeline.writers.base import DataWriter
from .chromadb_config import ChromaDBWriterConfig

logger = logging.getLogger(__name__)


class ChromadbOrchestrator(DataWriter):
    """
    Orchestrator for entity-specific ChromaDB writing.
    
    Routes each entity type with embeddings to its dedicated collection.
    """
    
    def __init__(self, config: ChromaDBWriterConfig, spark: SparkSession):
        """
        Initialize the ChromaDB orchestrator.
        
        Args:
            config: ChromaDB configuration
            spark: SparkSession instance
        """
        super().__init__(config)
        self.config = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.config.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
    
    def validate_connection(self) -> bool:
        """
        Validate the connection to ChromaDB.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Try to list collections
            collections = self.client.list_collections()
            self.logger.info(f"Successfully connected to ChromaDB at {self.config.persist_directory}")
            self.logger.info(f"Found {len(collections)} existing collections")
            return True
            
        except Exception as e:
            self.logger.error(f"ChromaDB connection validation failed: {e}")
            return False
    
    def write(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write entity-specific DataFrame with embeddings to ChromaDB.
        
        Args:
            df: DataFrame with embeddings to write
            metadata: Metadata including entity_type
            
        Returns:
            True if write was successful, False otherwise
        """
        entity_type = metadata.get("entity_type", "").lower()
        
        if entity_type == "property":
            return self._write_properties(df, metadata)
        elif entity_type == "neighborhood":
            return self._write_neighborhoods(df, metadata)
        elif entity_type == "wikipedia":
            return self._write_wikipedia(df, metadata)
        else:
            self.logger.error(f"Unknown entity type: {entity_type}")
            return False
    
    def _write_properties(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write property embeddings to ChromaDB.
        
        Args:
            df: Property DataFrame with embeddings
            metadata: Write metadata
            
        Returns:
            True if successful
        """
        try:
            collection_name = f"{self.config.collection_prefix}_properties"
            
            # Get or create collection
            if self.config.clear_before_write:
                try:
                    self.client.delete_collection(collection_name)
                    self.logger.info(f"Cleared existing collection: {collection_name}")
                except:
                    pass
            
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"entity_type": "property"}
            )
            
            # Filter to rows with embeddings
            embedded_df = df.filter("embedding is not null")
            record_count = embedded_df.count()
            
            if record_count == 0:
                self.logger.warning("No property records with embeddings to write")
                return True
            
            self.logger.info(f"Writing {record_count} property embeddings to {collection_name}")
            
            # Collect data for batch insertion
            rows = embedded_df.select(
                "listing_id", "embedding", "embedding_text",
                "city", "state", "price", "bedrooms", "bathrooms",
                "square_feet", "property_type"
            ).collect()
            
            # Prepare batch data
            ids = []
            embeddings = []
            documents = []
            metadatas = []
            
            for row in rows:
                ids.append(row["listing_id"])
                embeddings.append(row["embedding"])
                documents.append(row["embedding_text"] or "")
                metadatas.append({
                    "city": row["city"],
                    "state": row["state"],
                    "price": float(row["price"]) if row["price"] else 0,
                    "bedrooms": int(row["bedrooms"]) if row["bedrooms"] else 0,
                    "bathrooms": float(row["bathrooms"]) if row["bathrooms"] else 0,
                    "square_feet": int(row["square_feet"]) if row["square_feet"] else 0,
                    "property_type": row["property_type"] or "unknown"
                })
            
            # Batch insert
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            self.logger.info(f"Successfully wrote {record_count} property embeddings")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write properties to ChromaDB: {e}")
            return False
    
    def _write_neighborhoods(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write neighborhood embeddings to ChromaDB.
        
        Args:
            df: Neighborhood DataFrame with embeddings
            metadata: Write metadata
            
        Returns:
            True if successful
        """
        try:
            collection_name = f"{self.config.collection_prefix}_neighborhoods"
            
            # Get or create collection
            if self.config.clear_before_write:
                try:
                    self.client.delete_collection(collection_name)
                    self.logger.info(f"Cleared existing collection: {collection_name}")
                except:
                    pass
            
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"entity_type": "neighborhood"}
            )
            
            # Filter to rows with embeddings
            embedded_df = df.filter("embedding is not null")
            record_count = embedded_df.count()
            
            if record_count == 0:
                self.logger.warning("No neighborhood records with embeddings to write")
                return True
            
            self.logger.info(f"Writing {record_count} neighborhood embeddings to {collection_name}")
            
            # Collect data for batch insertion
            rows = embedded_df.select(
                "neighborhood_id", "embedding", "embedding_text",
                "name", "city", "state", "population", "median_income"
            ).collect()
            
            # Prepare batch data
            ids = []
            embeddings = []
            documents = []
            metadatas = []
            
            for row in rows:
                ids.append(row["neighborhood_id"])
                embeddings.append(row["embedding"])
                documents.append(row["embedding_text"] or "")
                metadatas.append({
                    "name": row["name"],
                    "city": row["city"],
                    "state": row["state"],
                    "population": int(row["population"]) if row["population"] else 0,
                    "median_income": float(row["median_income"]) if row["median_income"] else 0
                })
            
            # Batch insert
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            self.logger.info(f"Successfully wrote {record_count} neighborhood embeddings")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write neighborhoods to ChromaDB: {e}")
            return False
    
    def _write_wikipedia(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write Wikipedia article embeddings to ChromaDB.
        
        Args:
            df: Wikipedia DataFrame with embeddings
            metadata: Write metadata
            
        Returns:
            True if successful
        """
        try:
            collection_name = f"{self.config.collection_prefix}_wikipedia"
            
            # Get or create collection
            if self.config.clear_before_write:
                try:
                    self.client.delete_collection(collection_name)
                    self.logger.info(f"Cleared existing collection: {collection_name}")
                except:
                    pass
            
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"entity_type": "wikipedia"}
            )
            
            # Filter to rows with embeddings
            embedded_df = df.filter("embedding is not null")
            record_count = embedded_df.count()
            
            if record_count == 0:
                self.logger.warning("No Wikipedia records with embeddings to write")
                return True
            
            self.logger.info(f"Writing {record_count} Wikipedia embeddings to {collection_name}")
            
            # Collect data for batch insertion
            rows = embedded_df.select(
                "page_id", "embedding", "embedding_text",
                "title", "best_city", "best_state", 
                "relevance_score", "confidence_score"
            ).collect()
            
            # Prepare batch data
            ids = []
            embeddings = []
            documents = []
            metadatas = []
            
            for row in rows:
                ids.append(str(row["page_id"]))
                embeddings.append(row["embedding"])
                documents.append(row["embedding_text"] or "")
                metadatas.append({
                    "title": row["title"],
                    "best_city": row["best_city"] or "",
                    "best_state": row["best_state"] or "",
                    "relevance_score": float(row["relevance_score"]) if row["relevance_score"] else 0,
                    "confidence_score": float(row["confidence_score"]) if row["confidence_score"] else 0
                })
            
            # Batch insert
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            self.logger.info(f"Successfully wrote {record_count} Wikipedia embeddings")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write Wikipedia to ChromaDB: {e}")
            return False
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "chromadb"
    
    def clear_data(self) -> None:
        """
        Clear all ChromaDB collections for this prefix.
        """
        try:
            for entity in ["properties", "neighborhoods", "wikipedia"]:
                collection_name = f"{self.config.collection_prefix}_{entity}"
                try:
                    self.client.delete_collection(collection_name)
                    self.logger.info(f"Deleted collection: {collection_name}")
                except:
                    pass
        except Exception as e:
            self.logger.warning(f"Failed to clear ChromaDB data: {e}")