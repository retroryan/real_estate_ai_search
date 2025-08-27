"""Search pipeline schema definitions module.

This module provides input and output schema definitions for the search pipeline
transformation layer. Schemas ensure type safety and validation during DataFrame
transformations.

Input schemas define the expected structure of DataFrames from the data pipeline.
Output schemas define the target structure for Elasticsearch documents.
"""

from .input_schemas import (
    PropertyInput,
    NeighborhoodInput,
    WikipediaInput,
    
    # Nested input models
    AddressInput,
    CoordinatesInput,
    PropertyDetailsInput,
    PriceHistoryInput,
    NeighborhoodCharacteristicsInput,
    NeighborhoodDemographicsInput,
    WikipediaCorrelationsInput,
)

from .output_schemas import (
    PropertyOutputSchema,
    NeighborhoodOutputSchema,
    WikipediaOutputSchema,
    
    # Base and nested models
    BaseDocument,
    AddressModel,
    NeighborhoodModel,
    ParkingModel,
    LandmarkModel,
    LocationContextModel,
    NeighborhoodContextModel,
    NearbyPOIModel,
    LocationScoresModel,
)

__all__ = [
    # Input schemas
    "PropertyInput",
    "NeighborhoodInput", 
    "WikipediaInput",
    
    # Output schemas
    "PropertyOutputSchema",
    "NeighborhoodOutputSchema",
    "WikipediaOutputSchema",
    
    # Base models
    "BaseDocument",
    
    # Nested input models
    "AddressInput",
    "CoordinatesInput",
    "PropertyDetailsInput",
    "PriceHistoryInput",
    "NeighborhoodCharacteristicsInput",
    "NeighborhoodDemographicsInput", 
    "WikipediaCorrelationsInput",
    
    # Nested output models
    "AddressModel",
    "NeighborhoodModel",
    "ParkingModel",
    "LandmarkModel",
    "LocationContextModel",
    "NeighborhoodContextModel",
    "NearbyPOIModel",
    "LocationScoresModel",
]