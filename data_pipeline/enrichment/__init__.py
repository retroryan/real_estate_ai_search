"""
Entity-specific enrichment modules.

Provides base and specialized enrichers for properties, neighborhoods,
and Wikipedia articles with consistent patterns for data enhancement.
"""

from .base_enricher import BaseEnricher
from .location_enricher import LocationEnricher
from .neighborhood_enricher import NeighborhoodEnricher  
from .property_enricher import PropertyEnricher
from .wikipedia_enricher import WikipediaEnricher
from .wikipedia_integration import WikipediaEnrichmentBuilder

__all__ = [
    "BaseEnricher",
    "LocationEnricher",
    "NeighborhoodEnricher",
    "PropertyEnricher",
    "WikipediaEnricher",
    "WikipediaEnrichmentBuilder",
]