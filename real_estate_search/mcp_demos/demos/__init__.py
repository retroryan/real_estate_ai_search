"""MCP Demo scripts for Real Estate Search."""

# Import demo functions for easy access
from .property_search import (
    demo_basic_property_search,
    demo_property_filter
)

from .wikipedia_search import (
    demo_wikipedia_search,
    demo_wikipedia_location_context
)

from .location_discovery import demo_location_based_discovery
from .multi_entity import demo_multi_entity_search
from .property_details import demo_property_details_deep_dive
from .search_comparison import demo_semantic_vs_text_comparison

__all__ = [
    'demo_basic_property_search',
    'demo_property_filter',
    'demo_wikipedia_search',
    'demo_wikipedia_location_context',
    'demo_location_based_discovery',
    'demo_multi_entity_search',
    'demo_property_details_deep_dive',
    'demo_semantic_vs_text_comparison'
]