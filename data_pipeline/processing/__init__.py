"""
Data processing module for enrichment, text preparation, and embedding generation.

This module provides distributed data processing capabilities using
Apache Spark for data enrichment, text processing, and embedding generation.
"""

from data_pipeline.processing.embedding_generator import (
    ChunkingConfig,
    ChunkingMethod,
    DistributedEmbeddingGenerator,
    EmbeddingGeneratorConfig,
    EmbeddingProvider,
    ProviderConfig,
)
from data_pipeline.processing.enrichment_engine import (
    DataEnrichmentEngine,
    EnrichmentConfig,
    LocationMapping,
)
from data_pipeline.processing.text_processor import (
    TextProcessor,
    TextProcessingConfig,
)

__all__ = [
    # Enrichment
    "DataEnrichmentEngine",
    "EnrichmentConfig",
    "LocationMapping",
    # Text Processing
    "TextProcessor",
    "TextProcessingConfig",
    # Embedding Generation
    "DistributedEmbeddingGenerator",
    "EmbeddingGeneratorConfig",
    "ProviderConfig",
    "EmbeddingProvider",
    "ChunkingConfig",
    "ChunkingMethod",
]