"""
Search Service Layer for Real Estate Search.

This module provides a clean service layer for searching properties,
neighborhoods, and Wikipedia articles using Elasticsearch.
"""

from .base import BaseSearchService
from .properties import PropertySearchService
from .wikipedia import WikipediaSearchService
from .neighborhoods import NeighborhoodSearchService
from .models import (
    PropertySearchRequest,
    PropertySearchResponse,
    PropertyFilter,
    PropertyType,
    GeoLocation,
    NeighborhoodSearchRequest,
    NeighborhoodSearchResponse,
    NeighborhoodStatistics,
    RelatedProperty,
    RelatedWikipediaArticle,
    WikipediaSearchRequest,
    WikipediaSearchResponse,
    WikipediaSearchType,
    SearchError
)

__all__ = [
    'BaseSearchService',
    'PropertySearchService',
    'WikipediaSearchService',
    'NeighborhoodSearchService',
    'PropertySearchRequest',
    'PropertySearchResponse',
    'PropertyFilter',
    'PropertyType',
    'GeoLocation',
    'NeighborhoodSearchRequest',
    'NeighborhoodSearchResponse',
    'NeighborhoodStatistics',
    'RelatedProperty',
    'RelatedWikipediaArticle',
    'WikipediaSearchRequest',
    'WikipediaSearchResponse',
    'WikipediaSearchType',
    'SearchError'
]