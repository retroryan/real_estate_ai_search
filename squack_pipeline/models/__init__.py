"""Pydantic V2 data models for SQUACK pipeline."""

from squack_pipeline.models.enriched import (
    EnrichedNeighborhood,
    EnrichedProperty,
    PipelineOutput,
)
from squack_pipeline.models.location import (
    Demographics,
    GraphMetadata,
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
    "GraphMetadata",
    # Wikipedia models
    "WikipediaArticle",
    # Enriched models
    "EnrichedProperty",
    "EnrichedNeighborhood",
    "PipelineOutput",
]