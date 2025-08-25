"""
Pydantic models for the common embeddings module.

This module imports shared models from common and defines
embeddings-specific models for processing and pipeline operations.
"""

# Import shared models from common
from common.property_finder_models import (
    # Core
    BaseMetadata,
    
    # Enums
    EntityType,
    SourceType,
    EmbeddingProvider,
    
    # Configuration
    EmbeddingConfig,
    ChromaDBConfig,
    Config,
    
    # Exceptions
    ConfigurationError,
    DataLoadingError,
    StorageError,
    ValidationError,
    MetadataError,
)

# Import local embeddings-specific models
from .enums import (
    ChunkingMethod,
    PreprocessingStep,
    AugmentationType,
)

from .metadata import (
    PropertyMetadata,
    NeighborhoodMetadata,
    WikipediaMetadata,
    ChunkMetadata,
    EmbeddingContextMetadata,
    ProcessingMetadata,
)

from .config import (
    ChunkingConfig,
    ProcessingConfig,
    ExtendedConfig,
)

from .interfaces import (
    IDataLoader,
    IEmbeddingProvider,
    IVectorStore,
)

from .exceptions import (
    EmbeddingGenerationError,
    ProviderError,
    ChunkingError,
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
    # From common
    "BaseMetadata",
    "EntityType",
    "SourceType",
    "EmbeddingProvider",
    "EmbeddingConfig",
    "ChromaDBConfig",
    "Config",
    "ConfigurationError",
    "DataLoadingError",
    "StorageError",
    "ValidationError",
    "MetadataError",
    
    # Local enums
    "ChunkingMethod",
    "PreprocessingStep",
    "AugmentationType",
    
    # Local metadata
    "PropertyMetadata",
    "NeighborhoodMetadata",
    "WikipediaMetadata",
    "ChunkMetadata",
    "EmbeddingContextMetadata",
    "ProcessingMetadata",
    
    # Local configuration
    "ChunkingConfig",
    "ProcessingConfig",
    "ExtendedConfig",
    
    # Local interfaces
    "IDataLoader",
    "IEmbeddingProvider",
    "IVectorStore",
    
    # Local exceptions
    "EmbeddingGenerationError",
    "ProviderError",
    "ChunkingError",
    
    # Local processing
    "ProcessingChunkMetadata",
    "ProcessingResult",
    "BatchProcessingResult",
    "DocumentBatch",
    
    # Local statistics
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