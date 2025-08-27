"""Demo queries for Real Estate Search application."""

from .property_queries import (
    demo_basic_property_search,
    demo_property_filter,
    demo_geo_search
)
from .aggregation_queries import (
    demo_neighborhood_stats,
    demo_price_distribution
)
from .advanced_queries import (
    demo_semantic_search,
    demo_multi_entity_search,
    demo_wikipedia_search
)

__all__ = [
    'demo_basic_property_search',
    'demo_property_filter',
    'demo_geo_search',
    'demo_neighborhood_stats',
    'demo_price_distribution',
    'demo_semantic_search',
    'demo_multi_entity_search',
    'demo_wikipedia_search'
]