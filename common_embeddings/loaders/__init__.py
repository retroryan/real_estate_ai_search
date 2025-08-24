"""
Data loaders for the common embeddings module.

Handles loading documents from various data sources with proper metadata.
Includes LlamaIndex-optimized loaders following best practices.
"""

from .real_estate_loader import RealEstateLoader
from .wikipedia_loader import WikipediaLoader
from .optimized_loader import OptimizedDocumentLoader

__all__ = [
    "RealEstateLoader",
    "WikipediaLoader",
    "OptimizedDocumentLoader",
]