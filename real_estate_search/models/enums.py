"""
Consolidated enumerations for all models.

Single source of truth for all enums used throughout the application.
This module consolidates enums from property models, search models,
and demo queries into one location.
"""

from enum import Enum


class PropertyType(str, Enum):
    """Types of real estate properties."""
    SINGLE_FAMILY = "single-family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    MULTI_FAMILY = "multi-family"
    APARTMENT = "apartment"
    LAND = "land"
    OTHER = "other"
    
    @classmethod
    def _missing_(cls, value):
        """Handle case variations and unknown values."""
        if value:
            # Try case-insensitive match with hyphen variations
            value_lower = str(value).lower().replace("_", "-").replace(" ", "-")
            for member in cls:
                if member.value.lower() == value_lower:
                    return member
            # Handle common aliases
            aliases = {
                "single family": cls.SINGLE_FAMILY,
                "single_family": cls.SINGLE_FAMILY,
                "town-house": cls.TOWNHOUSE,
                "town_house": cls.TOWNHOUSE,
                "townhome": cls.TOWNHOUSE,
                "multi family": cls.MULTI_FAMILY,
                "multi_family": cls.MULTI_FAMILY,
                "multifamily": cls.MULTI_FAMILY,
            }
            if value_lower in aliases:
                return aliases[value_lower]
        # Default to OTHER for unknown types
        return cls.OTHER


class PropertyStatus(str, Enum):
    """Property listing status."""
    ACTIVE = "active"
    PENDING = "pending"
    SOLD = "sold"
    OFF_MARKET = "off_market"
    COMING_SOON = "coming_soon"


class ParkingType(str, Enum):
    """Types of parking."""
    GARAGE = "garage"
    SINGLE_GARAGE = "single_garage"
    MULTI_CAR_GARAGE = "multi_car_garage"
    CARPORT = "carport"
    DRIVEWAY = "driveway"
    STREET = "street"
    COVERED = "covered"
    UNCOVERED = "uncovered"
    NONE = "none"
    
    @classmethod
    def _missing_(cls, value):
        """Handle case variations and unknown values."""
        if value:
            # Try case-insensitive match with underscore/hyphen variations
            value_lower = str(value).lower()
            for member in cls:
                if member.value.lower() == value_lower:
                    return member
            # Handle common aliases
            aliases = {
                "single-garage": cls.SINGLE_GARAGE,
                "multi-car-garage": cls.MULTI_CAR_GARAGE,
                "multi_car_garage": cls.MULTI_CAR_GARAGE,
                "2-car-garage": cls.MULTI_CAR_GARAGE,
                "3-car-garage": cls.MULTI_CAR_GARAGE,
                "attached-garage": cls.GARAGE,
                "detached-garage": cls.GARAGE,
            }
            if value_lower in aliases:
                return aliases[value_lower]
        # Default to NONE for unknown types
        return cls.NONE


class IndexName(str, Enum):
    """Elasticsearch index names used in the system."""
    PROPERTIES = "properties"
    NEIGHBORHOODS = "neighborhoods"
    WIKIPEDIA = "wikipedia"
    PROPERTY_RELATIONSHIPS = "property_relationships"


class EntityType(str, Enum):
    """Types of entities in the search system."""
    PROPERTY = "property"
    NEIGHBORHOOD = "neighborhood"
    WIKIPEDIA = "wikipedia"


class QueryType(str, Enum):
    """Types of Elasticsearch queries used in demos."""
    MATCH = "match"
    TERM = "term"
    RANGE = "range"
    BOOL = "bool"
    FUNCTION_SCORE = "function_score"
    GEO_DISTANCE = "geo_distance"
    KNN = "knn"
    MULTI_MATCH = "multi_match"
    MATCH_PHRASE = "match_phrase"
    NESTED = "nested"
    EXISTS = "exists"
    PREFIX = "prefix"
    WILDCARD = "wildcard"
    FUZZY = "fuzzy"


class AggregationType(str, Enum):
    """Types of Elasticsearch aggregations."""
    TERMS = "terms"
    AVG = "avg"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    STATS = "stats"
    EXTENDED_STATS = "extended_stats"
    HISTOGRAM = "histogram"
    DATE_HISTOGRAM = "date_histogram"
    RANGE = "range"
    GEO_BOUNDS = "geo_bounds"
    GEO_CENTROID = "geo_centroid"
    CARDINALITY = "cardinality"
    PERCENTILES = "percentiles"