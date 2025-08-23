"""
Data loaders for the common embeddings module.

Handles loading documents from various data sources with proper metadata.
"""

from .real_estate_loader import RealEstateLoader
from .wikipedia_loader import WikipediaLoader

__all__ = [
    "RealEstateLoader",
    "WikipediaLoader",
]