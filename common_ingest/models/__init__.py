"""
Pydantic models for enriched data structures.
"""

from .base import BaseEnrichedModel, generate_uuid
from .embedding import (
    EmbeddingData,
    PropertyEmbedding,
    WikipediaEmbedding,
    NeighborhoodEmbedding
)
from .property import (
    PropertyType,
    PropertyStatus,
    GeoLocation,
    GeoPolygon,
    EnrichedAddress,
    EnrichedProperty,
    EnrichedNeighborhood
)
from .wikipedia import (
    LocationInfo,
    EnrichedWikipediaArticle,
    WikipediaSummary,
    WikipediaEnrichmentMetadata
)

__all__ = [
    # Base
    'BaseEnrichedModel',
    'generate_uuid',
    
    # Embedding models
    'EmbeddingData',
    'PropertyEmbedding',
    'WikipediaEmbedding',
    'NeighborhoodEmbedding',
    
    # Property models
    'PropertyType',
    'PropertyStatus',
    'GeoLocation',
    'GeoPolygon',
    'EnrichedAddress',
    'EnrichedProperty',
    'EnrichedNeighborhood',
    
    # Wikipedia models
    'LocationInfo',
    'EnrichedWikipediaArticle',
    'WikipediaSummary',
    'WikipediaEnrichmentMetadata',
]