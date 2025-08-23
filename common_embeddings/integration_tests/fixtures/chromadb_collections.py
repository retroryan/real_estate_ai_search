"""
ChromaDB test collection management utilities.

Provides isolated ChromaDB collections for integration testing with proper
setup, teardown, and health monitoring capabilities.
"""

import os
import shutil
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
import uuid

import chromadb
from chromadb.config import Settings

from ...models.enums import EntityType
from ...utils.logging import get_logger
from ..models import CollectionTestState, ValidationError, TestConfiguration

logger = get_logger(__name__)


class ChromaDBTestCollectionManager:
    """
    Manager for ChromaDB test collections.
    
    Provides isolated test environment with collection lifecycle management,
    health monitoring, and proper cleanup.
    """
    
    def __init__(self, config: TestConfiguration):
        """
        Initialize ChromaDB test collection manager.
        
        Args:
            config: Test configuration specifying ChromaDB settings
        """
        self.config = config
        self.test_session_id = str(uuid.uuid4())[:8]
        
        # ChromaDB client setup
        self.client: Optional[chromadb.Client] = None
        self.active_collections: Dict[str, CollectionTestState] = {}
        self.validation_errors: List[ValidationError] = []
        
        # Test isolation
        self.test_db_path = os.path.join(config.chromadb_path, f"test_session_{self.test_session_id}")
        
        logger.info(f"Initialized ChromaDB test manager with session ID: {self.test_session_id}")
        logger.info(f"Test database path: {self.test_db_path}")
    
    def setup_test_environment(self) -> bool:
        """
        Set up isolated ChromaDB test environment.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            # Ensure test directory exists
            Path(self.test_db_path).mkdir(parents=True, exist_ok=True)
            
            # Initialize ChromaDB client with test-specific settings
            self.client = chromadb.PersistentClient(
                path=self.test_db_path,
                settings=Settings(
                    allow_reset=True,
                    anonymized_telemetry=False
                )
            )
            
            logger.info(f"ChromaDB test environment set up at: {self.test_db_path}")
            return True
            
        except Exception as e:
            error = ValidationError(
                error_type="test_setup_error",
                error_message=f"Failed to set up ChromaDB test environment: {e}",
                context={"db_path": self.test_db_path, "error": str(e)},
                is_critical=True
            )
            self.validation_errors.append(error)
            logger.error(f"ChromaDB test setup failed: {e}")
            return False
    
    def create_test_collection(
        self,
        base_name: str,
        entity_type: EntityType,
        embedding_function: Optional[Any] = None
    ) -> Optional[str]:
        """
        Create a test collection with proper naming and tracking.
        
        Args:
            base_name: Base name for the collection
            entity_type: Primary entity type for the collection
            embedding_function: ChromaDB embedding function to use
            
        Returns:
            Collection name if created successfully, None otherwise
        """
        if not self.client:
            logger.error("ChromaDB client not initialized")
            return None
        
        # Generate test collection name
        collection_name = f"{self.config.test_collection_prefix}{base_name}_{self.test_session_id}"
        
        try:
            # Create collection
            collection = self.client.create_collection(
                name=collection_name,
                embedding_function=embedding_function,
                metadata={"entity_type": entity_type.value, "test_session": self.test_session_id}
            )
            
            # Track collection state
            collection_state = CollectionTestState(
                collection_name=collection_name,
                entity_type=entity_type,
                total_embeddings=0,
                unique_entities=0,
                chunk_groups=0
            )
            
            self.active_collections[collection_name] = collection_state
            
            logger.info(f"Created test collection: {collection_name}")
            return collection_name
            
        except Exception as e:
            error = ValidationError(
                error_type="collection_creation_error",
                error_message=f"Failed to create collection '{collection_name}': {e}",
                context={"collection_name": collection_name, "entity_type": entity_type.value},
                is_critical=True
            )
            self.validation_errors.append(error)
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return None
    
    def add_embeddings_to_collection(
        self,
        collection_name: str,
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> bool:
        """
        Add embeddings to a test collection with state tracking.
        
        Args:
            collection_name: Name of the collection
            embeddings: List of embedding vectors
            documents: List of document texts
            metadatas: List of metadata dictionaries
            ids: List of embedding IDs
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.error("ChromaDB client not initialized")
            return False
        
        if collection_name not in self.active_collections:
            logger.error(f"Collection {collection_name} not found in active collections")
            return False
        
        try:
            collection = self.client.get_collection(collection_name)
            
            # Add embeddings
            collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            # Update collection state
            state = self.active_collections[collection_name]
            state.test_embeddings_added += len(embeddings)
            state.total_embeddings += len(embeddings)
            
            # Count unique entities
            entity_ids = set()
            chunk_parents = set()
            
            for metadata in metadatas:
                # Extract entity identifier based on type
                if state.entity_type == EntityType.PROPERTY:
                    if 'listing_id' in metadata:
                        entity_ids.add(metadata['listing_id'])
                elif state.entity_type == EntityType.NEIGHBORHOOD:
                    if 'neighborhood_id' in metadata:
                        entity_ids.add(metadata['neighborhood_id'])
                elif state.entity_type in [EntityType.WIKIPEDIA_ARTICLE, EntityType.WIKIPEDIA_SUMMARY]:
                    if 'page_id' in metadata:
                        entity_ids.add(str(metadata['page_id']))
                
                # Track chunk groups
                if 'parent_hash' in metadata:
                    chunk_parents.add(metadata['parent_hash'])
            
            state.unique_entities = len(entity_ids)
            state.chunk_groups = len(chunk_parents)
            
            logger.info(f"Added {len(embeddings)} embeddings to collection {collection_name}")
            return True
            
        except Exception as e:
            error = ValidationError(
                error_type="embedding_storage_error",
                error_message=f"Failed to add embeddings to collection '{collection_name}': {e}",
                context={"collection_name": collection_name, "embedding_count": len(embeddings)},
                is_critical=True
            )
            self.validation_errors.append(error)
            logger.error(f"Failed to add embeddings to {collection_name}: {e}")
            return False
    
    def query_collection(
        self,
        collection_name: str,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Query a test collection with state tracking.
        
        Args:
            collection_name: Name of the collection to query
            query_texts: Query texts for similarity search
            query_embeddings: Query embeddings for similarity search
            n_results: Number of results to return
            where: Where clause for filtering
            include: Fields to include in results
            
        Returns:
            Query results or None if failed
        """
        if not self.client:
            logger.error("ChromaDB client not initialized")
            return None
        
        if collection_name not in self.active_collections:
            logger.error(f"Collection {collection_name} not found in active collections")
            return None
        
        try:
            collection = self.client.get_collection(collection_name)
            
            # Perform query
            results = collection.query(
                query_texts=query_texts,
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where,
                include=include or ['documents', 'metadatas', 'distances']
            )
            
            # Update state
            state = self.active_collections[collection_name]
            state.test_queries_executed += 1
            
            logger.debug(f"Executed query on collection {collection_name}, got {len(results.get('ids', [[]]))} result groups")
            return results
            
        except Exception as e:
            error = ValidationError(
                error_type="query_execution_error",
                error_message=f"Failed to query collection '{collection_name}': {e}",
                context={"collection_name": collection_name, "n_results": n_results},
                is_critical=False
            )
            self.validation_errors.append(error)
            logger.error(f"Failed to query collection {collection_name}: {e}")
            return None
    
    def get_collection_state(self, collection_name: str) -> Optional[CollectionTestState]:
        """
        Get current state of a test collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection state or None if not found
        """
        return self.active_collections.get(collection_name)
    
    def analyze_collection_health(self, collection_name: str) -> CollectionTestState:
        """
        Analyze collection health and update state.
        
        Args:
            collection_name: Name of the collection to analyze
            
        Returns:
            Updated collection state with health information
        """
        if collection_name not in self.active_collections:
            logger.error(f"Collection {collection_name} not found")
            return None
        
        state = self.active_collections[collection_name]
        
        if not self.client:
            logger.error("ChromaDB client not initialized")
            return state
        
        try:
            collection = self.client.get_collection(collection_name)
            
            # Get all data for analysis
            all_data = collection.get(
                include=['metadatas', 'documents', 'ids']
            )
            
            # Analyze for health issues
            ids = all_data.get('ids', [])
            metadatas = all_data.get('metadatas', [])
            documents = all_data.get('documents', [])
            
            # Check for duplicates (by text hash)
            text_hashes = []
            duplicate_count = 0
            for metadata in metadatas:
                if metadata and 'text_hash' in metadata:
                    text_hash = metadata['text_hash']
                    if text_hash in text_hashes:
                        duplicate_count += 1
                    else:
                        text_hashes.append(text_hash)
            
            state.has_duplicates = duplicate_count > 0
            
            # Check for orphaned chunks (chunks without parent references)
            orphaned_chunks = 0
            chunk_parents = set()
            for metadata in metadatas:
                if metadata and 'chunk_index' in metadata:
                    if 'parent_hash' not in metadata or not metadata['parent_hash']:
                        orphaned_chunks += 1
                    else:
                        chunk_parents.add(metadata['parent_hash'])
            
            state.has_orphaned_chunks = orphaned_chunks > 0
            
            # Check for missing metadata
            missing_metadata_count = 0
            for metadata in metadatas:
                if not metadata or 'entity_type' not in metadata:
                    missing_metadata_count += 1
                    continue
                
                # Check entity-specific required fields
                entity_type = metadata.get('entity_type')
                if entity_type == EntityType.PROPERTY.value and 'listing_id' not in metadata:
                    missing_metadata_count += 1
                elif entity_type == EntityType.NEIGHBORHOOD.value and 'neighborhood_id' not in metadata:
                    missing_metadata_count += 1
                elif entity_type in [EntityType.WIKIPEDIA_ARTICLE.value, EntityType.WIKIPEDIA_SUMMARY.value] and 'page_id' not in metadata:
                    missing_metadata_count += 1
            
            state.has_missing_metadata = missing_metadata_count > 0
            
            # Update counts
            state.total_embeddings = len(ids)
            state.chunk_groups = len(chunk_parents)
            
            logger.info(f"Collection {collection_name} health analysis: score={state.health_score:.2f}")
            return state
            
        except Exception as e:
            error = ValidationError(
                error_type="health_analysis_error",
                error_message=f"Failed to analyze collection health for '{collection_name}': {e}",
                context={"collection_name": collection_name},
                is_critical=False
            )
            self.validation_errors.append(error)
            logger.error(f"Health analysis failed for {collection_name}: {e}")
            return state
    
    def list_collections(self) -> List[str]:
        """
        List all active test collections.
        
        Returns:
            List of collection names
        """
        return list(self.active_collections.keys())
    
    def cleanup_test_collections(self) -> bool:
        """
        Clean up all test collections and data.
        
        Returns:
            True if cleanup successful, False otherwise
        """
        if not self.config.cleanup_collections:
            logger.info("Collection cleanup disabled, skipping")
            return True
        
        success = True
        
        # Delete collections from ChromaDB
        if self.client:
            for collection_name in list(self.active_collections.keys()):
                try:
                    self.client.delete_collection(collection_name)
                    logger.info(f"Deleted collection: {collection_name}")
                except Exception as e:
                    logger.error(f"Failed to delete collection {collection_name}: {e}")
                    success = False
        
        # Clear tracking
        self.active_collections.clear()
        
        # Remove test database directory
        if os.path.exists(self.test_db_path):
            try:
                shutil.rmtree(self.test_db_path)
                logger.info(f"Removed test database directory: {self.test_db_path}")
            except Exception as e:
                logger.error(f"Failed to remove test database directory: {e}")
                success = False
        
        # Close client
        if self.client:
            self.client = None
        
        logger.info(f"Collection cleanup completed (success={success})")
        return success
    
    def get_validation_errors(self) -> List[ValidationError]:
        """Get list of validation errors encountered."""
        return self.validation_errors.copy()
    
    def reset_client(self) -> bool:
        """
        Reset ChromaDB client (useful for testing error scenarios).
        
        Returns:
            True if reset successful, False otherwise
        """
        try:
            if self.client:
                self.client.reset()
                logger.info("ChromaDB client reset successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to reset ChromaDB client: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry."""
        if not self.setup_test_environment():
            raise RuntimeError("Failed to set up ChromaDB test environment")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup_test_collections()
        return False