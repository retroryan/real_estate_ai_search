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
    LocationScores,
    POICategory
)

__all__ = [
    'WikipediaArticle',
    'WikipediaLocation',
    'WikipediaPOI',
    'POICategory',
    'LocationContext',
    'NeighborhoodContext',
    'LocationScores'
]