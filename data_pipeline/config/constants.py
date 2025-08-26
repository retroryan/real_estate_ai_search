"""
Constants and configuration values for the data pipeline.

This module centralizes all magic numbers, thresholds, and configuration
constants used throughout the pipeline.
"""

# ============================================================================
# Processing Limits and Batch Sizes
# ============================================================================

# Maximum number of records to collect to driver (for safety)
MAX_COLLECT_SIZE = 100000

# Batch size for processing large datasets
DEFAULT_BATCH_SIZE = 10000

# Maximum batch size for embedding generation
EMBEDDING_BATCH_SIZE = 100

# Default sample size for testing
DEFAULT_SAMPLE_SIZE = 10

# ============================================================================
# Entity Defaults
# ============================================================================

# Default values for optional entity fields
DEFAULT_CITY_COUNT = 0
DEFAULT_MEDIAN_PRICE = None
DEFAULT_FEATURE_COUNT = 0
DEFAULT_CONFIDENCE_SCORE = 0.0
DEFAULT_SIMILARITY_THRESHOLD = 0.8

# ============================================================================
# Embedding Configuration
# ============================================================================

# Embedding dimensions by provider
EMBEDDING_DIMENSIONS = {
    "voyage-3": 1024,
    "voyage-large-2": 1536, 
    "voyage-code-2": 1536,
    "openai": 1536,
    "text-embedding-ada-002": 1536,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "gemini": 768,
    "mock": 1024
}

# Default embedding model names
DEFAULT_EMBEDDING_MODELS = {
    "voyage": "voyage-3",
    "openai": "text-embedding-ada-002",
    "gemini": "models/embedding-001",
    "mock": "mock-model"
}

# ============================================================================
# Price Range Configuration
# ============================================================================

# Price range boundaries (in dollars)
PRICE_RANGES = [
    (0, 250000, "Under 250K"),
    (250000, 500000, "250K-500K"),
    (500000, 750000, "500K-750K"),
    (750000, 1000000, "750K-1M"),
    (1000000, 2000000, "1M-2M"),
    (2000000, 5000000, "2M-5M"),
    (5000000, float('inf'), "Over 5M")
]

# ============================================================================
# Geographic Hierarchy
# ============================================================================

# Geographic levels
GEO_LEVELS = ["neighborhood", "city", "county", "state", "country"]

# Default country
DEFAULT_COUNTRY = "USA"

# State abbreviations (for validation)
VALID_STATE_CODES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
]

# ============================================================================
# Feature Categories
# ============================================================================

# Feature category mappings
FEATURE_CATEGORIES = {
    "amenities": ["pool", "gym", "spa", "sauna", "tennis court", "clubhouse"],
    "parking": ["garage", "carport", "driveway", "street parking", "covered parking"],
    "outdoor": ["garden", "patio", "deck", "balcony", "yard", "rooftop"],
    "kitchen": ["granite counters", "stainless appliances", "island", "pantry"],
    "security": ["gated", "security system", "doorman", "camera", "alarm"],
    "comfort": ["ac", "heating", "fireplace", "ceiling fans", "insulation"],
    "views": ["city view", "water view", "mountain view", "park view", "skyline view"]
}

# ============================================================================
# Topic Clustering
# ============================================================================

# Topic categories for clustering
TOPIC_CATEGORIES = {
    "education": ["school", "university", "college", "education", "academic"],
    "transportation": ["transit", "subway", "bus", "train", "highway", "airport"],
    "entertainment": ["theater", "cinema", "concert", "museum", "gallery", "nightlife"],
    "shopping": ["mall", "shopping", "retail", "stores", "boutique", "market"],
    "dining": ["restaurant", "cafe", "bar", "food", "cuisine", "dining"],
    "nature": ["park", "beach", "trail", "forest", "mountain", "lake", "river"],
    "healthcare": ["hospital", "medical", "clinic", "doctor", "health", "wellness"],
    "business": ["downtown", "financial", "office", "business", "commercial", "tech"]
}

# Default topic category
DEFAULT_TOPIC_CATEGORY = "general"

# ============================================================================
# Similarity and Scoring
# ============================================================================

# Similarity thresholds
HIGH_SIMILARITY_THRESHOLD = 0.9
MEDIUM_SIMILARITY_THRESHOLD = 0.7
LOW_SIMILARITY_THRESHOLD = 0.5

# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.8
MEDIUM_CONFIDENCE_THRESHOLD = 0.6
LOW_CONFIDENCE_THRESHOLD = 0.4

# Score weights for hybrid search
VECTOR_WEIGHT = 0.7
GRAPH_WEIGHT = 0.3

# ============================================================================
# Data Quality
# ============================================================================

# Minimum data quality thresholds
MIN_PROPERTY_FIELDS = 5  # Minimum non-null fields for valid property
MIN_FEATURE_LENGTH = 3    # Minimum character length for valid feature
MIN_DESCRIPTION_LENGTH = 10  # Minimum description length
MAX_DESCRIPTION_LENGTH = 10000  # Maximum description length

# Data validation patterns
VALID_LISTING_ID_PATTERN = r"^[a-zA-Z0-9\-_]+$"
VALID_EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
VALID_PHONE_PATTERN = r"^\+?1?\d{10,14}$"

# ============================================================================
# Timeout and Retry Configuration
# ============================================================================

# Network timeouts (in seconds)
DEFAULT_REQUEST_TIMEOUT = 30
EMBEDDING_REQUEST_TIMEOUT = 60
NEO4J_QUERY_TIMEOUT = 120

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2
RETRY_MAX_WAIT = 30

# ============================================================================
# Logging and Monitoring
# ============================================================================

# Log levels for different components
LOG_LEVELS = {
    "pipeline": "INFO",
    "extractor": "INFO",
    "writer": "INFO",
    "embedding": "WARNING",
    "validation": "WARNING"
}

# Metrics collection intervals (in seconds)
METRICS_COLLECTION_INTERVAL = 60
HEALTH_CHECK_INTERVAL = 30

# ============================================================================
# File and Path Configuration
# ============================================================================

# File extensions
PARQUET_EXTENSION = ".parquet"
JSON_EXTENSION = ".json"
CSV_EXTENSION = ".csv"

# Default paths
DEFAULT_OUTPUT_PATH = "data/processed"
DEFAULT_CHECKPOINT_PATH = "data/checkpoints"
DEFAULT_LOG_PATH = "logs"

# ============================================================================
# Neo4j Configuration
# ============================================================================

# Neo4j batch sizes
NEO4J_BATCH_SIZE = 1000
NEO4J_RELATIONSHIP_BATCH_SIZE = 5000

# Neo4j connection pool
NEO4J_MAX_CONNECTION_POOL_SIZE = 50
NEO4J_CONNECTION_ACQUISITION_TIMEOUT = 60

# ============================================================================
# Spark Configuration
# ============================================================================

# Spark memory settings
SPARK_DRIVER_MEMORY = "4g"
SPARK_EXECUTOR_MEMORY = "2g"
SPARK_MAX_RESULT_SIZE = "2g"

# Spark parallelism
DEFAULT_PARALLELISM = 200
SHUFFLE_PARTITIONS = 200

# ============================================================================
# Data Types and Schemas
# ============================================================================

# Supported data types for validation
SUPPORTED_PROPERTY_TYPES = [
    "house", "condo", "apartment", "townhouse", "multi-family",
    "land", "commercial", "industrial", "mixed-use", "other"
]

# Required fields for entities
REQUIRED_PROPERTY_FIELDS = ["listing_id", "listing_price", "bedrooms", "bathrooms"]
REQUIRED_NEIGHBORHOOD_FIELDS = ["neighborhood_id", "name", "city", "state"]
REQUIRED_WIKIPEDIA_FIELDS = ["page_id", "title", "content"]