"""
Common Embeddings Module - Unified embedding generation and storage system.

This module provides a centralized system for generating, storing, and managing
embeddings from multiple data sources with comprehensive metadata tracking for
correlation with source data.
"""

__version__ = "0.1.0"

from common.property_finder_models import (
    # Enums
    EntityType,
    SourceType,
    EmbeddingProvider,
    
    # Metadata Models
    BaseMetadata,
    
    # Configuration Models
    EmbeddingConfig,
    ChromaDBConfig,
    Config,
)

from .models import (
    # Enums specific to embeddings
    ChunkingMethod,
    
    # Configuration specific to embeddings
    ChunkingConfig,
    
    # Metadata Models
    PropertyMetadata,
    NeighborhoodMetadata,
    WikipediaMetadata,
    
    # Correlation Models
    ChunkGroup,
    ValidationResult,
    CollectionHealth,
    CorrelationMapping,
    StorageOperation,
)

from .pipeline import EmbeddingPipeline
from .embedding.factory import EmbeddingFactory
from .processing.chunking import TextChunker
from .processing.batch_processor import BatchProcessor
from .storage import ChromaDBStore
from .storage.enhanced_chromadb import EnhancedChromaDBManager
from .storage.query_manager import QueryManager
from .utils.correlation import CorrelationValidator, ChunkReconstructor
from .correlation import CorrelationManager, EnrichmentEngine
from .services import CollectionManager

# Setup logging
from .utils import setup_logging
setup_logging()

__all__ = [
    # Enums
    "EntityType",
    "SourceType",
    "EmbeddingProvider", 
    "ChunkingMethod",
    
    # Metadata
    "BaseMetadata",
    "PropertyMetadata",
    "NeighborhoodMetadata",
    "WikipediaMetadata",
    
    # Correlation Models
    "ChunkGroup",
    "ValidationResult",
    "CollectionHealth",
    "CorrelationMapping",
    "StorageOperation",
    
    # Configuration
    "EmbeddingConfig",
    "ChromaDBConfig",
    "ChunkingConfig",
    "Config",
    
    # Core Components
    "EmbeddingPipeline",
    "EmbeddingFactory",
    "TextChunker",
    "BatchProcessor",
    
    # Storage Components
    "ChromaDBStore",
    "EnhancedChromaDBManager",
    "QueryManager",
    
    # Utilities
    "CorrelationValidator",
    "ChunkReconstructor",
    
    # Correlation Engine
    "CorrelationManager",
    "EnrichmentEngine",
    
    # Services
    "CollectionManager",
]