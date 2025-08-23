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
    ChunkingMethod,
    PreprocessingStep,
    AugmentationType,
)
from .geographic import GeoLocation, GeoPolygon, EnrichedAddress, LocationInfo
from .entities import (
    EnrichedProperty,
    EnrichedNeighborhood,
    EnrichedWikipediaArticle,
    WikipediaSummary,
    WikipediaEnrichmentMetadata,
)
from .embeddings import (
    EmbeddingData,
    PropertyEmbedding,
    WikipediaEmbedding,
    NeighborhoodEmbedding,
    EmbeddingContextMetadata,
    ProcessingMetadata,
)
from .config import (
    EmbeddingConfig,
    ChromaDBConfig,
    ChunkingConfig,
    ProcessingConfig,
    Config,
)
from .api import (
    PaginationParams,
    PropertyFilter,
    NeighborhoodFilter,
    WikipediaArticleFilter,
    WikipediaSummaryFilter,
    ResponseMetadata,
    ResponseLinks,
    PropertyResponse,
    PropertyListResponse,
    NeighborhoodResponse,
    NeighborhoodListResponse,
    WikipediaArticleResponse,
    WikipediaArticleListResponse,
    WikipediaSummaryResponse,
    WikipediaSummaryListResponse,
    ErrorResponse,
)
from .exceptions import (
    PropertyFinderError,
    CommonEmbeddingsError,
    ConfigurationError,
    DataLoadingError,
    EmbeddingGenerationError,
    StorageError,
    CorrelationError,
    ValidationError,
    MetadataError,
    ChunkingError,
    ProviderError,
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
    "ChunkingMethod",
    "PreprocessingStep",
    "AugmentationType",
    # Geographic
    "GeoLocation",
    "GeoPolygon",
    "EnrichedAddress",
    "LocationInfo",
    # Entities
    "EnrichedProperty",
    "EnrichedNeighborhood",
    "EnrichedWikipediaArticle",
    "WikipediaSummary",
    "WikipediaEnrichmentMetadata",
    # Embeddings
    "EmbeddingData",
    "PropertyEmbedding",
    "WikipediaEmbedding",
    "NeighborhoodEmbedding",
    "EmbeddingContextMetadata",
    "ProcessingMetadata",
    # Config
    "EmbeddingConfig",
    "ChromaDBConfig",
    "ChunkingConfig",
    "ProcessingConfig",
    "Config",
    # API
    "PaginationParams",
    "PropertyFilter",
    "NeighborhoodFilter",
    "WikipediaArticleFilter",
    "WikipediaSummaryFilter",
    "ResponseMetadata",
    "ResponseLinks",
    "PropertyResponse",
    "PropertyListResponse",
    "NeighborhoodResponse",
    "NeighborhoodListResponse",
    "WikipediaArticleResponse",
    "WikipediaArticleListResponse",
    "WikipediaSummaryResponse",
    "WikipediaSummaryListResponse",
    "ErrorResponse",
    # Exceptions
    "PropertyFinderError",
    "CommonEmbeddingsError",
    "ConfigurationError",
    "DataLoadingError",
    "EmbeddingGenerationError",
    "StorageError",
    "CorrelationError",
    "ValidationError",
    "MetadataError",
    "ChunkingError",
    "ProviderError",
]