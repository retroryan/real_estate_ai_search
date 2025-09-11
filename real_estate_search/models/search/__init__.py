"""
Search models.

Consolidated models for Elasticsearch search operations.
"""

from .base import SearchHit, SourceFilter, SearchRequest, SearchResponse
from .queries import (
    QueryClause, BoolQuery, MatchQuery, MultiMatchQuery, 
    RangeQuery, TermQuery
)
from .filters import (
    BucketAggregation, StatsAggregation, AggregationResult,
    AggregationClause, FilterClause, SortClause
)
from .params import (
    PropertySearchParams, PropertyFilterParams, NeighborhoodSearchParams,
    WikipediaSearchParams, SemanticSearchParams, HybridSearchParams,
    AggregationParams, MultiEntitySearchParams
)

__all__ = [
    # Base
    "SearchHit", "SourceFilter", "SearchRequest", "SearchResponse",
    # Queries
    "QueryClause", "BoolQuery", "MatchQuery", "MultiMatchQuery",
    "RangeQuery", "TermQuery",
    # Filters
    "BucketAggregation", "StatsAggregation", "AggregationResult",
    "AggregationClause", "FilterClause", "SortClause",
    # Params
    "PropertySearchParams", "PropertyFilterParams", "NeighborhoodSearchParams",
    "WikipediaSearchParams", "SemanticSearchParams", "HybridSearchParams",
    "AggregationParams", "MultiEntitySearchParams"
]