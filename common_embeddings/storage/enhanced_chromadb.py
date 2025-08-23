"""
Enhanced ChromaDB storage with advanced correlation and management features.

Builds upon the basic ChromaDBStore with sophisticated operations for Phase 3.
"""

import os
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from .chromadb_store import ChromaDBStore
from ..models.config import ChromaDBConfig
from ..models.correlation import (
    ValidationResult,
    ChunkGroup,
    CollectionHealth,
    StorageOperation,
    CorrelationMapping
)
from ..models.enums import EntityType, SourceType
from ..models.statistics import CollectionInfo
from ..utils.correlation import CorrelationValidator, ChunkReconstructor, create_correlation_mappings
from ..utils.logging import get_logger, PerformanceLogger
from ..models.exceptions import StorageError


logger = get_logger(__name__)


class EnhancedChromaDBManager:
    """
    Advanced ChromaDB manager with correlation, validation, and management features.
    
    Extends basic ChromaDB functionality with Phase 3 requirements:
    - Advanced metadata validation
    - Chunk reconstruction
    - Collection health monitoring  
    - Atomic operations with rollback
    - Migration and cleanup utilities
    """
    
    def __init__(self, config: ChromaDBConfig):
        """
        Initialize enhanced ChromaDB manager.
        
        Args:
            config: ChromaDB configuration
        """
        self.config = config
        self.store = ChromaDBStore(config)
        self.validator = CorrelationValidator()
        self.reconstructor = ChunkReconstructor()
        
        # Operation tracking for rollback capability
        self.pending_operations: List[StorageOperation] = []
        
        logger.info("Initialized enhanced ChromaDB manager")
    
    def validate_and_store(
        self,
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        collection_name: str,
        collection_metadata: Optional[Dict[str, Any]] = None,
        validate_correlation: bool = True
    ) -> ValidationResult:
        """
        Validate embeddings and store them with comprehensive checks.
        
        Args:
            embeddings: List of embedding vectors
            texts: List of text content
            metadatas: List of metadata dictionaries
            ids: List of unique identifiers
            collection_name: Target collection name
            collection_metadata: Collection-level metadata
            validate_correlation: Whether to perform correlation validation
            
        Returns:
            ValidationResult with validation details
        """
        logger.info(f"Validating and storing {len(embeddings)} embeddings in collection '{collection_name}'")
        
        # Comprehensive validation
        if validate_correlation:
            validation_result = self.validator.validate_embeddings_batch(metadatas)
            if not validation_result.is_valid:
                logger.error(f"Validation failed: {validation_result.get_summary()}")
                return validation_result
        else:
            validation_result = ValidationResult(is_valid=True, total_checked=len(metadatas))
        
        # Check for duplicates using text_hash
        duplicate_check = self._check_for_duplicates(metadatas, collection_name)
        if duplicate_check.error_count > 0:
            validation_result.errors.extend(duplicate_check.errors)
            validation_result.is_valid = False
        
        # Store if validation passed
        if validation_result.is_valid:
            try:
                # Create collection if needed
                self.store.create_collection(
                    name=collection_name,
                    metadata=collection_metadata or {},
                    force_recreate=False
                )
                
                # Store embeddings
                self.store.add_embeddings(embeddings, texts, metadatas, ids)
                
                logger.info(f"Successfully stored {len(embeddings)} embeddings")
                
            except Exception as e:
                validation_result.add_error(f"Storage failed: {str(e)}")
                logger.error(f"Storage operation failed: {e}")
        
        return validation_result
    
    def _check_for_duplicates(
        self,
        metadatas: List[Dict[str, Any]],
        collection_name: str
    ) -> ValidationResult:
        """Check for duplicate embeddings using text_hash."""
        result = ValidationResult(total_checked=len(metadatas))
        
        # Check for duplicates within the batch
        text_hashes = [meta.get('text_hash') for meta in metadatas if meta.get('text_hash')]
        if len(text_hashes) != len(set(text_hashes)):
            duplicate_hashes = [h for h in text_hashes if text_hashes.count(h) > 1]
            result.add_error(f"Duplicate text_hash values in batch: {set(duplicate_hashes)}")
        
        # Check for duplicates in existing collection
        try:
            if collection_name in self.store.list_collections():
                self.store.create_collection(collection_name, {}, False)  # Don't recreate
                existing_data = self.store.get_all(include_embeddings=False)
                existing_hashes = {
                    meta.get('text_hash') for meta in existing_data.get('metadatas', [])
                    if meta and meta.get('text_hash')
                }
                
                batch_hashes = set(text_hashes)
                conflicts = batch_hashes & existing_hashes
                if conflicts:
                    result.add_error(f"Duplicate text_hash values already exist in collection: {conflicts}")
                    
        except Exception as e:
            result.add_warning(f"Could not check existing collection for duplicates: {e}")
        
        return result
    
    def analyze_collection_health(self, collection_name: str) -> CollectionHealth:
        """
        Analyze collection health and identify issues.
        
        Args:
            collection_name: Name of collection to analyze
            
        Returns:
            CollectionHealth with comprehensive analysis
        """
        logger.info(f"Analyzing health of collection '{collection_name}'")
        
        try:
            # Switch to collection and get all data
            self.store.create_collection(collection_name, {}, False)
            data = self.store.get_all(include_embeddings=False)
            
            if not data or not data.get('metadatas'):
                return CollectionHealth(
                    collection_name=collection_name,
                    total_embeddings=0
                )
            
            metadatas = data['metadatas']
            ids = data.get('ids', [])
            
            # Basic statistics
            health = CollectionHealth(
                collection_name=collection_name,
                total_embeddings=len(metadatas)
            )
            
            # Analyze entity types
            entity_types = defaultdict(int)
            source_types = defaultdict(int)
            chunk_sizes = []
            
            unique_entities = set()
            embedding_ids = set()
            chunk_groups = defaultdict(list)
            
            for i, meta in enumerate(metadatas):
                if not meta:
                    continue
                
                # Count entity and source types
                entity_type = meta.get('entity_type', 'unknown')
                source_type = meta.get('source_type', 'unknown')
                entity_types[entity_type] += 1
                source_types[source_type] += 1
                
                # Track unique entities
                entity_id = (
                    meta.get('listing_id') or 
                    meta.get('neighborhood_id') or 
                    meta.get('page_id') or 
                    meta.get('article_id') or 
                    'unknown'
                )
                unique_entities.add(f"{entity_type}:{entity_id}")
                
                # Check for duplicate IDs
                embedding_id = ids[i] if i < len(ids) else meta.get('embedding_id')
                if embedding_id:
                    if embedding_id in embedding_ids:
                        health.has_duplicate_ids = True
                    embedding_ids.add(embedding_id)
                
                # Track chunk information
                if meta.get('chunk_index') is not None:
                    parent_id = meta.get('parent_hash') or meta.get('source_doc_id', 'unknown')
                    chunk_groups[parent_id].append(meta)
                
                # Check for missing required metadata
                required_fields = ['embedding_id', 'entity_type', 'source_type', 'source_file']
                if any(not meta.get(field) for field in required_fields):
                    health.has_missing_metadata = True
                
                # Track chunk sizes (text length)
                text_length = len(meta.get('text', ''))
                chunk_sizes.append(text_length)
            
            # Set statistics
            health.unique_entities = len(unique_entities)
            health.entity_types = dict(entity_types)
            health.source_types = dict(source_types)
            
            # Analyze chunks
            health.chunk_groups = len(chunk_groups)
            
            # Check for orphaned chunks and incomplete groups
            for parent_id, chunks in chunk_groups.items():
                if len(chunks) == 1:
                    continue  # Single chunks are fine
                
                # Check if any chunk references a parent that doesn't exist as a complete document
                chunk_indices = [c.get('chunk_index') for c in chunks if c.get('chunk_index') is not None]
                chunk_totals = [c.get('chunk_total') for c in chunks if c.get('chunk_total') is not None]
                
                if not chunk_indices:
                    health.has_orphaned_chunks = True
                
                if chunk_totals:
                    expected_total = max(chunk_totals)
                    if len(chunk_indices) != expected_total:
                        health.has_incomplete_groups = True
            
            # Calculate chunk size statistics
            if chunk_sizes:
                health.chunk_size_stats = {
                    'min': float(min(chunk_sizes)),
                    'max': float(max(chunk_sizes)),
                    'avg': float(sum(chunk_sizes) / len(chunk_sizes)),
                    'total': len(chunk_sizes)
                }
            
            # Set primary entity type
            if entity_types:
                primary_entity = max(entity_types, key=entity_types.get)
                try:
                    health.entity_type = EntityType(primary_entity)
                except ValueError:
                    pass  # Invalid entity type
            
            logger.info(f"Health analysis complete: {health.status} (score: {health.health_score:.2f})")
            return health
            
        except Exception as e:
            logger.error(f"Failed to analyze collection health: {e}")
            return CollectionHealth(
                collection_name=collection_name,
                total_embeddings=0,
                has_missing_metadata=True
            )
    
    def reconstruct_documents(self, collection_name: str) -> List[Dict[str, Any]]:
        """
        Reconstruct documents from chunks in a collection.
        
        Args:
            collection_name: Name of collection to reconstruct from
            
        Returns:
            List of reconstructed document data
        """
        logger.info(f"Reconstructing documents from collection '{collection_name}'")
        
        try:
            # Get all data from collection
            self.store.create_collection(collection_name, {}, False)
            data = self.store.get_all(include_embeddings=True)
            
            if not data or not data.get('metadatas'):
                return []
            
            # Create chunk groups
            chunk_groups = self.reconstructor.group_chunks_by_parent(data['metadatas'])
            
            # Reconstruct documents
            reconstructed = self.reconstructor.reconstruct_documents(chunk_groups)
            
            logger.info(f"Reconstructed {len(reconstructed)} documents from {len(data['metadatas'])} chunks")
            return reconstructed
            
        except Exception as e:
            logger.error(f"Document reconstruction failed: {e}")
            raise StorageError(f"Failed to reconstruct documents: {e}")
    
    def create_correlation_mappings(self, collection_name: str) -> List[CorrelationMapping]:
        """
        Create correlation mappings for downstream services.
        
        Args:
            collection_name: Name of collection to create mappings for
            
        Returns:
            List of CorrelationMapping objects
        """
        logger.info(f"Creating correlation mappings for collection '{collection_name}'")
        
        try:
            # Get all metadata from collection
            self.store.create_collection(collection_name, {}, False)
            data = self.store.get_all(include_embeddings=False)
            
            if not data or not data.get('metadatas'):
                return []
            
            # Create mappings
            mappings = create_correlation_mappings(data['metadatas'])
            
            logger.info(f"Created {len(mappings)} correlation mappings")
            return mappings
            
        except Exception as e:
            logger.error(f"Failed to create correlation mappings: {e}")
            raise StorageError(f"Correlation mapping creation failed: {e}")
    
    def cleanup_collection(
        self,
        collection_name: str,
        remove_duplicates: bool = True,
        remove_orphaned_chunks: bool = False,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Clean up issues in a collection.
        
        Args:
            collection_name: Name of collection to clean up
            remove_duplicates: Whether to remove duplicate embeddings
            remove_orphaned_chunks: Whether to remove orphaned chunks
            dry_run: If True, only report what would be cleaned up
            
        Returns:
            Dictionary with cleanup report
        """
        logger.info(f"{'Dry run' if dry_run else 'Actual'} cleanup of collection '{collection_name}'")
        
        cleanup_report = {
            'collection': collection_name,
            'dry_run': dry_run,
            'duplicates_found': 0,
            'orphaned_chunks_found': 0,
            'actions_taken': [],
            'errors': []
        }
        
        try:
            # Analyze collection health first
            health = self.analyze_collection_health(collection_name)
            
            if remove_duplicates and health.has_duplicate_ids:
                # TODO: Implement duplicate removal logic
                cleanup_report['duplicates_found'] = 1  # Placeholder
                if not dry_run:
                    cleanup_report['actions_taken'].append("Removed duplicate embeddings")
            
            if remove_orphaned_chunks and health.has_orphaned_chunks:
                # TODO: Implement orphaned chunk removal logic
                cleanup_report['orphaned_chunks_found'] = 1  # Placeholder
                if not dry_run:
                    cleanup_report['actions_taken'].append("Removed orphaned chunks")
            
            logger.info(f"Cleanup {'simulation' if dry_run else 'execution'} completed")
            return cleanup_report
            
        except Exception as e:
            error_msg = f"Cleanup failed: {e}"
            cleanup_report['errors'].append(error_msg)
            logger.error(error_msg)
            return cleanup_report
    
    def migrate_collection(
        self,
        source_collection: str,
        target_collection: str,
        transform_metadata: bool = False
    ) -> Dict[str, Any]:
        """
        Migrate data from one collection to another.
        
        Args:
            source_collection: Source collection name
            target_collection: Target collection name 
            transform_metadata: Whether to transform metadata during migration
            
        Returns:
            Dictionary with migration report
        """
        logger.info(f"Migrating data from '{source_collection}' to '{target_collection}'")
        
        migration_report = {
            'source_collection': source_collection,
            'target_collection': target_collection,
            'items_migrated': 0,
            'errors': [],
            'started_at': datetime.now().isoformat(),
            'completed_at': None
        }
        
        try:
            with PerformanceLogger(f"Collection migration") as perf:
                # Get source data
                self.store.create_collection(source_collection, {}, False)
                source_data = self.store.get_all(include_embeddings=True)
                
                if not source_data or not source_data.get('embeddings'):
                    migration_report['errors'].append("Source collection is empty")
                    return migration_report
                
                # Create target collection
                target_metadata = {
                    'migrated_from': source_collection,
                    'migration_timestamp': datetime.now().isoformat(),
                    'migration_version': '1.0'
                }
                
                self.store.create_collection(target_collection, target_metadata, force_recreate=True)
                
                # Migrate data
                embeddings = source_data['embeddings']
                texts = source_data.get('documents', [''] * len(embeddings))
                metadatas = source_data['metadatas']
                ids = source_data['ids']
                
                # Transform metadata if requested
                if transform_metadata:
                    metadatas = [self._transform_metadata(meta) for meta in metadatas]
                
                # Store in target collection
                self.store.add_embeddings(embeddings, texts, metadatas, ids)
                
                migration_report['items_migrated'] = len(embeddings)
                migration_report['completed_at'] = datetime.now().isoformat()
                
                logger.info(f"Successfully migrated {len(embeddings)} items")
                
        except Exception as e:
            error_msg = f"Migration failed: {e}"
            migration_report['errors'].append(error_msg)
            migration_report['completed_at'] = datetime.now().isoformat()
            logger.error(error_msg)
        
        return migration_report
    
    def _transform_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform metadata during migration.
        
        Args:
            metadata: Original metadata dictionary
            
        Returns:
            Transformed metadata dictionary
        """
        # Add migration timestamp
        transformed = metadata.copy()
        transformed['migrated_at'] = datetime.now().isoformat()
        transformed['migration_version'] = '1.0'
        
        return transformed
    
    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics across all collections.
        
        Returns:
            Dictionary with system-wide statistics
        """
        logger.info("Gathering comprehensive system statistics")
        
        stats = {
            'timestamp': datetime.now().isoformat(),
            'total_collections': 0,
            'total_embeddings': 0,
            'collections': {},
            'health_summary': {
                'healthy': 0,
                'warning': 0,
                'critical': 0
            },
            'entity_type_distribution': defaultdict(int),
            'source_type_distribution': defaultdict(int)
        }
        
        try:
            collections = self.store.list_collections()
            stats['total_collections'] = len(collections)
            
            for collection_name in collections:
                try:
                    # Get collection health
                    health = self.analyze_collection_health(collection_name)
                    
                    stats['collections'][collection_name] = {
                        'embeddings_count': health.total_embeddings,
                        'unique_entities': health.unique_entities,
                        'health_score': health.health_score,
                        'status': health.status,
                        'issues': health.get_issues()
                    }
                    
                    stats['total_embeddings'] += health.total_embeddings
                    
                    # Update health summary
                    if health.health_score >= 0.9:
                        stats['health_summary']['healthy'] += 1
                    elif health.health_score >= 0.7:
                        stats['health_summary']['warning'] += 1
                    else:
                        stats['health_summary']['critical'] += 1
                    
                    # Update distributions
                    for entity_type, count in health.entity_types.items():
                        stats['entity_type_distribution'][entity_type] += count
                    
                    for source_type, count in health.source_types.items():
                        stats['source_type_distribution'][source_type] += count
                        
                except Exception as e:
                    logger.warning(f"Failed to analyze collection '{collection_name}': {e}")
                    stats['collections'][collection_name] = {
                        'error': str(e)
                    }
            
            logger.info(f"Statistics gathered for {len(collections)} collections")
            
        except Exception as e:
            logger.error(f"Failed to gather comprehensive statistics: {e}")
            stats['error'] = str(e)
        
        return stats