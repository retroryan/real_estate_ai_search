"""Pydantic V2 data models for SQUACK pipeline."""

from squack_pipeline.models.enriched import (
    EnrichedNeighborhood,
    EnrichedProperty,
    PipelineOutput,
)
from squack_pipeline.models.location import (
    Demographics,
    WikipediaCorrelations,
    Location,
    Neighborhood,
    NeighborhoodCharacteristics,
    ParentGeography,
    WikiArticle,
)
from squack_pipeline.models.property import (
    Address,
    Coordinates,
    PriceHistory,
    Property,
    PropertyDetails,
)
from squack_pipeline.models.wikipedia import WikipediaArticle
from squack_pipeline.models.embedding_models import (
    EmbeddingMetadata,
    EmbeddingNodeData,
    EmbeddingBatch,
)
from squack_pipeline.models.processing_models import (
    EntityType,
    MedallionTier,
    ProcessingStage,
    TableIdentifier,
    ProcessingContext,
    ProcessingResult,
    EntityProcessorConfig,
    ProcessingPipeline,
    create_property_processing_context,
    create_standard_property_pipeline,
)

__all__ = [
    # Property models
    "Property",
    "Address",
    "Coordinates",
    "PropertyDetails",
    "PriceHistory",
    # Location models
    "Location",
    "Neighborhood",
    "NeighborhoodCharacteristics",
    "Demographics",
    "WikiArticle",
    "ParentGeography",
    "WikipediaCorrelations",
    # Wikipedia models
    "WikipediaArticle",
    # Enriched models
    "EnrichedProperty",
    "EnrichedNeighborhood",
    "PipelineOutput",
    # Embedding models
    "EmbeddingMetadata",
    "EmbeddingNodeData", 
    "EmbeddingBatch",
    # Processing models
    "EntityType",
    "MedallionTier",
    "ProcessingStage",
    "TableIdentifier",
    "ProcessingContext",
    "ProcessingResult",
    "EntityProcessorConfig",
    "ProcessingPipeline",
    "create_property_processing_context",
    "create_standard_property_pipeline",
]