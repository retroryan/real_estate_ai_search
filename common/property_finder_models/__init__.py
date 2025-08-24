"""
Property Finder Models

Shared Pydantic models for the Property Finder ecosystem.
"""

__version__ = "1.0.0"

# Import all models for easy access
from .core import BaseEnrichedModel, BaseMetadata, generate_uuid
from .enums import (
    PropertyType,
    PropertyStatus,
    EntityType,
    SourceType,
    EmbeddingProvider,
)
from .geographic import GeoLocation, GeoPolygon, EnrichedAddress, LocationInfo
from .entities import (
    EmbeddingData,
    EnrichedProperty,
    EnrichedNeighborhood,
    EnrichedWikipediaArticle,
    WikipediaSummary,
    WikipediaEnrichmentMetadata,
)
from .config import (
    EmbeddingConfig,
    ChromaDBConfig,
    Config,
)
from .exceptions import (
    PropertyFinderError,
    ConfigurationError,
    DataLoadingError,
    StorageError,
    ValidationError,
    MetadataError,
)

__all__ = [
    # Core
    "BaseEnrichedModel",
    "BaseMetadata",
    "generate_uuid",
    # Enums
    "PropertyType",
    "PropertyStatus",
    "EntityType",
    "SourceType",
    "EmbeddingProvider",
    # Geographic
    "GeoLocation",
    "GeoPolygon",
    "EnrichedAddress",
    "LocationInfo",
    # Entities
    "EmbeddingData",
    "EnrichedProperty",
    "EnrichedNeighborhood",
    "EnrichedWikipediaArticle",
    "WikipediaSummary",
    "WikipediaEnrichmentMetadata",
    # Config
    "EmbeddingConfig",
    "ChromaDBConfig",
    "Config",
    # Exceptions
    "PropertyFinderError",
    "ConfigurationError",
    "DataLoadingError",
    "StorageError",
    "ValidationError",
    "MetadataError",
]