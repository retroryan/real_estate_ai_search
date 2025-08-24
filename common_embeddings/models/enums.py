"""
Enumerations specific to embeddings processing.

Core enums (EntityType, SourceType, EmbeddingProvider) are imported 
from property_finder_models.
"""

from enum import Enum


class ChunkingMethod(str, Enum):
    """Text chunking strategies for embeddings."""
    SIMPLE = "simple"
    SEMANTIC = "semantic"
    SENTENCE = "sentence"
    NONE = "none"


class PreprocessingStep(str, Enum):
    """Text preprocessing steps that can be applied."""
    LOWERCASE = "lowercase"
    REMOVE_PUNCTUATION = "remove_punctuation"
    REMOVE_STOPWORDS = "remove_stopwords"
    NORMALIZE_WHITESPACE = "normalize_whitespace"
    STRIP_HTML = "strip_html"


class AugmentationType(str, Enum):
    """Types of text augmentation for embeddings."""
    SUMMARY = "summary"
    CONTEXT = "context"
    NONE = "none"