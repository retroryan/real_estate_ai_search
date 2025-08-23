"""
Enumerations for type safety in the common embeddings module.

These enums ensure consistent values across the system and provide
clear options for configuration and metadata.
"""

from enum import Enum


class EntityType(str, Enum):
    """Types of entities that can have embeddings."""
    PROPERTY = "property"
    NEIGHBORHOOD = "neighborhood"
    WIKIPEDIA_ARTICLE = "wikipedia_article"
    WIKIPEDIA_SUMMARY = "wikipedia_summary"


class SourceType(str, Enum):
    """Types of data sources for correlation."""
    PROPERTY_JSON = "property_json"
    NEIGHBORHOOD_JSON = "neighborhood_json"
    WIKIPEDIA_DB = "wikipedia_db"
    WIKIPEDIA_HTML = "wikipedia_html"  # HTML files from Wikipedia pages
    NEO4J_GRAPH = "neo4j_graph"


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    GEMINI = "gemini"
    VOYAGE = "voyage"
    COHERE = "cohere"


class ChunkingMethod(str, Enum):
    """Text chunking strategies."""
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