"""Constants for MCP Server."""

from typing import Final

# Elasticsearch field names
class ElasticsearchFields:
    """Elasticsearch field name constants."""
    
    # Property fields
    PROPERTY_TYPE: Final[str] = "property_type"
    PRICE: Final[str] = "price"
    BEDROOMS: Final[str] = "bedrooms"
    BATHROOMS: Final[str] = "bathrooms"
    SQUARE_FEET: Final[str] = "square_feet"
    STATUS: Final[str] = "status"
    DAYS_ON_MARKET: Final[str] = "days_on_market"
    LISTING_ID: Final[str] = "listing_id"
    DESCRIPTION: Final[str] = "description"
    FEATURES: Final[str] = "features"
    AMENITIES: Final[str] = "amenities"
    SEARCH_TAGS: Final[str] = "search_tags"
    EMBEDDING: Final[str] = "embedding"
    
    # Address fields
    ADDRESS_CITY: Final[str] = "address.city"
    ADDRESS_STATE: Final[str] = "address.state"
    ADDRESS_ZIP: Final[str] = "address.zip_code"
    ADDRESS_STREET: Final[str] = "address.street"
    ADDRESS_LOCATION: Final[str] = "address.location"
    
    # Neighborhood fields
    NEIGHBORHOOD_ID: Final[str] = "neighborhood.id"
    NEIGHBORHOOD_NAME: Final[str] = "neighborhood.name"
    
    # Wikipedia fields
    WIKI_PAGE_ID: Final[str] = "page_id"
    WIKI_TITLE: Final[str] = "title"
    WIKI_CITY: Final[str] = "city"
    WIKI_STATE: Final[str] = "state"
    WIKI_CATEGORIES: Final[str] = "categories"
    WIKI_RELEVANCE: Final[str] = "relevance_score"
    WIKI_SHORT_SUMMARY: Final[str] = "short_summary"
    WIKI_LONG_SUMMARY: Final[str] = "long_summary"
    WIKI_FULL_CONTENT: Final[str] = "full_content"
    WIKI_KEY_TOPICS: Final[str] = "key_topics"
    WIKI_CHUNK_TEXT: Final[str] = "chunk_text"
    
    # Common fields
    SCORE: Final[str] = "_score"
    SOURCE: Final[str] = "_source"
    INDEX: Final[str] = "_index"
    ID: Final[str] = "_id"
    HIGHLIGHT: Final[str] = "highlight"
    EXPLANATION: Final[str] = "_explanation"


class SearchConstants:
    """Search-related constants."""
    
    # Search types
    SEARCH_TYPE_SEMANTIC: Final[str] = "semantic"
    SEARCH_TYPE_TEXT: Final[str] = "text"
    SEARCH_TYPE_HYBRID: Final[str] = "hybrid"
    
    # Search modes
    SEARCH_IN_FULL: Final[str] = "full"
    SEARCH_IN_SUMMARIES: Final[str] = "summaries"
    SEARCH_IN_CHUNKS: Final[str] = "chunks"
    
    # Sort orders
    SORT_ASC: Final[str] = "asc"
    SORT_DESC: Final[str] = "desc"
    
    # Sort fields
    SORT_RELEVANCE: Final[str] = "relevance"
    SORT_PRICE: Final[str] = "price"
    SORT_DATE: Final[str] = "date"
    SORT_BEDROOMS: Final[str] = "bedrooms"
    
    # Entity types
    ENTITY_PROPERTY: Final[str] = "property"
    ENTITY_WIKIPEDIA: Final[str] = "wikipedia_article"
    ENTITY_WIKI_CHUNK: Final[str] = "wikipedia_chunk"
    
    # Default values
    DEFAULT_SIZE: Final[int] = 20
    MAX_SIZE: Final[int] = 100
    DEFAULT_TIMEOUT: Final[int] = 30
    DEFAULT_RETRIES: Final[int] = 3
    
    # Score formula
    COSINE_SIMILARITY_FORMULA: Final[str] = "cosineSimilarity(params.query_vector, 'embedding') + 1.0"


class AggregationNames:
    """Aggregation name constants."""
    
    PROPERTY_TYPES: Final[str] = "property_types"
    PRICE_RANGES: Final[str] = "price_ranges"
    BEDROOM_COUNTS: Final[str] = "bedroom_counts"
    CITIES: Final[str] = "cities"
    AVG_PRICE: Final[str] = "avg_price"
    AVG_SQFT: Final[str] = "avg_sqft"


class PriceRanges:
    """Price range constants for aggregations."""
    
    UNDER_200K: Final[tuple] = (0, 200000, "Under $200k")
    RANGE_200K_500K: Final[tuple] = (200000, 500000, "$200k-$500k")
    RANGE_500K_1M: Final[tuple] = (500000, 1000000, "$500k-$1M")
    OVER_1M: Final[tuple] = (1000000, float('inf'), "Over $1M")
    
    @classmethod
    def get_ranges(cls) -> list:
        """Get all price ranges for aggregation."""
        return [
            {"to": cls.UNDER_200K[1], "key": cls.UNDER_200K[2]},
            {"from": cls.RANGE_200K_500K[0], "to": cls.RANGE_200K_500K[1], "key": cls.RANGE_200K_500K[2]},
            {"from": cls.RANGE_500K_1M[0], "to": cls.RANGE_500K_1M[1], "key": cls.RANGE_500K_1M[2]},
            {"from": cls.OVER_1M[0], "key": cls.OVER_1M[2]}
        ]


class HealthStatus:
    """Health check status constants."""
    
    HEALTHY: Final[str] = "healthy"
    DEGRADED: Final[str] = "degraded"
    UNHEALTHY: Final[str] = "unhealthy"
    
    # Elasticsearch cluster statuses
    ES_GREEN: Final[str] = "green"
    ES_YELLOW: Final[str] = "yellow"
    ES_RED: Final[str] = "red"


class LogMessages:
    """Log message templates."""
    
    # Service initialization
    SERVICE_INIT_START: Final[str] = "Initializing services"
    SERVICE_INIT_SUCCESS: Final[str] = "All services initialized successfully"
    SERVICE_INIT_FAILED: Final[str] = "Failed to initialize services: {error}"
    
    # Elasticsearch
    ES_CLIENT_INIT: Final[str] = "Elasticsearch client initialized successfully"
    ES_CLIENT_CLOSED: Final[str] = "Elasticsearch client connection closed"
    ES_CONNECTION_FAILED: Final[str] = "Failed to connect to Elasticsearch: {error}"
    
    # Embedding
    EMBEDDING_INIT: Final[str] = "Embedding service initialized with {provider}"
    EMBEDDING_FAILED: Final[str] = "Failed to generate embedding: {error}"
    
    # Search
    SEARCH_EXECUTING: Final[str] = "Executing {type} search: {query}"
    SEARCH_COMPLETED: Final[str] = "Search completed in {time}ms with {hits} results"
    SEARCH_FAILED: Final[str] = "{type} search failed: {error}"
    
    # Health check
    HEALTH_CHECK_START: Final[str] = "Performing health check"
    HEALTH_CHECK_COMPLETE: Final[str] = "Health check complete: {status}"
    
    # MCP Server
    SERVER_STARTING: Final[str] = "Starting MCP Server {name} v{version}"
    SERVER_READY: Final[str] = "MCP server ready: {name} v{version}"
    SERVER_STOPPING: Final[str] = "Stopping MCP server"
    SERVER_STOPPED: Final[str] = "MCP server stopped"