"""
Entity-specific enrichment modules.

Provides base and specialized enrichers for properties, neighborhoods,
and Wikipedia articles with consistent patterns for data enhancement.
"""

from .base_enricher import BaseEnricher
from .location_enricher import LocationEnricher, LocationEnrichmentConfig
from .neighborhood_enricher import NeighborhoodEnricher  
from .property_enricher import PropertyEnricher, PropertyEnrichmentConfig
from .relationship_builder import RelationshipBuilder, RelationshipBuilderConfig
from .wikipedia_enricher import WikipediaEnricher, WikipediaEnrichmentConfig

__all__ = [
    "BaseEnricher",
    "LocationEnricher",
    "LocationEnrichmentConfig",
    "NeighborhoodEnricher",
    "PropertyEnricher",
    "PropertyEnrichmentConfig",
    "RelationshipBuilder",
    "RelationshipBuilderConfig",
    "WikipediaEnricher",
    "WikipediaEnrichmentConfig",
]