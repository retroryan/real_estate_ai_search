"""
Demo metadata and configuration.

Defines metadata for each demo including display strategy, category,
and other configuration options.
"""

from dataclasses import dataclass, field
from typing import Callable, Type, Dict, Any, Optional
from enum import Enum

from .display_strategies import DisplayStrategy


class DemoCategory(Enum):
    """Categories for organizing demos."""
    BASIC_SEARCH = "basic_search"
    FILTERS = "filters"
    GEO = "geo"
    AGGREGATION = "aggregation"
    WIKIPEDIA = "wikipedia"
    RELATIONSHIPS = "relationships"
    NATURAL_LANGUAGE = "natural_language"
    HYBRID = "hybrid"
    LOCATION_AWARE = "location_aware"
    SHOWCASE = "showcase"


@dataclass
class DemoMetadata:
    """
    Metadata for a demo.
    
    Contains all configuration needed to execute and display a demo,
    following the Single Responsibility Principle.
    """
    number: int
    name: str
    description: str
    category: DemoCategory
    query_function: Callable
    display_strategy_type: str  # Type of display strategy to use
    supports_verbose: bool = True
    handles_own_display: bool = False  # For demos like 1-3 that use PropertyDemoRunner
    special_config: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """String representation for display."""
        return f"Demo {self.number}: {self.name}"
    
    def get_category_emoji(self) -> str:
        """Get an emoji representing the demo category."""
        emoji_map = {
            DemoCategory.BASIC_SEARCH: "🔍",
            DemoCategory.FILTERS: "🎯",
            DemoCategory.GEO: "📍",
            DemoCategory.AGGREGATION: "📊",
            DemoCategory.WIKIPEDIA: "📚",
            DemoCategory.RELATIONSHIPS: "🔗",
            DemoCategory.NATURAL_LANGUAGE: "💬",
            DemoCategory.HYBRID: "🔄",
            DemoCategory.LOCATION_AWARE: "🗺️",
            DemoCategory.SHOWCASE: "✨"
        }
        return emoji_map.get(self.category, "📋")


# Demo registry with metadata
DEMO_METADATA_REGISTRY = {
    1: DemoMetadata(
        number=1,
        name="Basic Search",
        description="Simple property search with text matching",
        category=DemoCategory.BASIC_SEARCH,
        query_function="demo_1",  # Will be resolved to actual function
        display_strategy_type="property",
        handles_own_display=True
    ),
    2: DemoMetadata(
        number=2,
        name="Filter and Sort",
        description="Property search with filters and sorting",
        category=DemoCategory.FILTERS,
        query_function="demo_2",
        display_strategy_type="property",
        handles_own_display=True
    ),
    3: DemoMetadata(
        number=3,
        name="Geo-Distance",
        description="Search properties by distance from a location",
        category=DemoCategory.GEO,
        query_function="demo_3",
        display_strategy_type="property",
        handles_own_display=True
    ),
    4: DemoMetadata(
        number=4,
        name="Multi-Field Search",
        description="Search across multiple property fields",
        category=DemoCategory.BASIC_SEARCH,
        query_function="demo_multi_field_search",
        display_strategy_type="rich"
    ),
    5: DemoMetadata(
        number=5,
        name="Aggregation Query",
        description="Statistical analysis of property data",
        category=DemoCategory.AGGREGATION,
        query_function="demo_aggregation_query",
        display_strategy_type="aggregation"
    ),
    6: DemoMetadata(
        number=6,
        name="Wikipedia Full-Text Search",
        description="Full-text search in Wikipedia articles",
        category=DemoCategory.WIKIPEDIA,
        query_function="run_wikipedia_demo",
        display_strategy_type="wikipedia"
    ),
    7: DemoMetadata(
        number=7,
        name="Property Relationships via Denormalized Index",
        description="Single query for property with all relationships",
        category=DemoCategory.RELATIONSHIPS,
        query_function="demo_single_query_relationships",
        display_strategy_type="rich"
    ),
    8: DemoMetadata(
        number=8,
        name="Natural Language Examples",
        description="Process natural language property queries",
        category=DemoCategory.NATURAL_LANGUAGE,
        query_function="demo_natural_language_examples",
        display_strategy_type="natural_language",
        handles_own_display=True  # Returns list of results
    ),
    9: DemoMetadata(
        number=9,
        name="Rich Real Estate Listing",
        description="Comprehensive property listing with embedded data",
        category=DemoCategory.SHOWCASE,
        query_function="demo_rich_property_listing",
        display_strategy_type="rich"
    ),
    10: DemoMetadata(
        number=10,
        name="Hybrid Search with RRF",
        description="Combined vector and keyword search with reciprocal rank fusion",
        category=DemoCategory.HYBRID,
        query_function="demo_hybrid_search_with_rrf",
        display_strategy_type="rich"
    ),
    11: DemoMetadata(
        number=11,
        name="Location Understanding",
        description="Extract and understand location from natural language",
        category=DemoCategory.LOCATION_AWARE,
        query_function="demo_location_understanding",
        display_strategy_type="location_understanding"
    ),
    12: DemoMetadata(
        number=12,
        name="Location-Aware: Waterfront Luxury",
        description="Find luxury waterfront properties in specific locations",
        category=DemoCategory.LOCATION_AWARE,
        query_function="demo_location_aware_waterfront_luxury",
        display_strategy_type="location"
    ),
    13: DemoMetadata(
        number=13,
        name="Location-Aware: Family Schools",
        description="Find family homes near good schools",
        category=DemoCategory.LOCATION_AWARE,
        query_function="demo_location_aware_family_schools",
        display_strategy_type="location"
    ),
    14: DemoMetadata(
        number=14,
        name="Location-Aware: Recreation Mountain",
        description="Find mountain retreats with recreation access",
        category=DemoCategory.LOCATION_AWARE,
        query_function="demo_location_aware_recreation_mountain",
        display_strategy_type="location"
    ),
    15: DemoMetadata(
        number=15,
        name="Location-Aware Search Showcase",
        description="Multiple location-aware searches in one demo",
        category=DemoCategory.SHOWCASE,
        query_function="demo_location_aware_search_showcase",
        display_strategy_type="location",
        handles_own_display=True  # Returns list of results
    ),
    16: DemoMetadata(
        number=16,
        name="Wikipedia Location Search",
        description="Location-aware Wikipedia article search",
        category=DemoCategory.WIKIPEDIA,
        query_function="demo_wikipedia_location_search",
        display_strategy_type="wikipedia"
    )
}


def get_demo_metadata(demo_number: int) -> Optional[DemoMetadata]:
    """
    Get metadata for a specific demo.
    
    Args:
        demo_number: Demo number to retrieve
        
    Returns:
        DemoMetadata if found, None otherwise
    """
    return DEMO_METADATA_REGISTRY.get(demo_number)


def get_demos_by_category(category: DemoCategory) -> Dict[int, DemoMetadata]:
    """
    Get all demos in a specific category.
    
    Args:
        category: Category to filter by
        
    Returns:
        Dictionary of demo number to metadata for demos in the category
    """
    return {
        num: meta
        for num, meta in DEMO_METADATA_REGISTRY.items()
        if meta.category == category
    }


def list_all_demos() -> Dict[int, DemoMetadata]:
    """
    Get all registered demos.
    
    Returns:
        Dictionary of all demo metadata
    """
    return DEMO_METADATA_REGISTRY.copy()