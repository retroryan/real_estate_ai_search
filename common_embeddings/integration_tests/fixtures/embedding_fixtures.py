"""
Real embedding access for integration testing.

Provides utilities to access and validate actual pre-generated embeddings
stored in ChromaDB collections from the main embedding pipeline.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import chromadb
from chromadb.config import Settings

from ...models.enums import EntityType
from ...utils.logging import get_logger
from ..models import EmbeddingFixture, DataSample

logger = get_logger(__name__)


class RealEmbeddingAccessor:
    """
    Accessor for real pre-generated embeddings from production ChromaDB.
    
    Provides read-only access to embeddings that have been generated
    by the main embedding pipeline for integration testing validation.
    """
    
    def __init__(self, production_chromadb_path: str = None):
        """
        Initialize real embedding accessor.
        
        Args:
            production_chromadb_path: Path to production ChromaDB with pre-generated embeddings
        """
        self.production_db_path = production_chromadb_path or "./data/chromadb"
        self.client: Optional[chromadb.Client] = None
        
        logger.info(f"Initialized RealEmbeddingAccessor with production DB: {self.production_db_path}")
    
    def connect_to_production_db(self) -> bool:
        """
        Connect to production ChromaDB containing real embeddings.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if not os.path.exists(self.production_db_path):
                logger.error(f"Production ChromaDB path not found: {self.production_db_path}")
                return False
            
            self.client = chromadb.PersistentClient(
                path=self.production_db_path,
                settings=Settings(
                    allow_reset=False,  # Read-only access
                    anonymized_telemetry=False
                )
            )
            
            logger.info(f"Connected to production ChromaDB at: {self.production_db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to production ChromaDB: {e}")
            return False
    
    def list_available_collections(self) -> List[str]:
        """
        List all available collections in production ChromaDB.
        
        Returns:
            List of collection names
        """
        if not self.client:
            logger.error("Not connected to production ChromaDB")
            return []
        
        try:
            collections = self.client.list_collections()
            collection_names = [col.name for col in collections]
            logger.info(f"Found {len(collection_names)} collections: {collection_names}")
            return collection_names
            
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
    
    def get_embeddings_by_entity_type(
        self,
        collection_name: str,
        entity_type: EntityType,
        limit: int = 50
    ) -> List[Tuple[str, List[float], Dict[str, Any]]]:
        """
        Get real embeddings for a specific entity type from production collection.
        
        Args:
            collection_name: Name of the ChromaDB collection
            entity_type: Type of entity to filter by
            limit: Maximum number of embeddings to return
            
        Returns:
            List of tuples (embedding_id, vector, metadata)
        """
        if not self.client:
            logger.error("Not connected to production ChromaDB")
            return []
        
        try:
            collection = self.client.get_collection(collection_name)
            
            # Query with entity type filter
            results = collection.get(
                where={"entity_type": entity_type.value},
                limit=limit,
                include=['embeddings', 'metadatas', 'ids']
            )
            
            embeddings_data = []
            ids = results.get('ids', [])
            embeddings = results.get('embeddings', [])
            metadatas = results.get('metadatas', [])
            
            for i, embedding_id in enumerate(ids):
                if i < len(embeddings) and i < len(metadatas):
                    embeddings_data.append((
                        embedding_id,
                        embeddings[i],
                        metadatas[i]
                    ))
            
            logger.info(f"Retrieved {len(embeddings_data)} real embeddings for {entity_type.value}")
            return embeddings_data
            
        except Exception as e:
            logger.error(f"Failed to get embeddings from collection {collection_name}: {e}")
            return []
    
    def get_embeddings_by_ids(
        self,
        collection_name: str,
        embedding_ids: List[str]
    ) -> List[Tuple[str, List[float], Dict[str, Any]]]:
        """
        Get specific embeddings by their IDs from production collection.
        
        Args:
            collection_name: Name of the ChromaDB collection
            embedding_ids: List of embedding IDs to retrieve
            
        Returns:
            List of tuples (embedding_id, vector, metadata)
        """
        if not self.client:
            logger.error("Not connected to production ChromaDB")
            return []
        
        try:
            collection = self.client.get_collection(collection_name)
            
            results = collection.get(
                ids=embedding_ids,
                include=['embeddings', 'metadatas', 'ids']
            )
            
            embeddings_data = []
            ids = results.get('ids', [])
            embeddings = results.get('embeddings', [])
            metadatas = results.get('metadatas', [])
            
            for i, embedding_id in enumerate(ids):
                if i < len(embeddings) and i < len(metadatas):
                    embeddings_data.append((
                        embedding_id,
                        embeddings[i],
                        metadatas[i]
                    ))
            
            logger.info(f"Retrieved {len(embeddings_data)} embeddings by IDs")
            return embeddings_data
            
        except Exception as e:
            logger.error(f"Failed to get embeddings by IDs from collection {collection_name}: {e}")
            return []
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        Get statistics about a production collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dictionary with collection statistics
        """
        if not self.client:
            logger.error("Not connected to production ChromaDB")
            return {}
        
        try:
            collection = self.client.get_collection(collection_name)
            
            # Get basic collection info
            stats = {
                'collection_name': collection_name,
                'total_embeddings': collection.count(),
                'metadata': collection.metadata
            }
            
            # Get sample to analyze entity types
            sample_results = collection.get(
                limit=100,
                include=['metadatas']
            )
            
            # Analyze entity type distribution
            entity_types = {}
            source_files = set()
            
            for metadata in sample_results.get('metadatas', []):
                if metadata:
                    entity_type = metadata.get('entity_type', 'unknown')
                    entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
                    
                    if 'source_file' in metadata:
                        source_files.add(metadata['source_file'])
            
            stats['entity_type_distribution'] = entity_types
            stats['source_files'] = list(source_files)
            stats['sample_size'] = len(sample_results.get('metadatas', []))
            
            logger.info(f"Collection {collection_name} stats: {stats['total_embeddings']} embeddings")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get stats for collection {collection_name}: {e}")
            return {}
    
    def validate_embeddings_exist_for_samples(
        self,
        collection_name: str,
        samples: List[DataSample]
    ) -> Dict[str, bool]:
        """
        Validate that embeddings exist for given data samples.
        
        Args:
            collection_name: Name of the collection to check
            samples: List of data samples to validate
            
        Returns:
            Dictionary mapping sample entity_id to existence status
        """
        if not self.client:
            logger.error("Not connected to production ChromaDB")
            return {}
        
        results = {}
        
        try:
            collection = self.client.get_collection(collection_name)
            
            for sample in samples:
                # Try to find embedding by metadata matching
                entity_type = sample.entity_type
                entity_id = sample.entity_id
                
                # Build query based on entity type
                where_clause = {"entity_type": entity_type.value}
                
                if entity_type == EntityType.PROPERTY:
                    where_clause["listing_id"] = entity_id
                elif entity_type == EntityType.NEIGHBORHOOD:
                    where_clause["neighborhood_id"] = entity_id
                elif entity_type in [EntityType.WIKIPEDIA_ARTICLE, EntityType.WIKIPEDIA_SUMMARY]:
                    try:
                        where_clause["page_id"] = int(entity_id)
                    except ValueError:
                        where_clause["page_id"] = entity_id
                
                # Query collection
                query_results = collection.get(
                    where=where_clause,
                    limit=1,
                    include=['ids']
                )
                
                exists = len(query_results.get('ids', [])) > 0
                results[entity_id] = exists
                
                if not exists:
                    logger.warning(f"No embedding found for {entity_type.value} {entity_id}")
            
            found_count = sum(1 for exists in results.values() if exists)
            logger.info(f"Validation complete: {found_count}/{len(samples)} samples have embeddings")
            
        except Exception as e:
            logger.error(f"Failed to validate embeddings for samples: {e}")
        
        return results
    
    def find_multi_chunk_documents(
        self,
        collection_name: str,
        entity_type: Optional[EntityType] = None
    ) -> Dict[str, List[str]]:
        """
        Find documents that were split into multiple chunks.
        
        Args:
            collection_name: Name of the collection to search
            entity_type: Optional entity type filter
            
        Returns:
            Dictionary mapping parent_hash to list of chunk embedding IDs
        """
        if not self.client:
            logger.error("Not connected to production ChromaDB")
            return {}
        
        try:
            collection = self.client.get_collection(collection_name)
            
            # Build where clause
            where_clause = {}
            if entity_type:
                where_clause["entity_type"] = entity_type.value
            
            # Get all embeddings with chunk information
            results = collection.get(
                where=where_clause,
                include=['metadatas', 'ids']
            )
            
            # Group by parent_hash
            chunk_groups = {}
            ids = results.get('ids', [])
            metadatas = results.get('metadatas', [])
            
            for i, embedding_id in enumerate(ids):
                if i < len(metadatas) and metadatas[i]:
                    metadata = metadatas[i]
                    parent_hash = metadata.get('parent_hash')
                    
                    if parent_hash and 'chunk_index' in metadata:
                        if parent_hash not in chunk_groups:
                            chunk_groups[parent_hash] = []
                        chunk_groups[parent_hash].append(embedding_id)
            
            # Filter to only multi-chunk documents
            multi_chunk_docs = {
                parent_hash: chunks 
                for parent_hash, chunks in chunk_groups.items() 
                if len(chunks) > 1
            }
            
            logger.info(f"Found {len(multi_chunk_docs)} multi-chunk documents")
            return multi_chunk_docs
            
        except Exception as e:
            logger.error(f"Failed to find multi-chunk documents: {e}")
            return {}
    
    def disconnect(self) -> None:
        """Disconnect from production ChromaDB."""
        if self.client:
            self.client = None
            logger.info("Disconnected from production ChromaDB")
    
    def __enter__(self):
        """Context manager entry."""
        if not self.connect_to_production_db():
            raise RuntimeError("Failed to connect to production ChromaDB")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False


class EmbeddingValidationHelper:
    """
    Helper utilities for validating real embedding data quality.
    
    Provides methods to check embedding characteristics, metadata consistency,
    and data integrity for integration testing.
    """
    
    @staticmethod
    def validate_embedding_vector(embedding: List[float]) -> Dict[str, Any]:
        """
        Validate characteristics of an embedding vector.
        
        Args:
            embedding: The embedding vector to validate
            
        Returns:
            Dictionary with validation results
        """
        import numpy as np
        
        vector = np.array(embedding)
        
        validation = {
            'is_valid': True,
            'dimension': len(embedding),
            'is_normalized': False,
            'has_nan_values': False,
            'has_inf_values': False,
            'magnitude': 0.0,
            'mean': 0.0,
            'std': 0.0,
            'issues': []
        }
        
        # Check for invalid values
        if np.isnan(vector).any():
            validation['has_nan_values'] = True
            validation['is_valid'] = False
            validation['issues'].append("Contains NaN values")
        
        if np.isinf(vector).any():
            validation['has_inf_values'] = True
            validation['is_valid'] = False
            validation['issues'].append("Contains infinite values")
        
        # Calculate statistics
        if validation['is_valid']:
            validation['magnitude'] = float(np.linalg.norm(vector))
            validation['mean'] = float(np.mean(vector))
            validation['std'] = float(np.std(vector))
            
            # Check if normalized (magnitude close to 1.0)
            validation['is_normalized'] = abs(validation['magnitude'] - 1.0) < 0.01
        
        # Check dimension
        if validation['dimension'] < 50 or validation['dimension'] > 2000:
            validation['issues'].append(f"Unusual dimension: {validation['dimension']}")
        
        return validation
    
    @staticmethod
    def validate_metadata_consistency(metadatas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate metadata consistency across embeddings.
        
        Args:
            metadatas: List of metadata dictionaries to validate
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'is_consistent': True,
            'total_count': len(metadatas),
            'missing_required_fields': [],
            'entity_type_distribution': {},
            'source_file_distribution': {},
            'issues': []
        }
        
        required_fields = ['embedding_id', 'entity_type', 'source_file', 'text_hash']
        missing_field_counts = {field: 0 for field in required_fields}
        
        for metadata in metadatas:
            if not metadata:
                validation['issues'].append("Found null metadata")
                continue
            
            # Check required fields
            for field in required_fields:
                if field not in metadata or metadata[field] is None:
                    missing_field_counts[field] += 1
            
            # Track distributions
            entity_type = metadata.get('entity_type', 'unknown')
            validation['entity_type_distribution'][entity_type] = \
                validation['entity_type_distribution'].get(entity_type, 0) + 1
            
            source_file = metadata.get('source_file', 'unknown')
            validation['source_file_distribution'][source_file] = \
                validation['source_file_distribution'].get(source_file, 0) + 1
        
        # Report missing fields
        for field, count in missing_field_counts.items():
            if count > 0:
                validation['missing_required_fields'].append({
                    'field': field,
                    'missing_count': count,
                    'percentage': (count / len(metadatas)) * 100
                })
                validation['is_consistent'] = False
                validation['issues'].append(f"Field '{field}' missing in {count} records")
        
        return validation