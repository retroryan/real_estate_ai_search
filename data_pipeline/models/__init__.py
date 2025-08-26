"""
Data pipeline models module.

This module provides Pydantic models for configuration, validation,
and result tracking throughout the data pipeline.
"""

# Processing result models
from data_pipeline.models.processing_results import (
    ValidationStats,
    EnrichmentStats,
    TextProcessingStats,
    EmbeddingStats,
    WriterStats,
    PropertyProcessingResult,
    NeighborhoodProcessingResult,
    WikipediaProcessingResult,
    PipelineExecutionResult,
)

# Spark models for schema generation
from data_pipeline.models.spark_models import (
    # Property models
    Address,
    Coordinates,
    PropertyDetails,
    PriceHistory,
    Property,
    FlattenedProperty,
    
    # Neighborhood models
    Demographics,
    Neighborhood,
    FlattenedNeighborhood,
    
    # Other models
    Location,
    WikipediaArticle,
    Relationship,
)

# Enrichment models
from data_pipeline.models.enrichment import (
    Landmark,
    NearbyPOI,
    LocationContext,
    NeighborhoodContext,
    EnrichmentData,
    WikipediaEnrichmentResult,
)

__all__ = [
    # Statistics models
    "ValidationStats",
    "EnrichmentStats", 
    "TextProcessingStats",
    "EmbeddingStats",
    "WriterStats",
    
    # Entity processing results
    "PropertyProcessingResult",
    "NeighborhoodProcessingResult",
    "WikipediaProcessingResult",
    
    # Pipeline execution
    "PipelineExecutionResult",
    
    # Spark models - Property
    "Address",
    "Coordinates",
    "PropertyDetails",
    "PriceHistory",
    "Property",
    "FlattenedProperty",
    
    # Spark models - Neighborhood
    "Demographics",
    "Neighborhood",
    "FlattenedNeighborhood",
    
    # Spark models - Other
    "Location",
    "WikipediaArticle",
    "Relationship",
    
    # Enrichment models
    "Landmark",
    "NearbyPOI",
    "LocationContext",
    "NeighborhoodContext",
    "EnrichmentData",
    "WikipediaEnrichmentResult",
]