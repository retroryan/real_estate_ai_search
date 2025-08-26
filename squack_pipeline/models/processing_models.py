"""Pydantic models for type-safe entity processing."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Supported entity types for processing."""
    PROPERTY = "property"
    NEIGHBORHOOD = "neighborhood"
    WIKIPEDIA = "wikipedia"
    LOCATION = "location"


class MedallionTier(str, Enum):
    """Medallion architecture tiers."""
    BRONZE = "bronze"
    SILVER = "silver" 
    GOLD = "gold"
    ENRICHED = "enriched"


class ProcessingStage(str, Enum):
    """Processing stages within tiers."""
    RAW_LOAD = "raw_load"
    VALIDATION = "validation"
    CLEANING = "cleaning"
    STANDARDIZATION = "standardization"
    ENRICHMENT = "enrichment"
    GEOGRAPHIC_ENRICHMENT = "geographic_enrichment"
    EMBEDDING_GENERATION = "embedding_generation"


class TableIdentifier(BaseModel):
    """Type-safe table identifier."""
    
    entity_type: EntityType = Field(description="Type of entity")
    tier: MedallionTier = Field(description="Medallion tier")
    timestamp: int = Field(description="Creation timestamp")
    stage: Optional[ProcessingStage] = Field(None, description="Processing stage")
    
    @property
    def table_name(self) -> str:
        """Generate type-safe table name."""
        base_name = f"{self.entity_type.value}_{self.tier.value}_{self.timestamp}"
        if self.stage:
            return f"{base_name}_{self.stage.value}"
        return base_name
    
    @property
    def friendly_name(self) -> str:
        """Human-readable table description."""
        stage_desc = f" ({self.stage.value})" if self.stage else ""
        return f"{self.entity_type.value.title()} {self.tier.value.title()}{stage_desc}"
    
    @classmethod
    def from_table_name(cls, table_name: str) -> Optional['TableIdentifier']:
        """Parse table name back to TableIdentifier."""
        parts = table_name.split('_')
        if len(parts) < 3:
            return None
        
        try:
            entity_type = EntityType(parts[0])
            tier = MedallionTier(parts[1])
            timestamp = int(parts[2])
            stage = ProcessingStage(parts[3]) if len(parts) > 3 else None
            
            return cls(
                entity_type=entity_type,
                tier=tier,
                timestamp=timestamp,
                stage=stage
            )
        except (ValueError, IndexError):
            return None


class ProcessingContext(BaseModel):
    """Context information for entity processing."""
    
    entity_type: EntityType = Field(description="Entity being processed")
    source_tier: MedallionTier = Field(description="Source tier")
    target_tier: MedallionTier = Field(description="Target tier")
    processing_stage: ProcessingStage = Field(description="Current processing stage")
    
    # Table identifiers
    source_table: TableIdentifier = Field(description="Source table identifier")
    target_table: TableIdentifier = Field(description="Target table identifier")
    
    # Processing metadata
    batch_id: str = Field(description="Unique batch identifier")
    started_at: datetime = Field(default_factory=datetime.now, description="Processing start time")
    record_limit: Optional[int] = Field(None, description="Record processing limit")
    
    # Configuration
    validation_enabled: bool = Field(default=True, description="Enable validation")
    enrichment_enabled: bool = Field(default=True, description="Enable enrichment")
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class ProcessingResult(BaseModel):
    """Result of entity processing operation."""
    
    context: ProcessingContext = Field(description="Processing context")
    
    # Results
    success: bool = Field(description="Processing success status")
    records_processed: int = Field(default=0, description="Number of records processed")
    records_created: int = Field(default=0, description="Number of records created")
    
    # Timing
    started_at: datetime = Field(description="Processing start time")
    completed_at: datetime = Field(default_factory=datetime.now, description="Processing completion time")
    
    # Validation results
    validation_passed: bool = Field(default=True, description="Validation status")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors")
    
    # Quality metrics
    data_quality_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Data quality score")
    completeness_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Data completeness score")
    
    # Error information
    error_message: Optional[str] = Field(None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list, description="Processing warnings")
    
    @property
    def processing_time_seconds(self) -> float:
        """Calculate processing time in seconds."""
        return (self.completed_at - self.started_at).total_seconds()
    
    @property
    def records_per_second(self) -> float:
        """Calculate processing rate."""
        time_elapsed = self.processing_time_seconds
        return self.records_processed / time_elapsed if time_elapsed > 0 else 0
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
    
    def add_validation_error(self, error: str) -> None:
        """Add a validation error."""
        self.validation_errors.append(error)
        self.validation_passed = False


class EntityProcessorConfig(BaseModel):
    """Configuration for entity-specific processors."""
    
    entity_type: EntityType = Field(description="Entity type this processor handles")
    supported_tiers: List[MedallionTier] = Field(description="Supported medallion tiers")
    supported_stages: List[ProcessingStage] = Field(description="Supported processing stages")
    
    # Processing options
    batch_size: int = Field(default=1000, ge=1, description="Processing batch size")
    enable_validation: bool = Field(default=True, description="Enable data validation")
    enable_enrichment: bool = Field(default=True, description="Enable data enrichment")
    
    # Quality thresholds
    min_quality_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Minimum quality score")
    min_completeness_score: float = Field(default=0.9, ge=0.0, le=1.0, description="Minimum completeness score")


class ProcessingPipeline(BaseModel):
    """Type-safe processing pipeline definition."""
    
    entity_type: EntityType = Field(description="Entity type for this pipeline")
    pipeline_name: str = Field(description="Human-readable pipeline name")
    
    # Processing flow
    processing_stages: List[ProcessingContext] = Field(description="Ordered processing stages")
    
    # Pipeline metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Pipeline creation time")
    version: str = Field(default="1.0.0", description="Pipeline version")
    
    def get_stage_by_tiers(self, source_tier: MedallionTier, target_tier: MedallionTier) -> Optional[ProcessingContext]:
        """Get processing stage by source and target tiers."""
        for stage in self.processing_stages:
            if stage.source_tier == source_tier and stage.target_tier == target_tier:
                return stage
        return None
    
    def get_next_stage(self, current_tier: MedallionTier) -> Optional[ProcessingContext]:
        """Get the next processing stage after current tier."""
        for stage in self.processing_stages:
            if stage.source_tier == current_tier:
                return stage
        return None


# Factory functions for creating common processing contexts
def create_property_processing_context(
    source_tier: MedallionTier,
    target_tier: MedallionTier,
    stage: ProcessingStage,
    batch_id: str,
    timestamp: int
) -> ProcessingContext:
    """Create processing context for property entities."""
    return ProcessingContext(
        entity_type=EntityType.PROPERTY,
        source_tier=source_tier,
        target_tier=target_tier,
        processing_stage=stage,
        source_table=TableIdentifier(
            entity_type=EntityType.PROPERTY,
            tier=source_tier,
            timestamp=timestamp,
            stage=stage
        ),
        target_table=TableIdentifier(
            entity_type=EntityType.PROPERTY,
            tier=target_tier,
            timestamp=timestamp,
            stage=stage
        ),
        batch_id=batch_id
    )


def create_standard_property_pipeline() -> ProcessingPipeline:
    """Create standard property processing pipeline."""
    timestamp = int(datetime.now().timestamp())
    batch_id = f"property_batch_{timestamp}"
    
    return ProcessingPipeline(
        entity_type=EntityType.PROPERTY,
        pipeline_name="Standard Property Processing Pipeline",
        processing_stages=[
            create_property_processing_context(
                MedallionTier.BRONZE, MedallionTier.SILVER, 
                ProcessingStage.CLEANING, batch_id, timestamp
            ),
            create_property_processing_context(
                MedallionTier.SILVER, MedallionTier.GOLD,
                ProcessingStage.ENRICHMENT, batch_id, timestamp
            ),
            create_property_processing_context(
                MedallionTier.GOLD, MedallionTier.ENRICHED,
                ProcessingStage.GEOGRAPHIC_ENRICHMENT, batch_id, timestamp
            )
        ]
    )