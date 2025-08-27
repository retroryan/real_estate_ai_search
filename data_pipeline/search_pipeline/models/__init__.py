"""
Search pipeline models package.

Provides Pydantic models for search pipeline configuration and data structures.
"""

from data_pipeline.search_pipeline.models.config import (
    ElasticsearchConfig,
    SearchPipelineConfig,
    BulkWriteConfig,
)
from data_pipeline.search_pipeline.models.results import (
    SearchIndexResult,
    SearchPipelineResult,
)
from data_pipeline.search_pipeline.models.documents import (
    BaseDocument,
    PropertyDocument,
    NeighborhoodDocument,
    WikipediaDocument,
    AddressModel,
    NeighborhoodModel,
    ParkingModel,
    LocationContextModel,
    NeighborhoodContextModel,
    NearbyPOIModel,
    LocationScoresModel,
    LandmarkModel,
)

__all__ = [
    "ElasticsearchConfig",
    "SearchPipelineConfig",
    "BulkWriteConfig",
    "SearchIndexResult",
    "SearchPipelineResult",
    "BaseDocument",
    "PropertyDocument",
    "NeighborhoodDocument",
    "WikipediaDocument",
    "AddressModel",
    "NeighborhoodModel",
    "ParkingModel",
    "LocationContextModel",
    "NeighborhoodContextModel",
    "NearbyPOIModel",
    "LocationScoresModel",
    "LandmarkModel",
]