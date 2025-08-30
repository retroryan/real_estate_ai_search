"""Enriched data models with computed fields and business logic."""

from squack_pipeline_v2.models.enriched.property import EnrichedProperty
from squack_pipeline_v2.models.enriched.neighborhood import EnrichedNeighborhood
from squack_pipeline_v2.models.enriched.wikipedia import EnrichedWikipediaArticle

__all__ = [
    "EnrichedProperty",
    "EnrichedNeighborhood", 
    "EnrichedWikipediaArticle",
]