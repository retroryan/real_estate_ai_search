"""
Pydantic models for the common embeddings module.

This module defines all data models, configurations, and metadata structures
following the enhanced metadata management system for correlation.
"""

from .enums import (
    EntityType,
    SourceType, 
    EmbeddingProvider,
    ChunkingMethod,
    PreprocessingStep,
    AugmentationType,
)

from .metadata import (
    BaseMetadata,
    PropertyMetadata,
    NeighborhoodMetadata, 
    WikipediaMetadata,
    ChunkMetadata,
    EmbeddingContextMetadata,
    ProcessingMetadata,
)

from .config import (
    EmbeddingConfig,
    ChromaDBConfig,
    ChunkingConfig,
    Config,
)

from .interfaces import (
    IDataLoader,
    IEmbeddingProvider,
    IVectorStore,
)

from .exceptions import (
    ConfigurationError,
    DataLoadingError,
    EmbeddingGenerationError,
    StorageError,
    ProviderError,
)

from .processing import (
    ChunkMetadata as ProcessingChunkMetadata,  # Avoid conflict with metadata.ChunkMetadata
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
    # Enums
    "EntityType",
    "SourceType",
    "EmbeddingProvider",
    "ChunkingMethod",
    "PreprocessingStep",
    "AugmentationType",
    
    # Metadata
    "BaseMetadata",
    "PropertyMetadata",
    "NeighborhoodMetadata",
    "WikipediaMetadata",
    "ChunkMetadata",
    "EmbeddingContextMetadata",
    "ProcessingMetadata",
    
    # Configuration
    "EmbeddingConfig",
    "ChromaDBConfig",
    "ChunkingConfig",
    "Config",
    
    # Interfaces
    "IDataLoader",
    "IEmbeddingProvider",
    "IVectorStore",
    
    # Exceptions
    "ConfigurationError",
    "DataLoadingError",
    "EmbeddingGenerationError",
    "StorageError",
    "ProviderError",
    
    # Processing
    "ProcessingChunkMetadata",
    "ProcessingResult", 
    "BatchProcessingResult",
    "DocumentBatch",
    
    # Statistics
    "CollectionInfo",
    "PipelineStatistics",
    "BatchProcessorStatistics",
    "SystemStatistics",
    
    # Correlation and Advanced Operations
    "ChunkGroup",
    "ValidationResult",
    "CollectionHealth",
    "CorrelationMapping",
    "StorageOperation",
]