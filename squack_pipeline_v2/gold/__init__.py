"""Gold layer - Data enrichment."""

from squack_pipeline_v2.gold.base import GoldEnricher
from squack_pipeline_v2.gold.location import LocationGoldEnricher

__all__ = ["GoldEnricher", "LocationGoldEnricher"]