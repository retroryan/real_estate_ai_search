"""Output schema definitions for search pipeline transformations.

These schemas define the structure of documents that will be indexed to Elasticsearch.
They re-export the existing document models from data_pipeline.search_pipeline.models.documents
to provide a clear interface for transformers.

All schemas match the Elasticsearch mappings exactly to ensure proper indexing.
"""

# Re-export document models as output schemas
from data_pipeline.search_pipeline.models.documents import (
    BaseDocument,
    PropertyDocument,
    NeighborhoodDocument,
    WikipediaDocument,
    
    # Nested object models
    AddressModel,
    NeighborhoodModel,
    ParkingModel,
    LandmarkModel,
    LocationContextModel,
    NeighborhoodContextModel,
    NearbyPOIModel,
    LocationScoresModel,
)

# Define aliases for clarity in transformer context
PropertyOutputSchema = PropertyDocument
NeighborhoodOutputSchema = NeighborhoodDocument
WikipediaOutputSchema = WikipediaDocument

__all__ = [
    # Primary document schemas
    "PropertyOutputSchema",
    "NeighborhoodOutputSchema", 
    "WikipediaOutputSchema",
    
    # Base schemas
    "BaseDocument",
    
    # Original document models (for backward compatibility)
    "PropertyDocument",
    "NeighborhoodDocument",
    "WikipediaDocument",
    
    # Nested object models
    "AddressModel",
    "NeighborhoodModel",
    "ParkingModel",
    "LandmarkModel",
    "LocationContextModel",
    "NeighborhoodContextModel",
    "NearbyPOIModel",
    "LocationScoresModel",
]