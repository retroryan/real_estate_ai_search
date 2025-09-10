"""
Configuration constants for semantic search functionality.

All configuration values and constants used across the semantic search modules.
"""

from typing import List, Tuple, Dict


# Search configuration
DEFAULT_QUERY: str = "modern home with mountain views and open floor plan"
DEFAULT_SIZE: int = 10
KNN_NUM_CANDIDATES_MULTIPLIER: int = 10
MAX_DISPLAY_RESULTS: int = 10
TOP_MATCH_DISPLAY_COUNT: int = 3

# Property fields to retrieve
PROPERTY_FIELDS: List[str] = [
    "listing_id", "property_type", "price", "bedrooms", "bathrooms",
    "square_feet", "address", "description", "features", "year_built"
]

BASIC_PROPERTY_FIELDS: List[str] = [
    "listing_id", "property_type", "price", "bedrooms", "bathrooms",
    "square_feet", "address", "description"
]

# Example queries for demo
EXAMPLE_QUERIES: List[Tuple[str, str]] = [
    ("cozy family home near good schools and parks", "Family-oriented home search"),
    ("modern downtown condo with city views", "Urban condo search"),
    ("spacious property with home office and fast internet", "Work-from-home property search"),
    ("eco-friendly house with solar panels and energy efficiency", "Sustainable home search"),
    ("luxury estate with pool and entertainment areas", "Luxury property search")
]

# Match explanations for example queries
MATCH_EXPLANATIONS: Dict[int, str] = {
    1: "AI understands 'family' context - properties with multiple bedrooms, residential neighborhoods, space for children",
    2: "Semantic search identifies urban/city characteristics - downtown locations, modern architecture, high-rise features", 
    3: "AI recognizes work-from-home needs - spacious properties, dedicated office spaces, quiet environments",
    4: "Embeddings understand sustainability concepts - energy-efficient features, eco-friendly materials, green amenities",
    5: "Semantic search finds luxury indicators - high-end finishes, premium amenities, entertainment features"
}