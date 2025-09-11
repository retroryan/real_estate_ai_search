"""
Unified models for the real estate search application.

This module provides the single source of truth for all data structures
throughout the application.
"""

# Core domain models
from .address import Address
from .property import PropertyListing, Parking
from .wikipedia import WikipediaArticle
from .neighborhood import Neighborhood, Demographics, SchoolRatings

# Enumerations
from .enums import (
    PropertyType, PropertyStatus, ParkingType,
    IndexName, EntityType, QueryType, AggregationType
)

# Geographic models
from .geo import GeoPoint, Distance, BoundingBox, GeoSearchParams

# Search models
from .search import (
    SearchHit, SourceFilter, SearchRequest, SearchResponse,
    QueryClause, BoolQuery, MatchQuery, MultiMatchQuery, RangeQuery, TermQuery,
    BucketAggregation, StatsAggregation, AggregationResult,
    AggregationClause, FilterClause, SortClause,
    PropertySearchParams, PropertyFilterParams, NeighborhoodSearchParams,
    WikipediaSearchParams, SemanticSearchParams, HybridSearchParams,
    AggregationParams, MultiEntitySearchParams
)

# Result models
from .results import (
    BaseQueryResult, PropertySearchResult, WikipediaSearchResult,
    AggregationBucket, AggregationSearchResult, MixedEntityResult
)

__all__ = [
    # Core domain
    "Address",
    "PropertyListing",
    "Parking",
    "WikipediaArticle",
    "Neighborhood",
    "Demographics",
    "SchoolRatings",
    # Enums
    "PropertyType",
    "PropertyStatus",
    "ParkingType",
    "IndexName",
    "EntityType",
    "QueryType",
    "AggregationType",
    # Geographic
    "GeoPoint",
    "Distance",
    "BoundingBox",
    "GeoSearchParams",
    # Search
    "SearchHit",
    "SourceFilter",
    "SearchRequest",
    "SearchResponse",
    "QueryClause",
    "BoolQuery",
    "MatchQuery",
    "MultiMatchQuery",
    "RangeQuery",
    "TermQuery",
    "BucketAggregation",
    "StatsAggregation",
    "AggregationResult",
    "AggregationClause",
    "FilterClause",
    "SortClause",
    "PropertySearchParams",
    "PropertyFilterParams",
    "NeighborhoodSearchParams",
    "WikipediaSearchParams",
    "SemanticSearchParams",
    "HybridSearchParams",
    "AggregationParams",
    "MultiEntitySearchParams",
    # Results
    "BaseQueryResult",
    "PropertySearchResult",
    "WikipediaSearchResult",
    "AggregationBucket",
    "AggregationSearchResult",
    "MixedEntityResult"
]