"""Demo queries for Real Estate Search application."""

from .property import (
    demo_basic_property_search,
    demo_property_filter,
    demo_geo_search
)
from .aggregation_queries import (
    demo_neighborhood_stats,
    demo_price_distribution
)
# Advanced demos removed - demos 6, 7, 8 deleted
from .wikipedia import WikipediaDemoRunner
from .wikipedia_location_search import demo_wikipedia_location_search
from .demo_single_query_relationships import demo_simplified_relationships
from .semantic_query_search import (
    demo_natural_language_examples
)
from .rich_listing_demo import demo_rich_property_listing
from .hybrid_search import demo_hybrid_search
from .location_understanding import demo_location_understanding
from .location_aware_demos import (
    demo_location_aware_waterfront_luxury,
    demo_location_aware_family_schools,
    demo_location_aware_recreation_mountain,
    demo_location_aware_search_showcase
)

__all__ = [
    'demo_basic_property_search',
    'demo_property_filter',
    'demo_geo_search',
    'demo_neighborhood_stats',
    'demo_price_distribution',
    'WikipediaDemoRunner',
    'demo_wikipedia_location_search',
    'demo_simplified_relationships',
    'demo_natural_language_examples',
    'demo_rich_property_listing',
    'demo_hybrid_search',
    'demo_location_understanding',
    'demo_location_aware_waterfront_luxury',
    'demo_location_aware_family_schools',
    'demo_location_aware_recreation_mountain',
    'demo_location_aware_search_showcase'
]