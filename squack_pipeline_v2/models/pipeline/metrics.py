"""Pipeline metrics models."""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field, computed_field, ConfigDict


class StageMetrics(BaseModel):
    """Metrics for a single pipeline stage."""
    
    model_config = ConfigDict(frozen=True)
    
    stage_name: str = Field(description="Name of the stage")
    input_records: int = Field(ge=0, description="Number of input records")
    output_records: int = Field(ge=0, description="Number of output records")
    dropped_records: int = Field(ge=0, description="Number of dropped records")
    error_count: int = Field(default=0, ge=0, description="Number of errors")
    
    start_time: datetime = Field(description="Stage start time")
    end_time: Optional[datetime] = Field(default=None, description="Stage end time")
    
    memory_usage_mb: Optional[float] = Field(default=None, ge=0, description="Memory usage in MB")
    
    @computed_field
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate stage duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @computed_field
    @property
    def records_per_second(self) -> Optional[float]:
        """Calculate processing rate."""
        if self.duration_seconds and self.duration_seconds > 0:
            return self.output_records / self.duration_seconds
        return None
    
    @computed_field
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.input_records
        if total > 0:
            return (total - self.dropped_records - self.error_count) / total
        return 1.0


class EntityMetrics(BaseModel):
    """Metrics for a single entity type through all stages."""
    
    model_config = ConfigDict(frozen=True)
    
    entity_type: str = Field(description="Entity type")
    
    # Stage metrics
    bronze_metrics: Optional[StageMetrics] = Field(default=None, description="Bronze stage metrics")
    silver_metrics: Optional[StageMetrics] = Field(default=None, description="Silver stage metrics")
    gold_metrics: Optional[StageMetrics] = Field(default=None, description="Gold stage metrics")
    
    # Output metrics
    embeddings_generated: int = Field(default=0, ge=0, description="Number of embeddings")
    parquet_files_written: int = Field(default=0, ge=0, description="Parquet files written")
    elasticsearch_documents: int = Field(default=0, ge=0, description="ES documents indexed")
    
    # Quality metrics
    data_quality_score: float = Field(default=1.0, ge=0, le=1, description="Overall data quality")
    validation_passed: bool = Field(default=True, description="Validation status")
    
    @computed_field
    @property
    def total_records(self) -> int:
        """Get final record count."""
        if self.gold_metrics:
            return self.gold_metrics.output_records
        elif self.silver_metrics:
            return self.silver_metrics.output_records
        elif self.bronze_metrics:
            return self.bronze_metrics.output_records
        return 0
    
    @computed_field
    @property
    def total_duration_seconds(self) -> float:
        """Calculate total processing time."""
        duration = 0.0
        for metrics in [self.bronze_metrics, self.silver_metrics, self.gold_metrics]:
            if metrics and metrics.duration_seconds:
                duration += metrics.duration_seconds
        return duration


class PipelineMetrics(BaseModel):
    """Overall pipeline execution metrics."""
    
    model_config = ConfigDict(frozen=True)
    
    pipeline_id: str = Field(description="Unique pipeline execution ID")
    start_time: datetime = Field(description="Pipeline start time")
    end_time: Optional[datetime] = Field(default=None, description="Pipeline end time")
    
    # Entity metrics
    property_metrics: Optional[EntityMetrics] = Field(default=None, description="Property metrics")
    neighborhood_metrics: Optional[EntityMetrics] = Field(default=None, description="Neighborhood metrics")
    wikipedia_metrics: Optional[EntityMetrics] = Field(default=None, description="Wikipedia metrics")
    
    # Overall counts
    total_input_records: int = Field(default=0, ge=0, description="Total input records")
    total_output_records: int = Field(default=0, ge=0, description="Total output records")
    total_embeddings: int = Field(default=0, ge=0, description="Total embeddings generated")
    
    # Status
    status: str = Field(default="running", description="Pipeline status")
    error_messages: list[str] = Field(default_factory=list, description="Error messages")
    
    @computed_field
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate total pipeline duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    @computed_field
    @property
    def is_successful(self) -> bool:
        """Check if pipeline completed successfully."""
        return self.status == "completed" and len(self.error_messages) == 0
    
    @computed_field
    @property
    def entities_processed(self) -> list[str]:
        """List entities that were processed."""
        entities = []
        if self.property_metrics:
            entities.append("property")
        if self.neighborhood_metrics:
            entities.append("neighborhood")
        if self.wikipedia_metrics:
            entities.append("wikipedia")
        return entities