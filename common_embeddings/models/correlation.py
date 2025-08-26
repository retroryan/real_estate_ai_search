"""
Pydantic models for correlation and chunk reconstruction operations.

Clean, type-safe models for advanced ChromaDB operations and correlation.
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from .enums import EntityType, SourceType
from .metadata import BaseMetadata


class ChunkGroup(BaseModel):
    """
    A group of chunks belonging to the same parent document.
    
    Used for document reconstruction from multiple chunks.
    """
    
    parent_id: str = Field(description="Parent document identifier")
    entity_type: EntityType = Field(description="Type of entity")
    chunks: List[Dict[str, Any]] = Field(description="List of chunk data sorted by index")
    total_expected: Optional[int] = Field(None, description="Expected number of chunks")
    
    # Derived properties
    @property
    def chunk_count(self) -> int:
        """Number of chunks in this group."""
        return len(self.chunks)
    
    @property
    def is_complete(self) -> bool:
        """Check if all expected chunks are present."""
        if self.total_expected is None:
            return True  # Can't determine completeness
        return self.chunk_count == self.total_expected
    
    @property
    def missing_indices(self) -> List[int]:
        """Get list of missing chunk indices."""
        if not self.chunks:
            return []
        
        present_indices = {chunk.get('chunk_index', 0) for chunk in self.chunks}
        if self.total_expected:
            expected_indices = set(range(self.total_expected))
            return sorted(expected_indices - present_indices)
        return []
    
    def get_reconstructed_text(self) -> str:
        """Reconstruct original text by joining chunks in order."""
        # Sort chunks by index
        sorted_chunks = sorted(self.chunks, key=lambda c: c.get('chunk_index', 0))
        return ' '.join(chunk.get('text', '') for chunk in sorted_chunks)


class ValidationResult(BaseModel):
    """
    Result of metadata validation operations.
    
    Comprehensive validation report with specific error details.
    """
    
    is_valid: bool = Field(description="Overall validation status")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    
    # Validation categories
    required_fields_valid: bool = Field(True, description="All required fields present")
    identifier_unique: bool = Field(True, description="Identifiers are unique")
    chunk_sequence_valid: bool = Field(True, description="Chunk sequences are complete")
    source_files_valid: bool = Field(True, description="Source files exist and accessible")
    
    # Statistics
    total_checked: int = Field(0, description="Total items validated")
    error_count: int = Field(0, description="Number of errors found")
    warning_count: int = Field(0, description="Number of warnings found")
    
    @field_validator('error_count', mode='before')
    @classmethod
    def set_error_count(cls, v, info):
        """Automatically set error count from errors list."""
        if hasattr(info, 'data'):
            return len(info.data.get('errors', []))
        return v or 0
    
    @field_validator('warning_count', mode='before')
    @classmethod
    def set_warning_count(cls, v, info):
        """Automatically set warning count from warnings list."""
        if hasattr(info, 'data'):
            return len(info.data.get('warnings', []))
        return v or 0
    
    def add_error(self, error: str) -> None:
        """Add a validation error."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a validation warning."""
        self.warnings.append(warning)
    
    def get_summary(self) -> str:
        """Get validation summary as string."""
        status = "✅ VALID" if self.is_valid else "❌ INVALID"
        return f"{status} - {self.total_checked} items checked, {self.error_count} errors, {self.warning_count} warnings"


class CollectionHealth(BaseModel):
    """
    Health status and statistics for a ChromaDB collection.
    
    Comprehensive collection analysis for maintenance and monitoring.
    """
    
    collection_name: str = Field(description="Name of the collection")
    entity_type: Optional[EntityType] = Field(None, description="Primary entity type in collection")
    
    # Basic statistics  
    total_embeddings: int = Field(ge=0, description="Total number of embeddings")
    unique_entities: int = Field(ge=0, description="Number of unique entities")
    chunk_groups: int = Field(ge=0, description="Number of chunk groups (parent documents)")
    
    # Health indicators
    has_orphaned_chunks: bool = Field(False, description="Has chunks without parent references")
    has_duplicate_ids: bool = Field(False, description="Has duplicate embedding IDs")
    has_incomplete_groups: bool = Field(False, description="Has incomplete chunk groups")
    has_missing_metadata: bool = Field(False, description="Has embeddings with missing required metadata")
    
    # Metadata distribution
    source_types: Dict[str, int] = Field(default_factory=dict, description="Count by source type")
    entity_types: Dict[str, int] = Field(default_factory=dict, description="Count by entity type")
    chunk_size_stats: Dict[str, float] = Field(default_factory=dict, description="Chunk size statistics")
    
    # Timestamps
    analyzed_at: datetime = Field(default_factory=datetime.now, description="Analysis timestamp")
    
    @property
    def health_score(self) -> float:
        """Calculate overall health score (0.0-1.0)."""
        issues = sum([
            self.has_orphaned_chunks,
            self.has_duplicate_ids,
            self.has_incomplete_groups,
            self.has_missing_metadata
        ])
        return max(0.0, 1.0 - (issues * 0.25))
    
    @property
    def status(self) -> str:
        """Get health status string."""
        score = self.health_score
        if score >= 0.9:
            return "✅ HEALTHY"
        elif score >= 0.7:
            return "⚠️ WARNING"
        else:
            return "❌ CRITICAL"
    
    def get_issues(self) -> List[str]:
        """Get list of identified issues."""
        issues = []
        if self.has_orphaned_chunks:
            issues.append("Orphaned chunks detected")
        if self.has_duplicate_ids:
            issues.append("Duplicate IDs found")
        if self.has_incomplete_groups:
            issues.append("Incomplete chunk groups")
        if self.has_missing_metadata:
            issues.append("Missing required metadata")
        return issues


class CorrelationMapping(BaseModel):
    """
    Mapping between embeddings and source data for correlation.
    
    Efficient lookup structure for downstream services.
    """
    
    embedding_id: str = Field(description="Unique embedding identifier")
    entity_type: EntityType = Field(description="Type of entity")
    source_type: SourceType = Field(description="Type of source data")
    
    # Entity identifiers for correlation
    listing_id: Optional[str] = Field(None, description="Property listing identifier")
    neighborhood_id: Optional[str] = Field(None, description="Neighborhood identifier")
    page_id: Optional[int] = Field(None, description="Wikipedia page identifier")
    article_id: Optional[int] = Field(None, description="Wikipedia article identifier")
    
    # Source location
    source_file: str = Field(description="Path to source data file")
    chunk_info: Optional[Dict[str, Any]] = Field(None, description="Chunk-specific information")
    
    # Processing metadata
    text_hash: Optional[str] = Field(None, description="Hash of source text")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    
    def get_primary_identifier(self) -> Optional[str]:
        """Get the primary identifier for this entity."""
        if self.listing_id:
            return self.listing_id
        elif self.neighborhood_id:
            return self.neighborhood_id
        elif self.page_id:
            return str(self.page_id)
        elif self.article_id:
            return str(self.article_id)
        return None


class StorageOperation(BaseModel):
    """
    A storage operation with rollback capability.
    
    Supports atomic batch operations on ChromaDB.
    """
    
    operation_id: str = Field(description="Unique operation identifier")
    operation_type: str = Field(description="Type of operation (insert, update, delete)")
    collection_name: str = Field(description="Target collection name")
    
    # Operation data
    embeddings: Optional[List[List[float]]] = Field(None, description="Embeddings to store")
    texts: Optional[List[str]] = Field(None, description="Text content")
    metadatas: Optional[List[Dict[str, Any]]] = Field(None, description="Metadata objects")
    ids: Optional[List[str]] = Field(None, description="Embedding IDs")
    
    # Operation status
    executed: bool = Field(False, description="Whether operation was executed")
    rollback_data: Optional[Dict[str, Any]] = Field(None, description="Data needed for rollback")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now, description="Operation creation time")
    executed_at: Optional[datetime] = Field(None, description="Execution timestamp")
    
    def mark_executed(self, rollback_data: Optional[Dict[str, Any]] = None) -> None:
        """Mark operation as executed."""
        self.executed = True
        self.executed_at = datetime.now()
        self.rollback_data = rollback_data