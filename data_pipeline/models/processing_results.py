"""
Processing result models for entity-specific pipeline operations.

This module provides Pydantic models for tracking and reporting the results
of processing operations for each entity type.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ValidationStats(BaseModel):
    """Statistics for validation operations."""
    
    total_records: int = Field(ge=0, description="Total number of records processed")
    valid_records: int = Field(ge=0, description="Number of valid records")
    invalid_records: int = Field(ge=0, description="Number of invalid records")
    validation_errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors encountered"
    )
    quality_score: float = Field(ge=0, le=1, description="Overall validation quality score")


class EnrichmentStats(BaseModel):
    """Statistics for enrichment operations."""
    
    records_enriched: int = Field(ge=0, description="Number of records enriched")
    fields_added: List[str] = Field(
        default_factory=list,
        description="List of fields added during enrichment"
    )
    avg_quality_score: float = Field(ge=0, le=1, description="Average quality score")
    enrichment_time_ms: float = Field(ge=0, description="Time spent on enrichment in milliseconds")


class TextProcessingStats(BaseModel):
    """Statistics for text processing operations."""
    
    records_processed: int = Field(ge=0, description="Number of records with text processed")
    avg_text_length: float = Field(ge=0, description="Average text length after processing")
    min_text_length: int = Field(ge=0, description="Minimum text length")
    max_text_length: int = Field(ge=0, description="Maximum text length")
    processing_time_ms: float = Field(ge=0, description="Time spent on text processing")


class EmbeddingStats(BaseModel):
    """Statistics for embedding generation."""
    
    records_embedded: int = Field(ge=0, description="Number of records with embeddings generated")
    embedding_dimension: int = Field(gt=0, description="Dimension of embeddings")
    model_used: str = Field(description="Embedding model identifier")
    avg_generation_time_ms: float = Field(ge=0, description="Average time per embedding")
    failed_embeddings: int = Field(ge=0, description="Number of failed embedding generations")


class WriterStats(BaseModel):
    """Statistics for writing operations."""
    
    records_written: int = Field(ge=0, description="Number of records written")
    write_time_ms: float = Field(ge=0, description="Time spent writing")
    destination: str = Field(description="Destination identifier (e.g., collection name, index)")
    writer_type: str = Field(description="Type of writer used")
    errors_count: int = Field(ge=0, description="Number of write errors")


class PropertyProcessingResult(BaseModel):
    """Result model for property processing operations."""
    
    entity_type: str = Field(default="property", description="Entity type")
    start_time: datetime = Field(description="Processing start time")
    end_time: Optional[datetime] = Field(None, description="Processing end time")
    total_processing_time_ms: Optional[float] = Field(None, ge=0, description="Total processing time")
    
    # Processing stages
    validation_stats: Optional[ValidationStats] = None
    enrichment_stats: Optional[EnrichmentStats] = None
    text_processing_stats: Optional[TextProcessingStats] = None
    embedding_stats: Optional[EmbeddingStats] = None
    writing_stats: List[WriterStats] = Field(default_factory=list)
    
    # Property-specific metrics
    properties_with_price: int = Field(ge=0, description="Properties with price information")
    avg_price_per_sqft: Optional[float] = Field(None, ge=0, description="Average price per square foot")
    price_categories: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by price category"
    )
    
    def calculate_total_time(self) -> None:
        """Calculate total processing time if end_time is set."""
        if self.end_time:
            self.total_processing_time_ms = (
                self.end_time - self.start_time
            ).total_seconds() * 1000


class NeighborhoodProcessingResult(BaseModel):
    """Result model for neighborhood processing operations."""
    
    entity_type: str = Field(default="neighborhood", description="Entity type")
    start_time: datetime = Field(description="Processing start time")
    end_time: Optional[datetime] = Field(None, description="Processing end time")
    total_processing_time_ms: Optional[float] = Field(None, ge=0, description="Total processing time")
    
    # Processing stages
    validation_stats: Optional[ValidationStats] = None
    enrichment_stats: Optional[EnrichmentStats] = None
    text_processing_stats: Optional[TextProcessingStats] = None
    embedding_stats: Optional[EmbeddingStats] = None
    writing_stats: List[WriterStats] = Field(default_factory=list)
    
    # Neighborhood-specific metrics
    neighborhoods_with_demographics: int = Field(
        ge=0, description="Neighborhoods with demographic data"
    )
    neighborhoods_with_boundaries: int = Field(
        ge=0, description="Neighborhoods with boundary data"
    )
    avg_demographic_completeness: float = Field(
        ge=0, le=1, description="Average demographic data completeness"
    )
    income_brackets: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by income bracket"
    )
    
    def calculate_total_time(self) -> None:
        """Calculate total processing time if end_time is set."""
        if self.end_time:
            self.total_processing_time_ms = (
                self.end_time - self.start_time
            ).total_seconds() * 1000


class WikipediaProcessingResult(BaseModel):
    """Result model for Wikipedia article processing operations."""
    
    entity_type: str = Field(default="wikipedia", description="Entity type")
    start_time: datetime = Field(description="Processing start time")
    end_time: Optional[datetime] = Field(None, description="Processing end time")
    total_processing_time_ms: Optional[float] = Field(None, ge=0, description="Total processing time")
    
    # Processing stages
    validation_stats: Optional[ValidationStats] = None
    enrichment_stats: Optional[EnrichmentStats] = None
    text_processing_stats: Optional[TextProcessingStats] = None
    embedding_stats: Optional[EmbeddingStats] = None
    writing_stats: List[WriterStats] = Field(default_factory=list)
    
    # Wikipedia-specific metrics
    articles_with_location: int = Field(
        ge=0, description="Articles with location data"
    )
    avg_confidence_score: float = Field(
        ge=0, le=1, description="Average confidence score"
    )
    articles_above_threshold: int = Field(
        ge=0, description="Articles above confidence threshold"
    )
    relevance_categories: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by relevance category"
    )
    location_specificity: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by location specificity level"
    )
    
    def calculate_total_time(self) -> None:
        """Calculate total processing time if end_time is set."""
        if self.end_time:
            self.total_processing_time_ms = (
                self.end_time - self.start_time
            ).total_seconds() * 1000


class PipelineExecutionResult(BaseModel):
    """Result model for complete pipeline execution."""
    
    pipeline_name: str = Field(description="Name of the pipeline")
    pipeline_version: str = Field(description="Version of the pipeline")
    execution_id: str = Field(description="Unique identifier for this execution")
    start_time: datetime = Field(description="Pipeline start time")
    end_time: Optional[datetime] = Field(None, description="Pipeline end time")
    total_execution_time_ms: Optional[float] = Field(None, ge=0, description="Total execution time")
    
    # Entity processing results
    property_result: Optional[PropertyProcessingResult] = None
    neighborhood_result: Optional[NeighborhoodProcessingResult] = None
    wikipedia_result: Optional[WikipediaProcessingResult] = None
    
    # Overall statistics
    total_records_processed: int = Field(ge=0, description="Total records across all entities")
    successful_entities: List[str] = Field(
        default_factory=list,
        description="List of successfully processed entity types"
    )
    failed_entities: List[str] = Field(
        default_factory=list,
        description="List of failed entity types"
    )
    
    # Environment info
    environment: str = Field(description="Execution environment")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional execution metadata"
    )
    
    def calculate_total_time(self) -> None:
        """Calculate total execution time if end_time is set."""
        if self.end_time:
            self.total_execution_time_ms = (
                self.end_time - self.start_time
            ).total_seconds() * 1000
    
    def add_entity_result(
        self,
        entity_type: str,
        result: Union[PropertyProcessingResult, NeighborhoodProcessingResult, WikipediaProcessingResult]
    ) -> None:
        """
        Add an entity processing result.
        
        Args:
            entity_type: Type of entity processed
            result: Processing result for the entity
        """
        if entity_type.lower() == "property":
            self.property_result = result
        elif entity_type.lower() == "neighborhood":
            self.neighborhood_result = result
        elif entity_type.lower() in ["wikipedia", "wikipedia_article"]:
            self.wikipedia_result = result
        
        # Update successful/failed tracking
        if result.validation_stats and result.validation_stats.valid_records > 0:
            if entity_type not in self.successful_entities:
                self.successful_entities.append(entity_type)
        else:
            if entity_type not in self.failed_entities:
                self.failed_entities.append(entity_type)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the pipeline execution.
        
        Returns:
            Dictionary with execution summary
        """
        return {
            "pipeline": f"{self.pipeline_name} v{self.pipeline_version}",
            "execution_id": self.execution_id,
            "duration_ms": self.total_execution_time_ms,
            "entities_processed": len(self.successful_entities),
            "entities_failed": len(self.failed_entities),
            "total_records": self.total_records_processed,
            "environment": self.environment,
            "status": "success" if not self.failed_entities else "partial" if self.successful_entities else "failed"
        }