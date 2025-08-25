"""Data source implementations for dependency injection"""

from .property_source import PropertyFileDataSource
from .wikipedia_source import WikipediaFileDataSource
from .geographic_source import GeographicFileDataSource

__all__ = [
    "PropertyFileDataSource",
    "WikipediaFileDataSource",
    "GeographicFileDataSource",
]