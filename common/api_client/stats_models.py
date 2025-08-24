"""Statistics API models."""

from typing import Dict, Any, Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class DataSummaryStats(BaseModel):
    """Overall data summary statistics."""
    total_properties: int
    total_neighborhoods: int
    total_wikipedia_articles: int
    total_wikipedia_summaries: int
    unique_cities: int
    unique_states: int
    price_range: Dict[str, Decimal]


class PropertyStats(BaseModel):
    """Property statistics and distributions."""
    total_count: int
    by_type: Dict[str, int]
    by_city: Dict[str, int]
    by_state: Dict[str, int]
    price_stats: Dict[str, Decimal]
    bedroom_stats: Dict[str, float]
    features_analysis: Dict[str, int]
    amenities_analysis: Dict[str, int]
    data_completeness: Dict[str, float]


class NeighborhoodStats(BaseModel):
    """Neighborhood statistics and distributions."""
    total_count: int
    by_city: Dict[str, int]
    by_state: Dict[str, int]
    poi_stats: Dict[str, float]
    characteristics_analysis: Dict[str, int]
    data_completeness: Dict[str, float]


class WikipediaStats(BaseModel):
    """Wikipedia data statistics and quality metrics."""
    total_articles: int
    total_summaries: int
    relevance_distribution: Dict[str, int]
    confidence_distribution: Dict[str, int]
    geographic_coverage: Dict[str, Dict[str, int]]
    quality_metrics: Dict[str, float]


class CoverageStats(BaseModel):
    """Geographic coverage and data distribution metrics."""
    by_city: Dict[str, Dict[str, int]]
    by_state: Dict[str, Dict[str, int]]
    coverage_summary: Dict[str, int]
    top_cities_by_data: list


class EnrichmentStats(BaseModel):
    """Data enrichment success rates and quality metrics."""
    address_enrichment: Dict[str, float]
    feature_normalization: Dict[str, float]
    coordinate_availability: Dict[str, float]
    enrichment_success_summary: Dict[str, float]


class StatsResponse(BaseModel):
    """Base response model for statistics endpoints."""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StatsSummaryResponse(StatsResponse):
    """Response model for summary statistics."""
    data: DataSummaryStats


class PropertyStatsResponse(StatsResponse):
    """Response model for property statistics."""
    data: PropertyStats


class NeighborhoodStatsResponse(StatsResponse):
    """Response model for neighborhood statistics."""
    data: NeighborhoodStats


class WikipediaStatsResponse(StatsResponse):
    """Response model for Wikipedia statistics."""
    data: WikipediaStats


class CoverageStatsResponse(StatsResponse):
    """Response model for coverage statistics."""
    data: CoverageStats


class EnrichmentStatsResponse(StatsResponse):
    """Response model for enrichment statistics."""
    data: EnrichmentStats