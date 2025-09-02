"""
Example query library for location-aware hybrid search.

This module provides a structured collection of example queries organized by 
search patterns, location types, and property features. All examples use 
Pydantic models for type safety and validation.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class LocationType(str, Enum):
    """Types of location references in queries."""
    CITY = "city"
    STATE = "state" 
    NEIGHBORHOOD = "neighborhood"
    ZIP_CODE = "zip_code"
    REGION = "region"
    PROXIMITY = "proximity"


class PropertyType(str, Enum):
    """Types of properties in queries."""
    CONDO = "condo"
    HOUSE = "house"
    TOWNHOUSE = "townhouse"
    LOFT = "loft"
    APARTMENT = "apartment"
    CABIN = "cabin"
    PENTHOUSE = "penthouse"
    BROWNSTONE = "brownstone"


class SearchCategory(str, Enum):
    """Categories of search patterns."""
    LUXURY = "luxury"
    FAMILY = "family"
    INVESTMENT = "investment"
    RECREATION = "recreation"
    HISTORIC = "historic"
    URBAN = "urban"
    SUBURBAN = "suburban"
    WATERFRONT = "waterfront"
    ARCHITECTURAL = "architectural"


class QueryExample(BaseModel):
    """Single query example with metadata."""
    query: str = Field(..., description="Natural language search query")
    category: SearchCategory = Field(..., description="Search pattern category")
    property_type: Optional[PropertyType] = Field(None, description="Primary property type")
    location_types: List[LocationType] = Field(..., description="Location reference types")
    expected_features: List[str] = Field(..., description="Expected property features to match")
    description: str = Field(..., description="Description of the search pattern")
    complexity: int = Field(..., ge=1, le=5, description="Query complexity level (1-5)")


class QueryLibrary(BaseModel):
    """Complete library of example queries organized by patterns."""
    examples: List[QueryExample] = Field(..., description="All query examples")
    
    def by_category(self, category: SearchCategory) -> List[QueryExample]:
        """Get all examples for a specific category."""
        return [ex for ex in self.examples if ex.category == category]
    
    def by_property_type(self, property_type: PropertyType) -> List[QueryExample]:
        """Get all examples for a specific property type."""
        return [ex for ex in self.examples if ex.property_type == property_type]
    
    def by_location_type(self, location_type: LocationType) -> List[QueryExample]:
        """Get all examples that include a specific location type."""
        return [ex for ex in self.examples if location_type in ex.location_types]
    
    def by_complexity(self, min_complexity: int = 1, max_complexity: int = 5) -> List[QueryExample]:
        """Get examples within a complexity range."""
        return [ex for ex in self.examples 
                if min_complexity <= ex.complexity <= max_complexity]
    
    def simple_queries(self) -> List[QueryExample]:
        """Get simple queries (complexity 1-2)."""
        return self.by_complexity(1, 2)
    
    def complex_queries(self) -> List[QueryExample]:
        """Get complex queries (complexity 4-5)."""
        return self.by_complexity(4, 5)


# Complete example query library
LOCATION_AWARE_QUERY_LIBRARY = QueryLibrary(
    examples=[
        QueryExample(
            query="Luxury waterfront condo in Miami Beach",
            category=SearchCategory.LUXURY,
            property_type=PropertyType.CONDO,
            location_types=[LocationType.CITY],
            expected_features=["waterfront", "luxury", "premium", "ocean"],
            description="City-specific luxury search with waterfront proximity",
            complexity=3
        ),
        QueryExample(
            query="Family home near good schools in Palo Alto California",
            category=SearchCategory.FAMILY,
            property_type=PropertyType.HOUSE,
            location_types=[LocationType.CITY, LocationType.STATE, LocationType.PROXIMITY],
            expected_features=["family", "schools", "residential", "suburban"],
            description="Multi-location family search with proximity requirements",
            complexity=4
        ),
        QueryExample(
            query="Modern apartment downtown Seattle",
            category=SearchCategory.URBAN,
            property_type=PropertyType.APARTMENT,
            location_types=[LocationType.CITY, LocationType.NEIGHBORHOOD],
            expected_features=["modern", "urban", "downtown", "contemporary"],
            description="Neighborhood-level search with architectural style",
            complexity=2
        ),
        QueryExample(
            query="Ski cabin in Park City Utah",
            category=SearchCategory.RECREATION,
            property_type=PropertyType.CABIN,
            location_types=[LocationType.CITY, LocationType.STATE],
            expected_features=["ski", "mountain", "recreation", "vacation"],
            description="Recreation property with city and state targeting",
            complexity=2
        ),
        QueryExample(
            query="Historic brownstone in Brooklyn New York",
            category=SearchCategory.HISTORIC,
            property_type=PropertyType.BROWNSTONE,
            location_types=[LocationType.NEIGHBORHOOD, LocationType.STATE],
            expected_features=["historic", "character", "architecture", "heritage"],
            description="Historic property with neighborhood and state context",
            complexity=3
        ),
        QueryExample(
            query="Beach house walking distance to ocean in Malibu",
            category=SearchCategory.WATERFRONT,
            property_type=PropertyType.HOUSE,
            location_types=[LocationType.CITY, LocationType.PROXIMITY],
            expected_features=["beach", "ocean", "coastal", "proximity"],
            description="Proximity-based waterfront search with distance requirements",
            complexity=4
        ),
        QueryExample(
            query="Investment property in Austin Texas under 500k",
            category=SearchCategory.INVESTMENT,
            property_type=None,
            location_types=[LocationType.CITY, LocationType.STATE],
            expected_features=["investment", "roi", "price", "market"],
            description="Business-focused search with price constraints",
            complexity=3
        ),
        QueryExample(
            query="Penthouse with city views in San Francisco",
            category=SearchCategory.LUXURY,
            property_type=PropertyType.PENTHOUSE,
            location_types=[LocationType.CITY],
            expected_features=["penthouse", "views", "luxury", "premium"],
            description="Luxury urban property with view requirements",
            complexity=2
        ),
        QueryExample(
            query="Ranch style home in suburban Denver Colorado",
            category=SearchCategory.SUBURBAN,
            property_type=PropertyType.HOUSE,
            location_types=[LocationType.CITY, LocationType.STATE],
            expected_features=["ranch", "suburban", "style", "residential"],
            description="Architectural style with area type and full location",
            complexity=3
        ),
        QueryExample(
            query="Loft with exposed brick in SoHo Manhattan",
            category=SearchCategory.ARCHITECTURAL,
            property_type=PropertyType.LOFT,
            location_types=[LocationType.NEIGHBORHOOD],
            expected_features=["loft", "exposed brick", "industrial", "character"],
            description="Architectural details with specific neighborhood targeting",
            complexity=4
        ),
        # Additional examples for variety
        QueryExample(
            query="Affordable condo in Portland",
            category=SearchCategory.URBAN,
            property_type=PropertyType.CONDO,
            location_types=[LocationType.CITY],
            expected_features=["affordable", "budget", "starter"],
            description="Simple city search with budget considerations",
            complexity=1
        ),
        QueryExample(
            query="Townhouse with garage near schools in Plano Texas",
            category=SearchCategory.FAMILY,
            property_type=PropertyType.TOWNHOUSE,
            location_types=[LocationType.CITY, LocationType.STATE, LocationType.PROXIMITY],
            expected_features=["townhouse", "garage", "schools", "family"],
            description="Complex family search with specific amenities and proximity",
            complexity=4
        ),
        QueryExample(
            query="Victorian house in San Francisco Bay Area",
            category=SearchCategory.HISTORIC,
            property_type=PropertyType.HOUSE,
            location_types=[LocationType.REGION],
            expected_features=["Victorian", "historic", "architecture", "character"],
            description="Architectural style search in regional area",
            complexity=3
        ),
        QueryExample(
            query="High-rise apartment with gym in downtown Chicago",
            category=SearchCategory.URBAN,
            property_type=PropertyType.APARTMENT,
            location_types=[LocationType.CITY, LocationType.NEIGHBORHOOD],
            expected_features=["high-rise", "gym", "amenities", "downtown"],
            description="Urban amenity search with specific building type",
            complexity=3
        ),
        QueryExample(
            query="Lakefront property with dock in Lake Tahoe California",
            category=SearchCategory.WATERFRONT,
            property_type=None,
            location_types=[LocationType.REGION, LocationType.STATE],
            expected_features=["lakefront", "dock", "waterfront", "recreation"],
            description="Recreational waterfront with specific amenities",
            complexity=4
        ),
        QueryExample(
            query="Studio apartment under 2000 in Manhattan",
            category=SearchCategory.URBAN,
            property_type=PropertyType.APARTMENT,
            location_types=[LocationType.NEIGHBORHOOD],
            expected_features=["studio", "budget", "small", "urban"],
            description="Budget urban search with size and price constraints",
            complexity=2
        ),
        QueryExample(
            query="Golf course home in Scottsdale Arizona retirement community",
            category=SearchCategory.RECREATION,
            property_type=PropertyType.HOUSE,
            location_types=[LocationType.CITY, LocationType.STATE],
            expected_features=["golf", "retirement", "community", "recreation"],
            description="Lifestyle community search with recreational focus",
            complexity=5
        ),
        QueryExample(
            query="New construction townhome in Austin suburbs",
            category=SearchCategory.SUBURBAN,
            property_type=PropertyType.TOWNHOUSE,
            location_types=[LocationType.CITY],
            expected_features=["new construction", "suburban", "modern", "development"],
            description="New development search in suburban areas",
            complexity=2
        ),
        QueryExample(
            query="Industrial loft with high ceilings in arts district Los Angeles",
            category=SearchCategory.ARCHITECTURAL,
            property_type=PropertyType.LOFT,
            location_types=[LocationType.CITY, LocationType.NEIGHBORHOOD],
            expected_features=["industrial", "high ceilings", "arts", "creative"],
            description="Creative district search with specific architectural features",
            complexity=5
        ),
        QueryExample(
            query="Beachfront condo with ocean views in Santa Monica",
            category=SearchCategory.WATERFRONT,
            property_type=PropertyType.CONDO,
            location_types=[LocationType.CITY],
            expected_features=["beachfront", "ocean views", "coastal", "premium"],
            description="Premium beachfront with view requirements",
            complexity=3
        )
    ]
)


def get_demo_queries_by_pattern() -> Dict[str, List[str]]:
    """
    Get demo queries organized by search patterns for easy access.
    
    Returns:
        Dictionary mapping pattern names to query lists
    """
    library = LOCATION_AWARE_QUERY_LIBRARY
    
    return {
        "luxury": [ex.query for ex in library.by_category(SearchCategory.LUXURY)],
        "family": [ex.query for ex in library.by_category(SearchCategory.FAMILY)],
        "urban": [ex.query for ex in library.by_category(SearchCategory.URBAN)],
        "investment": [ex.query for ex in library.by_category(SearchCategory.INVESTMENT)],
        "waterfront": [ex.query for ex in library.by_category(SearchCategory.WATERFRONT)],
        "historic": [ex.query for ex in library.by_category(SearchCategory.HISTORIC)],
        "recreation": [ex.query for ex in library.by_category(SearchCategory.RECREATION)],
        "architectural": [ex.query for ex in library.by_category(SearchCategory.ARCHITECTURAL)],
        "suburban": [ex.query for ex in library.by_category(SearchCategory.SUBURBAN)],
        "simple": [ex.query for ex in library.simple_queries()],
        "complex": [ex.query for ex in library.complex_queries()]
    }


def get_test_queries(count: int = 10) -> List[str]:
    """
    Get a diverse set of test queries for validation.
    
    Args:
        count: Number of queries to return
        
    Returns:
        List of query strings for testing
    """
    library = LOCATION_AWARE_QUERY_LIBRARY
    
    # Get diverse examples across categories and complexity levels
    queries = []
    
    # Add examples from each category
    for category in SearchCategory:
        category_examples = library.by_category(category)
        if category_examples:
            queries.append(category_examples[0].query)
    
    # Add complexity examples if we need more
    if len(queries) < count:
        remaining = count - len(queries)
        simple_queries = library.simple_queries()
        complex_queries = library.complex_queries()
        
        # Alternate between simple and complex
        for i in range(remaining):
            if i % 2 == 0 and simple_queries:
                queries.append(simple_queries[i // 2].query)
            elif complex_queries:
                queries.append(complex_queries[i // 2].query)
    
    return queries[:count]