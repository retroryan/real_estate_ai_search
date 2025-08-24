"""
Entity-specific schemas using Pydantic for type safety.
"""

from .entity_schemas import (
    PropertySchema,
    NeighborhoodSchema, 
    WikipediaArticleSchema,
)
from .location_schema import LocationSchema, get_location_spark_schema

__all__ = [
    "PropertySchema",
    "NeighborhoodSchema",
    "WikipediaArticleSchema", 
    "LocationSchema",
    "get_location_spark_schema",
]