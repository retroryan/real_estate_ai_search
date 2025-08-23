"""
Enumerations for type safety across the Property Finder ecosystem.

Provides consistent enum values for all modules.
"""

from enum import Enum


# Property-related enums
class PropertyType(str, Enum):
    """Property type enumeration."""
    HOUSE = "house"
    CONDO = "condo"
    APARTMENT = "apartment"
    TOWNHOUSE = "townhouse"
    LAND = "land"
    COMMERCIAL = "commercial"
    OTHER = "other"


class PropertyStatus(str, Enum):
    """Property listing status."""
    ACTIVE = "active"
    PENDING = "pending"
    SOLD = "sold"
    OFF_MARKET = "off_market"
    COMING_SOON = "coming_soon"


# Entity and source type enums
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
    WIKIPEDIA_HTML = "wikipedia_html"
    NEO4J_GRAPH = "neo4j_graph"
    EVALUATION_JSON = "evaluation_json"  # JSON file for evaluation testing


# Embedding-related enums
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