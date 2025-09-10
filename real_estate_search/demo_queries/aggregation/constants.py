"""
Configuration values and defaults for aggregation queries.

This module centralizes all configuration constants used throughout
the aggregation functionality.
"""

# Default aggregation parameters
DEFAULT_NEIGHBORHOOD_SIZE: int = 20
DEFAULT_PRICE_INTERVAL: int = 100000
DEFAULT_MIN_PRICE: float = 0
DEFAULT_MAX_PRICE: float = 2000000

# Index configuration
PROPERTIES_INDEX: str = "properties"

# Field names for aggregations
FIELD_LISTING_ID: str = "listing_id"
FIELD_NEIGHBORHOOD_ID: str = "neighborhood_id"
FIELD_PRICE: str = "price"
FIELD_BEDROOMS: str = "bedrooms"
FIELD_SQUARE_FEET: str = "square_feet"
FIELD_PRICE_PER_SQFT: str = "price_per_sqft"
FIELD_PROPERTY_TYPE: str = "property_type"

# Aggregation configuration
MAX_PROPERTY_TYPES_PER_BUCKET: int = 10
MAX_BUCKETS_TERMS: int = 10
TOP_PROPERTIES_TO_SHOW: int = 5

# Percentile levels for price distribution
PRICE_PERCENTILES: list[int] = [25, 50, 75, 90, 95, 99]
MEDIAN_PERCENTILE: list[int] = [50]

# Display configuration
HISTOGRAM_BAR_MAX_WIDTH: int = 50
PRICE_LABEL_WIDTH: int = 15