"""
MCP Server data models.
Pure Pydantic models with no Marshmallow dependencies.
"""

# Property models
from .property import (
    PropertyType,
    GeoLocation,
    Address,
    Property,
    PropertyHit
)

# Search models
from .search import (
    SearchMode,
    SortOrder,
    GeoDistanceUnit,
    PriceRange,
    SearchFilters,
    PropertySearchParams,
    GeoSearchParams,
    SearchResults,
    SimilarPropertiesParams,
    SimilarPropertiesResult
)

# Enrichment models
from .enrichment import (
    POICategory,
    WikipediaContext,
    POIInfo,
    NeighborhoodContext,
    LocationHistory,
    MarketContext,
    EnrichmentBundle
)

# Analysis models
from .analysis import (
    InvestmentGrade,
    MarketPosition,
    InvestmentMetrics,
    ComparableProperty,
    PropertyAnalysis,
    PropertyComparison,
    AffordabilityAnalysis,
    CommuteAnalysis
)

__all__ = [
    # Property
    "PropertyType",
    "GeoLocation",
    "Address",
    "Property",
    "PropertyHit",
    
    # Search
    "SearchMode",
    "SortOrder",
    "GeoDistanceUnit",
    "PriceRange",
    "SearchFilters",
    "PropertySearchParams",
    "GeoSearchParams",
    "SearchResults",
    "SimilarPropertiesParams",
    "SimilarPropertiesResult",
    
    # Enrichment
    "POICategory",
    "WikipediaContext",
    "POIInfo",
    "NeighborhoodContext",
    "LocationHistory",
    "MarketContext",
    "EnrichmentBundle",
    
    # Analysis
    "InvestmentGrade",
    "MarketPosition",
    "InvestmentMetrics",
    "ComparableProperty",
    "PropertyAnalysis",
    "PropertyComparison",
    "AffordabilityAnalysis",
    "CommuteAnalysis"
]