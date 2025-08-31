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
from .wikipedia_fulltext import demo_wikipedia_fulltext
from .demo_single_query_relationships import demo_simplified_relationships
from .semantic_query_search import (
    demo_natural_language_search,
    demo_natural_language_examples,
    demo_semantic_vs_keyword_comparison
)
from .rich_listing_demo import demo_rich_property_listing

__all__ = [
    'demo_basic_property_search',
    'demo_property_filter',
    'demo_geo_search',
    'demo_neighborhood_stats',
    'demo_price_distribution',
    'demo_semantic_search',
    'demo_multi_entity_search',
    'demo_wikipedia_search',
    'demo_wikipedia_fulltext',
    'demo_simplified_relationships',
    'demo_natural_language_search',
    'demo_natural_language_examples',
    'demo_semantic_vs_keyword_comparison',
    'demo_rich_property_listing'
]