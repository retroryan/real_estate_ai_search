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
from .property_neighborhood_wiki import (
    demo_property_with_full_context,
    demo_neighborhood_properties_and_wiki,
    demo_location_wikipedia_context
)

__all__ = [
    'demo_basic_property_search',
    'demo_property_filter',
    'demo_geo_search',
    'demo_neighborhood_stats',
    'demo_price_distribution',
    'demo_semantic_search',
    'demo_multi_entity_search',
    'demo_wikipedia_search',
    'demo_property_with_full_context',
    'demo_neighborhood_properties_and_wiki',
    'demo_location_wikipedia_context'
]