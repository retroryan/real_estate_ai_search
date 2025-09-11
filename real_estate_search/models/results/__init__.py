"""
Result models.

Models for search results without display logic.
Display formatting should be handled by separate display services.
"""

from .base import BaseQueryResult
from .property import PropertySearchResult
from .wikipedia import WikipediaSearchResult
from .aggregation import AggregationBucket, AggregationSearchResult
from .mixed import MixedEntityResult
from .location import LocationUnderstandingResult

__all__ = [
    "BaseQueryResult",
    "PropertySearchResult",
    "WikipediaSearchResult",
    "AggregationBucket",
    "AggregationSearchResult",
    "MixedEntityResult",
    "LocationUnderstandingResult"
]