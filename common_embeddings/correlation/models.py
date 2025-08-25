"""
Pydantic models for the correlation engine.

Defines data structures for correlation results, enriched entities, 
and source data management.
"""

from typing import Dict, Any, List, Optional, Set, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator

from ..models import EntityType, SourceType, BaseMetadata


class SourceDataCache(BaseModel):
    """
    Cache for source data to avoid repeated file reads.
    
    Efficient lookup structure for correlation operations.
    """
    
    entity_type: EntityType = Field(description="Type of entities in cache")
    source_type: SourceType = Field(description="Type of source data")
    
    # Cache data by identifier
    data_by_id: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Source data keyed by identifier")
    file_paths: Set[str] = Field(default_factory=set, description="Source files loaded into cache")
    
    # Cache statistics
    total_entities: int = Field(default=0, description="Total entities in cache")
    cache_hits: int = Field(default=0, description="Number of cache hits")
    cache_misses: int = Field(default=0, description="Number of cache misses")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Cache creation time")
    last_accessed: datetime = Field(default_factory=datetime.now, description="Last access time")
    
    def get_entity(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get entity from cache by identifier."""
        self.last_accessed = datetime.now()
        
        if identifier in self.data_by_id:
            self.cache_hits += 1
            return self.data_by_id[identifier]
        else:
            self.cache_misses += 1
            return None
    
    def add_entity(self, identifier: str, data: Dict[str, Any]) -> None:
        """Add entity to cache."""
        self.data_by_id[identifier] = data
        self.total_entities = len(self.data_by_id)
        self.last_accessed = datetime.now()
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_requests = self.cache_hits + self.cache_misses
        return self.cache_hits / total_requests if total_requests > 0 else 0.0


class CorrelationResult(BaseModel):
    """
    Result of correlating an embedding with its source data.
    
    Contains the embedding metadata, source data, and correlation status.
    """
    
    embedding_id: str = Field(description="Embedding identifier")
    entity_type: EntityType = Field(description="Type of entity")
    
    # Correlation status
    is_correlated: bool = Field(description="Whether correlation was successful")
    correlation_method: str = Field(description="Method used for correlation")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence in correlation")
    
    # Data references
    embedding_metadata: Dict[str, Any] = Field(description="Embedding metadata from ChromaDB")
    source_data: Optional[Dict[str, Any]] = Field(None, description="Correlated source data")
    
    # Correlation details
    identifier_used: Optional[str] = Field(None, description="Identifier used for correlation")
    source_file: Optional[str] = Field(None, description="Source file containing the data")
    
    # Error information
    error_message: Optional[str] = Field(None, description="Error message if correlation failed")
    warnings: List[str] = Field(default_factory=list, description="Correlation warnings")
    
    # Processing metadata
    correlation_timestamp: datetime = Field(default_factory=datetime.now, description="When correlation was performed")
    processing_time_ms: Optional[float] = Field(None, description="Time taken for correlation in milliseconds")
    
    @validator('confidence_score')
    def validate_confidence(cls, v):
        """Validate confidence score is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the correlation result."""
        self.warnings.append(warning)


class EnrichedEntity(BaseModel):
    """
    Entity enriched with embedding data and source information.
    
    Combines source data with embedding information for comprehensive representation.
    """
    
    # Entity identification
    entity_id: str = Field(description="Primary entity identifier")
    entity_type: EntityType = Field(description="Type of entity")
    source_type: SourceType = Field(description="Type of source data")
    
    # Core data
    source_data: Dict[str, Any] = Field(description="Original source data")
    embedding_ids: List[str] = Field(description="Associated embedding identifiers")
    
    # Enrichment metadata
    total_embeddings: int = Field(ge=0, description="Number of associated embeddings")
    chunk_count: int = Field(ge=0, description="Number of chunks if multi-chunk document")
    is_complete: bool = Field(True, description="Whether all chunks are present")
    
    # Text reconstruction
    reconstructed_text: Optional[str] = Field(None, description="Reconstructed text from chunks")
    text_length: Optional[int] = Field(None, description="Length of reconstructed text")
    
    # Processing metadata
    enriched_at: datetime = Field(default_factory=datetime.now, description="Enrichment timestamp")
    source_files: Set[str] = Field(default_factory=set, description="Source files used")
    
    # Validation status
    validation_passed: bool = Field(True, description="Whether validation passed")
    validation_warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    
    @validator('total_embeddings')
    def validate_embedding_count(cls, v, values):
        """Validate embedding count matches embedding_ids length."""
        embedding_ids = values.get('embedding_ids', [])
        if v != len(embedding_ids):
            raise ValueError("total_embeddings must match length of embedding_ids")
        return v
    
    def add_validation_warning(self, warning: str) -> None:
        """Add a validation warning to the entity."""
        self.validation_warnings.append(warning)
        self.validation_passed = False
    
    @property
    def primary_identifier(self) -> str:
        """Get the primary identifier for this entity."""
        return self.entity_id
    
    def get_embedding_summary(self) -> Dict[str, Any]:
        """Get summary of embedding information."""
        return {
            'total_embeddings': self.total_embeddings,
            'chunk_count': self.chunk_count,
            'is_complete': self.is_complete,
            'text_length': self.text_length,
            'validation_passed': self.validation_passed
        }


class CorrelationReport(BaseModel):
    """
    Comprehensive report of correlation operations.
    
    Provides statistics and analysis of correlation performance.
    """
    
    # Report metadata
    report_id: str = Field(description="Unique report identifier")
    collection_names: List[str] = Field(description="Collections processed")
    entity_types: List[EntityType] = Field(description="Entity types processed")
    
    # Processing statistics
    total_embeddings: int = Field(ge=0, description="Total embeddings processed")
    successful_correlations: int = Field(ge=0, description="Successful correlations")
    failed_correlations: int = Field(ge=0, description="Failed correlations")
    
    # Performance metrics
    processing_time_seconds: float = Field(ge=0.0, description="Total processing time")
    average_time_per_embedding_ms: float = Field(ge=0.0, description="Average time per embedding")
    
    # Error analysis
    error_counts: Dict[str, int] = Field(default_factory=dict, description="Count of errors by type")
    warning_counts: Dict[str, int] = Field(default_factory=dict, description="Count of warnings by type")
    
    # Entity analysis
    entities_by_type: Dict[str, int] = Field(default_factory=dict, description="Entity count by type")
    incomplete_entities: int = Field(ge=0, description="Entities with missing chunks")
    orphaned_embeddings: int = Field(ge=0, description="Embeddings without source data")
    
    # Cache performance
    cache_statistics: Dict[str, Dict[str, float]] = Field(default_factory=dict, description="Cache performance by entity type")
    
    # Timestamps
    started_at: datetime = Field(default_factory=datetime.now, description="Processing start time")
    completed_at: Optional[datetime] = Field(None, description="Processing completion time")
    
    @property
    def success_rate(self) -> float:
        """Calculate correlation success rate."""
        if self.total_embeddings == 0:
            return 0.0
        return self.successful_correlations / self.total_embeddings
    
    @property
    def failure_rate(self) -> float:
        """Calculate correlation failure rate."""
        return 1.0 - self.success_rate
    
    def add_error(self, error_type: str) -> None:
        """Add an error to the report."""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self.failed_correlations += 1
    
    def add_warning(self, warning_type: str) -> None:
        """Add a warning to the report."""
        self.warning_counts[warning_type] = self.warning_counts.get(warning_type, 0) + 1
    
    def add_success(self) -> None:
        """Record a successful correlation."""
        self.successful_correlations += 1
    
    def complete_report(self) -> None:
        """Mark the report as completed."""
        self.completed_at = datetime.now()
        if self.started_at and self.completed_at:
            self.processing_time_seconds = (self.completed_at - self.started_at).total_seconds()
            
        if self.total_embeddings > 0 and self.processing_time_seconds > 0:
            self.average_time_per_embedding_ms = (self.processing_time_seconds * 1000) / self.total_embeddings
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the report."""
        status = "✅ SUCCESS" if self.success_rate >= 0.95 else "⚠️ WARNINGS" if self.success_rate >= 0.8 else "❌ ISSUES"
        
        return (f"{status} - Processed {self.total_embeddings} embeddings, "
                f"{self.successful_correlations} successful ({self.success_rate:.1%}), "
                f"{self.failed_correlations} failed, "
                f"completed in {self.processing_time_seconds:.1f}s")


class BulkCorrelationRequest(BaseModel):
    """
    Request for bulk correlation operations.
    
    Configuration for processing multiple collections and entity types.
    """
    
    collection_names: List[str] = Field(description="Collections to process")
    entity_types: Optional[List[EntityType]] = Field(None, description="Entity types to filter by")
    
    # Processing configuration
    batch_size: int = Field(default=100, ge=1, description="Batch size for processing")
    parallel_workers: int = Field(default=4, ge=1, description="Number of parallel workers")
    
    # Options
    include_orphaned: bool = Field(False, description="Include orphaned embeddings in results")
    validate_completeness: bool = Field(True, description="Validate chunk completeness")
    use_cache: bool = Field(True, description="Use source data caching")
    
    # Output configuration
    include_embeddings: bool = Field(False, description="Include embedding vectors in results")
    output_format: str = Field(default="enriched", description="Output format: enriched, raw, summary")
    
    @validator('output_format')
    def validate_output_format(cls, v):
        """Validate output format is supported."""
        valid_formats = ['enriched', 'raw', 'summary']
        if v not in valid_formats:
            raise ValueError(f"Output format must be one of: {valid_formats}")
        return v