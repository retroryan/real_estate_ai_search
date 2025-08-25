"""
Statistics response schemas for API endpoints.

Defines Pydantic models for data statistics, coverage metrics, and enrichment analysis.
"""

import time
from typing import Dict, List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class DataSummaryStats(BaseModel):
    """
    Overall data summary statistics.
    
    Provides high-level overview of all data sources and their key metrics.
    """
    
    total_properties: int = Field(ge=0, description="Total number of properties")
    total_neighborhoods: int = Field(ge=0, description="Total number of neighborhoods")
    total_wikipedia_articles: int = Field(ge=0, description="Total number of Wikipedia articles")
    total_wikipedia_summaries: int = Field(ge=0, description="Total number of Wikipedia summaries")
    
    unique_cities: int = Field(ge=0, description="Number of unique cities covered")
    unique_states: int = Field(ge=0, description="Number of unique states covered")
    
    price_range: Dict[str, Decimal] = Field(description="Property price range (min, max, avg)")
    
    timestamp: float = Field(default_factory=time.time, description="Statistics generation timestamp")


class PropertyStats(BaseModel):
    """
    Property-specific statistics and distributions.
    
    Detailed analysis of property data including types, prices, and geographic distribution.
    """
    
    total_count: int = Field(ge=0, description="Total number of properties")
    
    by_type: Dict[str, int] = Field(description="Property count by type")
    by_city: Dict[str, int] = Field(description="Property count by city")
    by_state: Dict[str, int] = Field(description="Property count by state")
    
    price_stats: Dict[str, Decimal] = Field(description="Price statistics (min, max, avg, median)")
    bedroom_stats: Dict[str, float] = Field(description="Bedroom statistics (min, max, avg)")
    
    features_analysis: Dict[str, int] = Field(description="Most common property features")
    amenities_analysis: Dict[str, int] = Field(description="Most common property amenities")
    
    data_completeness: Dict[str, float] = Field(description="Percentage of complete fields")


class NeighborhoodStats(BaseModel):
    """
    Neighborhood-specific statistics and distributions.
    
    Analysis of neighborhood data including geographic distribution and characteristics.
    """
    
    total_count: int = Field(ge=0, description="Total number of neighborhoods")
    
    by_city: Dict[str, int] = Field(description="Neighborhood count by city")
    by_state: Dict[str, int] = Field(description="Neighborhood count by state")
    
    poi_stats: Dict[str, float] = Field(description="POI count statistics (min, max, avg)")
    characteristics_analysis: Dict[str, int] = Field(description="Most common characteristics")
    
    data_completeness: Dict[str, float] = Field(description="Percentage of complete fields")


class WikipediaStats(BaseModel):
    """
    Wikipedia data statistics and quality metrics.
    
    Analysis of Wikipedia articles and summaries including confidence and relevance scores.
    """
    
    total_articles: int = Field(ge=0, description="Total number of Wikipedia articles")
    total_summaries: int = Field(ge=0, description="Total number of Wikipedia summaries")
    
    relevance_distribution: Dict[str, int] = Field(description="Article count by relevance score ranges")
    confidence_distribution: Dict[str, int] = Field(description="Summary count by confidence score ranges")
    
    geographic_coverage: Dict[str, Dict[str, int]] = Field(description="Geographic coverage by state/city")
    
    quality_metrics: Dict[str, float] = Field(description="Average relevance and confidence scores")


class CoverageStats(BaseModel):
    """
    Geographic coverage and data distribution metrics.
    
    Shows how data is distributed across different locations and identifies coverage gaps.
    """
    
    by_city: Dict[str, Dict[str, int]] = Field(description="Data counts by city")
    by_state: Dict[str, Dict[str, int]] = Field(description="Data counts by state")
    
    coverage_summary: Dict[str, int] = Field(description="Summary of geographic coverage")
    
    top_cities_by_data: List[Dict[str, int]] = Field(description="Cities with most data points")


class EnrichmentStats(BaseModel):
    """
    Data enrichment success rates and quality metrics.
    
    Shows how effectively data enrichment processes are working across different data types.
    """
    
    address_enrichment: Dict[str, float] = Field(description="Address expansion success rates")
    feature_normalization: Dict[str, float] = Field(description="Feature normalization success rates")
    coordinate_availability: Dict[str, float] = Field(description="Geographic coordinate availability")
    
    enrichment_success_summary: Dict[str, float] = Field(description="Overall enrichment success rates")


class StatsSummaryResponse(BaseModel):
    """Response model for data summary statistics."""
    
    data: DataSummaryStats = Field(description="Data summary statistics")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Response metadata")


class PropertyStatsResponse(BaseModel):
    """Response model for property statistics."""
    
    data: PropertyStats = Field(description="Property statistics")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Response metadata")


class NeighborhoodStatsResponse(BaseModel):
    """Response model for neighborhood statistics."""
    
    data: NeighborhoodStats = Field(description="Neighborhood statistics")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Response metadata")


class WikipediaStatsResponse(BaseModel):
    """Response model for Wikipedia statistics."""
    
    data: WikipediaStats = Field(description="Wikipedia statistics")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Response metadata")


class CoverageStatsResponse(BaseModel):
    """Response model for coverage statistics."""
    
    data: CoverageStats = Field(description="Coverage statistics")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Response metadata")


class EnrichmentStatsResponse(BaseModel):
    """Response model for enrichment statistics."""
    
    data: EnrichmentStats = Field(description="Enrichment statistics")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Response metadata")