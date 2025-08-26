"""
Pydantic models for type-safe writer operations.

This module provides strongly-typed models for writer operations,
ensuring type safety and validation throughout the writing process.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pyspark.sql import DataFrame


class EntityType(str, Enum):
    """Supported entity types for writing."""
    
    PROPERTY = "property"
    NEIGHBORHOOD = "neighborhood"
    WIKIPEDIA = "wikipedia"
    FEATURE = "feature"
    PROPERTY_TYPE = "property_type"
    PRICE_RANGE = "price_range"
    COUNTY = "county"
    CITY = "city"
    STATE = "state"
    TOPIC_CLUSTER = "topic_cluster"


class WriteMetadata(BaseModel):
    """Metadata for write operations with full validation."""
    
    pipeline_name: str = Field(
        description="Name of the pipeline executing the write"
    )
    pipeline_version: str = Field(
        description="Version of the pipeline"
    )
    entity_type: EntityType = Field(
        description="Type of entity being written"
    )
    record_count: int = Field(
        ge=0,
        description="Number of records being written"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of the write operation"
    )
    environment: Optional[str] = Field(
        default="development",
        description="Environment (development, staging, production)"
    )
    
    # Optional fields for tracking
    source_system: Optional[str] = Field(
        default=None,
        description="Source system for the data"
    )
    processing_time_seconds: Optional[float] = Field(
        default=None,
        ge=0,
        description="Time taken to process the data"
    )
    quality_metrics: Optional[Dict[str, float]] = Field(
        default=None,
        description="Quality metrics for the data"
    )
    
    # Entity-specific metadata
    entity_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Entity-specific metadata"
    )
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_serializers={
            datetime: lambda v: v.isoformat()
        }
    )


class WriteRequest(BaseModel):
    """Type-safe write request for a single entity."""
    
    entity_type: EntityType = Field(
        description="Type of entity to write"
    )
    dataframe: Any = Field(  # Can't directly type DataFrame in Pydantic
        description="Spark DataFrame to write"
    )
    metadata: WriteMetadata = Field(
        description="Metadata for the write operation"
    )
    
    @field_validator('dataframe')
    @classmethod
    def validate_dataframe(cls, v):
        """Validate that the dataframe is not None."""
        if v is None:
            raise ValueError("DataFrame cannot be None")
        # Could add more validation here if needed
        return v
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True  # Allow DataFrame type
    )


class EntityWriteRequests(BaseModel):
    """Container for multiple entity write requests."""
    
    property_request: Optional[WriteRequest] = Field(
        default=None,
        description="Property write request"
    )
    neighborhood_request: Optional[WriteRequest] = Field(
        default=None,
        description="Neighborhood write request"
    )
    wikipedia_request: Optional[WriteRequest] = Field(
        default=None,
        description="Wikipedia write request"
    )
    
    def get_requests(self) -> List[WriteRequest]:
        """Get all non-null write requests."""
        requests = []
        if self.property_request:
            requests.append(self.property_request)
        if self.neighborhood_request:
            requests.append(self.neighborhood_request)
        if self.wikipedia_request:
            requests.append(self.wikipedia_request)
        return requests
    
    def has_data(self) -> bool:
        """Check if any requests have data."""
        return any([
            self.property_request,
            self.neighborhood_request,
            self.wikipedia_request
        ])


class WriteResult(BaseModel):
    """Result of a write operation."""
    
    entity_type: EntityType = Field(
        description="Type of entity written"
    )
    writer_name: str = Field(
        description="Name of the writer used"
    )
    success: bool = Field(
        description="Whether the write was successful"
    )
    records_written: int = Field(
        ge=0,
        description="Number of records written"
    )
    duration_seconds: float = Field(
        ge=0,
        description="Time taken for the write"
    )
    output_path: Optional[str] = Field(
        default=None,
        description="Path where data was written"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if write failed"
    )
    
    model_config = ConfigDict(
        use_enum_values=True
    )


class WriteSessionResult(BaseModel):
    """Result of a complete write session across all entities and writers."""
    
    session_id: str = Field(
        description="Unique identifier for this write session"
    )
    start_time: datetime = Field(
        description="When the write session started"
    )
    end_time: datetime = Field(
        description="When the write session completed"
    )
    total_duration_seconds: float = Field(
        ge=0,
        description="Total time for all writes"
    )
    
    # Results by entity and writer
    results: List[WriteResult] = Field(
        default_factory=list,
        description="Individual write results"
    )
    
    # Summary statistics
    total_records_written: int = Field(
        ge=0,
        default=0,
        description="Total records written across all entities"
    )
    successful_writes: int = Field(
        ge=0,
        default=0,
        description="Number of successful write operations"
    )
    failed_writes: int = Field(
        ge=0,
        default=0,
        description="Number of failed write operations"
    )
    
    def add_result(self, result: WriteResult) -> None:
        """Add a write result to the session."""
        self.results.append(result)
        if result.success:
            self.successful_writes += 1
            self.total_records_written += result.records_written
        else:
            self.failed_writes += 1
    
    def get_results_by_entity(self, entity_type: EntityType) -> List[WriteResult]:
        """Get all results for a specific entity type."""
        return [r for r in self.results if r.entity_type == entity_type]
    
    def get_results_by_writer(self, writer_name: str) -> List[WriteResult]:
        """Get all results for a specific writer."""
        return [r for r in self.results if r.writer_name == writer_name]
    
    def all_successful(self) -> bool:
        """Check if all writes were successful."""
        return self.failed_writes == 0
    
    model_config = ConfigDict(
        json_serializers={
            datetime: lambda v: v.isoformat()
        }
    )


class RelationshipConfig(BaseModel):
    """Configuration for a Neo4j relationship type."""
    
    source_labels: str = Field(
        description="Neo4j labels for source nodes (e.g., ':Property')"
    )
    source_keys: str = Field(
        description="Mapping of DataFrame column to node property (e.g., 'from_id:listing_id')"
    )
    target_labels: str = Field(
        description="Neo4j labels for target nodes (e.g., ':Neighborhood')"
    )
    target_keys: str = Field(
        description="Mapping of DataFrame column to node property (e.g., 'to_id:neighborhood_id')"
    )
    
    model_config = ConfigDict(
        frozen=True  # Make immutable for use as dict values
    )


class RelationshipType(str, Enum):
    """Supported relationship types in Neo4j."""
    
    LOCATED_IN = "LOCATED_IN"
    PART_OF = "PART_OF"
    DESCRIBES = "DESCRIBES"
    SIMILAR_TO = "SIMILAR_TO"
    NEAR = "NEAR"
    HAS_FEATURE = "HAS_FEATURE"
    OF_TYPE = "OF_TYPE"
    IN_PRICE_RANGE = "IN_PRICE_RANGE"
    IN_COUNTY = "IN_COUNTY"
    IN_TOPIC_CLUSTER = "IN_TOPIC_CLUSTER"


class Neo4jEntityConfig(BaseModel):
    """Configuration for writing an entity type to Neo4j."""
    
    label: str = Field(
        description="Neo4j node label (e.g., 'Property', 'Neighborhood')"
    )
    key_field: str = Field(
        description="Unique identifier field in the DataFrame"
    )
    
    model_config = ConfigDict(
        frozen=True  # Make immutable for use as dict values
    )


class WriterConfiguration(BaseModel):
    """Configuration for a specific writer."""
    
    writer_name: str = Field(
        description="Name of the writer"
    )
    enabled: bool = Field(
        default=True,
        description="Whether this writer is enabled"
    )
    supported_entities: List[EntityType] = Field(
        description="Entity types this writer supports"
    )
    configuration: Dict[str, Any] = Field(
        default_factory=dict,
        description="Writer-specific configuration"
    )
    
    def supports_entity(self, entity_type: EntityType) -> bool:
        """Check if this writer supports the given entity type."""
        return entity_type in self.supported_entities
    
    model_config = ConfigDict(
        use_enum_values=True
    )


class OrchestratorConfiguration(BaseModel):
    """Configuration for the writer orchestrator."""
    
    writers: List[WriterConfiguration] = Field(
        description="Configurations for all writers"
    )
    fail_fast: bool = Field(
        default=True,
        description="Stop on first failure"
    )
    validate_schemas: bool = Field(
        default=True,
        description="Validate DataFrames against schemas"
    )
    clear_before_write: bool = Field(
        default=False,
        description="Clear existing data before writing"
    )
    parallel_writes: bool = Field(
        default=False,
        description="Write to multiple destinations in parallel"
    )
    
    def get_enabled_writers(self) -> List[WriterConfiguration]:
        """Get all enabled writer configurations."""
        return [w for w in self.writers if w.enabled]
    
    def get_writers_for_entity(self, entity_type: EntityType) -> List[WriterConfiguration]:
        """Get all writers that support the given entity type."""
        return [
            w for w in self.writers 
            if w.enabled and w.supports_entity(entity_type)
        ]