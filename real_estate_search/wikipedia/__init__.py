"""
Wikipedia data integration for real estate search.
Enriches property listings with Wikipedia location context.
"""

from .models import (
    WikipediaArticle,
    WikipediaLocation,
    WikipediaPOI,
    LocationContext,
    NeighborhoodContext,
    LocationScores
)
from .extractor import WikipediaExtractor
from .enricher import PropertyEnricher

__all__ = [
    'WikipediaArticle',
    'WikipediaLocation',
    'WikipediaPOI',
    'LocationContext',
    'NeighborhoodContext',
    'LocationScores',
    'WikipediaExtractor',
    'PropertyEnricher'
]