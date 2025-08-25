"""
Validation utilities for metadata and configuration.
"""

from typing import Tuple, Optional, Dict, Any, List
from ..models import (
    BaseMetadata,
    PropertyMetadata,
    NeighborhoodMetadata,
    WikipediaMetadata,
    EntityType,
)


def validate_metadata_fields(metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate that metadata contains all required correlation fields.
    
    Args:
        metadata: Metadata dictionary to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Simplified required fields following ChromaDB best practices
    # ChromaDB docs emphasize simple metadata without over-validation
    required_base_fields = [
        'embedding_id',
        'source_file',
        'embedding_model',
        'text_hash'
    ]
    
    missing_fields = []
    for field in required_base_fields:
        if field not in metadata or metadata[field] is None:
            missing_fields.append(field)
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    # Validate entity-specific fields
    entity_type = metadata.get('entity_type')
    
    if entity_type == EntityType.PROPERTY.value:
        if 'listing_id' not in metadata or metadata['listing_id'] is None:
            return False, "Property metadata must include listing_id"
    
    elif entity_type == EntityType.NEIGHBORHOOD.value:
        if 'neighborhood_id' not in metadata or metadata['neighborhood_id'] is None:
            return False, "Neighborhood metadata must include neighborhood_id"
        if 'neighborhood_name' not in metadata or metadata['neighborhood_name'] is None:
            return False, "Neighborhood metadata must include neighborhood_name"
    
    elif entity_type in [EntityType.WIKIPEDIA_ARTICLE.value, EntityType.WIKIPEDIA_SUMMARY.value]:
        if 'page_id' not in metadata or metadata['page_id'] is None:
            return False, "Wikipedia metadata must include page_id"
    
    return True, None


def validate_correlation_identifiers(
    metadata: BaseMetadata,
    entity_type: EntityType
) -> Tuple[bool, Optional[str]]:
    """
    Validate correlation identifiers for a specific entity type.
    
    Args:
        metadata: Metadata object to validate
        entity_type: Expected entity type
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if metadata.entity_type != entity_type.value:
        return False, f"Entity type mismatch: expected {entity_type.value}, got {metadata.entity_type}"
    
    if isinstance(metadata, PropertyMetadata):
        if not metadata.listing_id:
            return False, "Property must have listing_id for correlation"
    
    elif isinstance(metadata, NeighborhoodMetadata):
        if not metadata.neighborhood_id or not metadata.neighborhood_name:
            return False, "Neighborhood must have both neighborhood_id and neighborhood_name"
    
    elif isinstance(metadata, WikipediaMetadata):
        if metadata.page_id is None or metadata.page_id < 0:
            return False, "Wikipedia article must have valid page_id"
    
    return True, None


def validate_chunk_sequence(chunks: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """
    Validate that chunks form a complete sequence.
    
    Args:
        chunks: List of chunk metadata dictionaries
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not chunks:
        return True, None
    
    # Group by parent_id
    parent_chunks = {}
    for chunk in chunks:
        if 'parent_id' in chunk:
            parent_id = chunk['parent_id']
            if parent_id not in parent_chunks:
                parent_chunks[parent_id] = []
            parent_chunks[parent_id].append(chunk)
    
    # Validate each parent's chunks
    for parent_id, chunk_list in parent_chunks.items():
        # Sort by chunk_index
        chunk_list.sort(key=lambda x: x.get('chunk_index', 0))
        
        # Check for sequential indices
        expected_total = chunk_list[0].get('chunk_total', 1)
        indices = [c.get('chunk_index', -1) for c in chunk_list]
        
        if len(chunk_list) != expected_total:
            return False, f"Parent {parent_id} has {len(chunk_list)} chunks but expects {expected_total}"
        
        for i, idx in enumerate(indices):
            if idx != i:
                return False, f"Parent {parent_id} has non-sequential chunk indices"
    
    return True, None


def validate_collection_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate ChromaDB collection name format.
    
    Args:
        name: Collection name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    import re
    
    # Pattern: {entity_type}_{model}_{version}
    pattern = r'^[a-z]+_[a-z0-9_]+_v\d+$'
    
    if not re.match(pattern, name):
        return False, f"Collection name '{name}' doesn't match pattern: entity_model_v#"
    
    return True, None