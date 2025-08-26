"""
Pydantic models for the common embeddings module.

This module contains all models for the embeddings processing pipeline.
"""

# Import from base module
from .base import (
    BaseEnrichedModel,
    BaseMetadata,
    generate_uuid,
    ISODatetime,
)

# Import from enums module
from .enums import (
    # Property enums
    PropertyType,
    PropertyStatus,
    # Entity enums
    EntityType,
    SourceType,
    # Embedding enums
    EmbeddingProvider,
    ChunkingMethod,
    PreprocessingStep,
    AugmentationType,
)

# Import from geographic module
from .geographic import (
    GeoLocation,
    GeoPolygon,
    EnrichedAddress,
    LocationInfo,
)

# Import from entities module
from .entities import (
    EmbeddingData,
    EnrichedProperty,
    EnrichedNeighborhood,
    EnrichedWikipediaArticle,
    WikipediaSummary,
    WikipediaEnrichmentMetadata,
)

# Import from config module
from .config import (
    EmbeddingConfig,
    ChromaDBConfig,
    Config,
    ChunkingConfig,
    ProcessingConfig,
    ExtendedConfig,
    BaseConfig,
)

# Import from exceptions module
from .exceptions import (
    PropertyFinderError,
    ConfigurationError,
    DataLoadingError,
    StorageError,
    ValidationError,
    MetadataError,
    EmbeddingGenerationError,
    ChunkingError,
    ProviderError,
)

from .metadata import (
    PropertyMetadata,
    NeighborhoodMetadata,
    WikipediaMetadata,
    ChunkMetadata,
    EmbeddingContextMetadata,
    ProcessingMetadata,
)


from .interfaces import (
    IDataLoader,
    IEmbeddingProvider,
    IVectorStore,
)


from .processing import (
    ProcessingChunkMetadata,
    ProcessingResult,
    BatchProcessingResult,
    DocumentBatch,
)

from .statistics import (
    CollectionInfo,
    PipelineStatistics,
    BatchProcessorStatistics,
    SystemStatistics,
)

from .correlation import (
    ChunkGroup,
    ValidationResult,
    CollectionHealth,
    CorrelationMapping,
    StorageOperation,
)

__all__ = [
    # Base models
    "BaseEnrichedModel",
    "BaseMetadata",
    "generate_uuid",
    "ISODatetime",
    
    # Enums
    "PropertyType",
    "PropertyStatus",
    "EntityType",
    "SourceType",
    "EmbeddingProvider",
    "ChunkingMethod",
    "PreprocessingStep",
    "AugmentationType",
    
    # Geographic models
    "GeoLocation",
    "GeoPolygon",
    "EnrichedAddress",
    "LocationInfo",
    
    # Entity models
    "EmbeddingData",
    "EnrichedProperty",
    "EnrichedNeighborhood",
    "EnrichedWikipediaArticle",
    "WikipediaSummary",
    "WikipediaEnrichmentMetadata",
    
    # Configuration
    "EmbeddingConfig",
    "ChromaDBConfig",
    "Config",
    "BaseConfig",
    "ChunkingConfig",
    "ProcessingConfig",
    "ExtendedConfig",
    
    # Exceptions
    "PropertyFinderError",
    "ConfigurationError",
    "DataLoadingError",
    "StorageError",
    "ValidationError",
    "MetadataError",
    "EmbeddingGenerationError",
    "ChunkingError",
    "ProviderError",
    
    # Metadata models
    "PropertyMetadata",
    "NeighborhoodMetadata",
    "WikipediaMetadata",
    "ChunkMetadata",
    "EmbeddingContextMetadata",
    "ProcessingMetadata",
    
    # Interfaces
    "IDataLoader",
    "IEmbeddingProvider",
    "IVectorStore",
    
    # Processing models
    "ProcessingChunkMetadata",
    "ProcessingResult",
    "BatchProcessingResult",
    "DocumentBatch",
    
    # Statistics models
    "CollectionInfo",
    "PipelineStatistics",
    "BatchProcessorStatistics",
    "SystemStatistics",
    
    # Correlation models
    "ChunkGroup",
    "ValidationResult",
    "CollectionHealth",
    "CorrelationMapping",
    "StorageOperation",
]