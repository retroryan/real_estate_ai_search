"""Data loading modules for SQUACK pipeline."""

from squack_pipeline.loaders.base import BaseLoader
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.loaders.property_loader import PropertyLoader

__all__ = [
    "BaseLoader",
    "DuckDBConnectionManager", 
    "PropertyLoader",
]