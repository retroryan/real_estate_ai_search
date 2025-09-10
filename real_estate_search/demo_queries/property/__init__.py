"""
Property search module with clean separation of concerns.
"""

from .query_builder import PropertyQueryBuilder
from .search_executor import PropertySearchExecutor
from .models import PropertySearchResult
# PropertyDisplayService removed - using result model display methods
from .demo_runner import (
    PropertyDemoRunner,
    demo_basic_property_search,
    demo_filtered_property_search,
    demo_geo_distance_search,
    demo_price_range_search
)

# Aliases for commonly used functions
demo_property_filter = demo_filtered_property_search
demo_geo_search = demo_geo_distance_search

__all__ = [
    # Core classes
    'PropertyQueryBuilder',
    'PropertySearchExecutor',
    'PropertyDemoRunner',
    'PropertySearchResult',
    
    # Demo functions
    'demo_basic_property_search',
    'demo_filtered_property_search',
    'demo_geo_distance_search',
    'demo_price_range_search',
    
    # Aliases
    'demo_property_filter',
    'demo_geo_search',
]