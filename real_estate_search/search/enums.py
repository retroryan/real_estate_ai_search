"""
Search-specific enums for type safety.
All search-related constants are defined here.
"""

from enum import Enum

# For Python 3.10 compatibility
try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        """Backport of StrEnum for Python < 3.11"""
        pass


class QueryType(StrEnum):
    """Types of search queries."""
    TEXT = "text"
    FILTER = "filter"
    GEO = "geo"
    SIMILAR = "similar"
    COMPOUND = "compound"


class QueryOperator(StrEnum):
    """Boolean query operators."""
    MUST = "must"
    SHOULD = "should"
    FILTER = "filter"
    MUST_NOT = "must_not"


class TextQueryType(StrEnum):
    """Elasticsearch text query types."""
    MATCH = "match"
    MULTI_MATCH = "multi_match"
    MATCH_PHRASE = "match_phrase"
    MATCH_ALL = "match_all"
    MORE_LIKE_THIS = "more_like_this"


class RangeOperator(StrEnum):
    """Range query operators."""
    GTE = "gte"
    GT = "gt"
    LTE = "lte"
    LT = "lt"


class GeoDistanceUnit(StrEnum):
    """Units for geographic distance."""
    METERS = "m"
    KILOMETERS = "km"
    MILES = "mi"
    YARDS = "yd"
    FEET = "ft"


class SearchField(StrEnum):
    """Fields used in search queries with boost values."""
    DESCRIPTION_BOOSTED = "description^3"
    SEARCH_TAGS_BOOSTED = "search_tags^2"
    ADDRESS_STREET = "address.street"
    NEIGHBORHOOD_NAME = "neighborhood.name"
    FEATURES = "features"
    AMENITIES = "amenities"
    
    # For exact matching
    LISTING_ID = "listing_id"
    MLS_NUMBER = "mls_number"
    STATUS = "status"
    PROPERTY_TYPE = "property_type"


class AggregationName(StrEnum):
    """Names for search aggregations."""
    PRICE_RANGES = "price_ranges"
    PRICE_HISTOGRAM = "price_histogram"
    PROPERTY_TYPES = "property_types"
    CITIES = "cities"
    NEIGHBORHOODS = "neighborhoods"
    BEDROOM_COUNTS = "bedroom_counts"
    BATHROOM_COUNTS = "bathroom_counts"
    FEATURES_FACET = "features_facet"
    AMENITIES_FACET = "amenities_facet"
    PRICE_STATS = "price_stats"
    SQFT_STATS = "sqft_stats"
    STATUS_DISTRIBUTION = "status_distribution"
    YEAR_BUILT_RANGES = "year_built_ranges"


class PriceRange(StrEnum):
    """Predefined price range labels."""
    UNDER_300K = "Under $300k"
    RANGE_300K_500K = "$300k-$500k"
    RANGE_500K_750K = "$500k-$750k"
    RANGE_750K_1M = "$750k-$1M"
    OVER_1M = "Over $1M"


class HighlightTag(StrEnum):
    """HTML tags for search result highlighting."""
    OPEN = "<mark>"
    CLOSE = "</mark>"


class ScriptField(StrEnum):
    """Computed fields using Elasticsearch scripts."""
    DISTANCE = "_distance"
    SCORE = "_score"
    RANDOM_SCORE = "random_score"