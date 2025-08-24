"""
Correlation utilities for advanced metadata validation and chunk reconstruction.

Enhanced validation and reconstruction capabilities for ChromaDB operations.
"""

import os
from typing import List, Dict, Any, Set, Optional, Tuple
from pathlib import Path
from collections import defaultdict

from ..models import (
    ValidationResult,
    ChunkGroup,
    CorrelationMapping,
    CollectionHealth,
    EntityType,
    SourceType,
    BaseMetadata,
)
from ..utils.logging import get_logger


logger = get_logger(__name__)


class CorrelationValidator:
    """
    Advanced validator for correlation metadata and chunk sequences.
    
    Provides comprehensive validation beyond basic field checking.
    """
    
    def __init__(self):
        """Initialize correlation validator."""
        self.seen_ids = set()
        self.chunk_groups = defaultdict(list)
        self.source_files = set()
        
    def validate_embeddings_batch(
        self,
        embeddings_data: List[Dict[str, Any]],
        check_source_files: bool = True
    ) -> ValidationResult:
        """
        Validate a batch of embedding data for correlation requirements.
        
        Args:
            embeddings_data: List of embedding metadata dictionaries
            check_source_files: Whether to verify source files exist
            
        Returns:
            ValidationResult with detailed validation report
        """
        result = ValidationResult(total_checked=len(embeddings_data))
        
        # Reset state for this batch
        self.seen_ids.clear()
        self.chunk_groups.clear()
        self.source_files.clear()
        
        # Validate each embedding
        for i, data in enumerate(embeddings_data):
            self._validate_single_embedding(data, i, result, check_source_files)
        
        # Validate chunk sequences
        self._validate_chunk_sequences(result)
        
        # Final validation status
        result.required_fields_valid = "required fields" not in str(result.errors).lower()
        result.identifier_unique = "duplicate" not in str(result.errors).lower()
        result.chunk_sequence_valid = "chunk" not in str(result.errors).lower()
        result.source_files_valid = "source file" not in str(result.errors).lower()
        
        logger.info(f"Validation completed: {result.get_summary()}")
        return result
    
    def _validate_single_embedding(
        self,
        data: Dict[str, Any],
        index: int,
        result: ValidationResult,
        check_source_files: bool
    ) -> None:
        """Validate a single embedding's metadata."""
        
        # Check required correlation fields
        required_fields = ['embedding_id', 'entity_type', 'source_type', 'source_file']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            result.add_error(f"Item {index}: Missing required fields: {missing_fields}")
            return
        
        embedding_id = data['embedding_id']
        entity_type = data['entity_type']
        source_file = data['source_file']
        
        # Check ID uniqueness
        if embedding_id in self.seen_ids:
            result.add_error(f"Duplicate embedding_id: {embedding_id}")
        else:
            self.seen_ids.add(embedding_id)
        
        # Validate entity-specific identifiers
        self._validate_entity_identifiers(data, entity_type, index, result)
        
        # Track chunk information for sequence validation
        if 'chunk_index' in data and 'parent_hash' in data:
            parent_id = data['parent_hash']
            self.chunk_groups[parent_id].append({
                'embedding_id': embedding_id,
                'chunk_index': data['chunk_index'],
                'chunk_total': data.get('chunk_total'),
                'text': data.get('text', ''),
                'metadata': data
            })
        
        # Track source files for existence check
        if check_source_files:
            self.source_files.add(source_file)
    
    def _validate_entity_identifiers(
        self,
        data: Dict[str, Any],
        entity_type: str,
        index: int,
        result: ValidationResult
    ) -> None:
        """Validate entity-specific identifiers are present."""
        
        if entity_type == EntityType.PROPERTY.value:
            if not data.get('listing_id'):
                result.add_error(f"Item {index}: Property missing listing_id")
                
        elif entity_type == EntityType.NEIGHBORHOOD.value:
            if not data.get('neighborhood_id'):
                result.add_error(f"Item {index}: Neighborhood missing neighborhood_id")
                
        elif entity_type in [EntityType.WIKIPEDIA_ARTICLE.value, EntityType.WIKIPEDIA_SUMMARY.value]:
            if not data.get('page_id') and not data.get('article_id'):
                result.add_error(f"Item {index}: Wikipedia item missing page_id or article_id")
    
    def _validate_chunk_sequences(self, result: ValidationResult) -> None:
        """Validate chunk sequences are complete and properly ordered."""
        
        for parent_id, chunks in self.chunk_groups.items():
            if len(chunks) < 2:
                continue  # Single chunks don't need sequence validation
                
            # Sort chunks by index
            chunks.sort(key=lambda c: c['chunk_index'])
            
            # Check for expected total consistency
            expected_totals = {c.get('chunk_total') for c in chunks if c.get('chunk_total')}
            if len(expected_totals) > 1:
                result.add_error(f"Inconsistent chunk_total values for parent {parent_id[:8]}: {expected_totals}")
                continue
            
            expected_total = expected_totals.pop() if expected_totals else len(chunks)
            
            # Check sequence completeness
            indices = [c['chunk_index'] for c in chunks]
            expected_indices = list(range(expected_total))
            missing_indices = set(expected_indices) - set(indices)
            
            if missing_indices:
                result.add_error(f"Missing chunk indices for parent {parent_id[:8]}: {sorted(missing_indices)}")
            
            # Check for duplicate indices
            if len(indices) != len(set(indices)):
                duplicate_indices = [idx for idx in indices if indices.count(idx) > 1]
                result.add_error(f"Duplicate chunk indices for parent {parent_id[:8]}: {duplicate_indices}")
    
    def validate_source_files(self, source_files: Set[str]) -> ValidationResult:
        """
        Validate that source files exist and are accessible.
        
        Args:
            source_files: Set of source file paths to validate
            
        Returns:
            ValidationResult for source file validation
        """
        result = ValidationResult(total_checked=len(source_files))
        
        for source_file in source_files:
            if not self._check_file_exists(source_file):
                result.add_error(f"Source file not found: {source_file}")
            elif not self._check_file_readable(source_file):
                result.add_warning(f"Source file not readable: {source_file}")
        
        result.source_files_valid = len(result.errors) == 0
        return result
    
    def _check_file_exists(self, file_path: str) -> bool:
        """Check if a file exists, handling various path formats."""
        try:
            # Handle relative paths from project root
            if not os.path.isabs(file_path):
                # Try relative to current working directory
                if os.path.exists(file_path):
                    return True
                
                # Try relative to common parent paths
                common_roots = [
                    "/Users/ryanknight/projects/temporal/real_estate_ai_search",
                    "real_estate_data",
                    "data/wikipedia"
                ]
                
                for root in common_roots:
                    full_path = os.path.join(root, file_path)
                    if os.path.exists(full_path):
                        return True
                
                return False
            else:
                return os.path.exists(file_path)
                
        except Exception:
            return False
    
    def _check_file_readable(self, file_path: str) -> bool:
        """Check if a file is readable."""
        try:
            return os.access(file_path, os.R_OK)
        except Exception:
            return False


class ChunkReconstructor:
    """
    Utility for reconstructing documents from multiple chunks.
    
    Handles grouping, ordering, and text reconstruction.
    """
    
    def __init__(self):
        """Initialize chunk reconstructor."""
        pass
    
    def group_chunks_by_parent(self, embeddings_data: List[Dict[str, Any]]) -> List[ChunkGroup]:
        """
        Group chunks by their parent document.
        
        Args:
            embeddings_data: List of embedding metadata with chunk information
            
        Returns:
            List of ChunkGroup objects for reconstruction
        """
        chunk_groups = defaultdict(list)
        entity_types = {}
        
        # Group chunks by parent
        for data in embeddings_data:
            parent_id = data.get('parent_hash') or data.get('source_doc_id')
            if not parent_id:
                # Single chunk document
                parent_id = data.get('embedding_id', 'unknown')
            
            chunk_groups[parent_id].append(data)
            entity_types[parent_id] = data.get('entity_type', EntityType.PROPERTY.value)
        
        # Create ChunkGroup objects
        groups = []
        for parent_id, chunks in chunk_groups.items():
            # Sort chunks by index
            chunks.sort(key=lambda c: c.get('chunk_index', 0))
            
            # Determine expected total
            expected_total = None
            chunk_totals = {c.get('chunk_total') for c in chunks if c.get('chunk_total')}
            if chunk_totals:
                expected_total = max(chunk_totals)  # Use the highest reported total
            
            group = ChunkGroup(
                parent_id=parent_id,
                entity_type=EntityType(entity_types[parent_id]),
                chunks=chunks,
                total_expected=expected_total
            )
            groups.append(group)
        
        logger.info(f"Grouped {len(embeddings_data)} chunks into {len(groups)} parent documents")
        return groups
    
    def reconstruct_documents(self, chunk_groups: List[ChunkGroup]) -> List[Dict[str, Any]]:
        """
        Reconstruct original documents from chunk groups.
        
        Args:
            chunk_groups: List of ChunkGroup objects
            
        Returns:
            List of reconstructed document data
        """
        reconstructed = []
        
        for group in chunk_groups:
            if not group.chunks:
                continue
            
            # Get the first chunk's metadata as base
            base_metadata = group.chunks[0].copy()
            
            # Reconstruct text
            reconstructed_text = group.get_reconstructed_text()
            
            # Create reconstructed document
            doc_data = {
                'parent_id': group.parent_id,
                'entity_type': group.entity_type,
                'chunk_count': group.chunk_count,
                'is_complete': group.is_complete,
                'missing_indices': group.missing_indices,
                'reconstructed_text': reconstructed_text,
                'metadata': base_metadata,
                'chunks': group.chunks
            }
            
            reconstructed.append(doc_data)
        
        complete_docs = sum(1 for doc in reconstructed if doc['is_complete'])
        logger.info(f"Reconstructed {len(reconstructed)} documents ({complete_docs} complete)")
        
        return reconstructed


def create_correlation_mappings(embeddings_data: List[Dict[str, Any]]) -> List[CorrelationMapping]:
    """
    Create correlation mappings for downstream services.
    
    Args:
        embeddings_data: List of embedding metadata dictionaries
        
    Returns:
        List of CorrelationMapping objects for efficient lookup
    """
    mappings = []
    
    for data in embeddings_data:
        try:
            mapping = CorrelationMapping(
                embedding_id=data.get('embedding_id', ''),
                entity_type=EntityType(data.get('entity_type', EntityType.PROPERTY.value)),
                source_type=SourceType(data.get('source_type', SourceType.PROPERTY_JSON.value)),
                listing_id=data.get('listing_id'),
                neighborhood_id=data.get('neighborhood_id'),
                page_id=data.get('page_id'),
                article_id=data.get('article_id'),
                source_file=data.get('source_file', ''),
                chunk_info={
                    'chunk_index': data.get('chunk_index'),
                    'chunk_total': data.get('chunk_total'),
                    'parent_hash': data.get('parent_hash')
                } if data.get('chunk_index') is not None else None,
                text_hash=data.get('text_hash')
            )
            mappings.append(mapping)
        except Exception as e:
            logger.warning(f"Failed to create correlation mapping for {data.get('embedding_id', 'unknown')}: {e}")
    
    logger.info(f"Created {len(mappings)} correlation mappings")
    return mappings