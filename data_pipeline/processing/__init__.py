"""
Entity-specific data processing module.

This module provides entity-specific processors for properties, neighborhoods,
and Wikipedia articles using entity-specific processing logic.
"""

# Entity-specific text processors
from data_pipeline.processing.property_text_processor import (
    PropertyTextProcessor,
    PropertyTextConfig,
)
from data_pipeline.processing.neighborhood_text_processor import (
    NeighborhoodTextProcessor,
    NeighborhoodTextConfig,
)
from data_pipeline.processing.wikipedia_text_processor import (
    WikipediaTextProcessor,
    WikipediaTextConfig,
)

# Entity-specific embedding generators
from data_pipeline.processing.entity_embeddings import (
    PropertyEmbeddingGenerator,
    NeighborhoodEmbeddingGenerator,
    WikipediaEmbeddingGenerator,
)

__all__ = [
    # Property Processing
    "PropertyTextProcessor",
    "PropertyTextConfig",
    "PropertyEmbeddingGenerator",
    
    # Neighborhood Processing
    "NeighborhoodTextProcessor", 
    "NeighborhoodTextConfig",
    "NeighborhoodEmbeddingGenerator",
    
    # Wikipedia Processing
    "WikipediaTextProcessor",
    "WikipediaTextConfig", 
    "WikipediaEmbeddingGenerator",
]