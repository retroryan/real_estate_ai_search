"""Statistics API Client Implementation."""

import logging
from typing import Dict, Any

from .base import BaseAPIClient
from .config import APIClientConfig
from .exceptions import APIError
from .stats_models import (
    DataSummaryStats,
    PropertyStats,
    NeighborhoodStats,
    WikipediaStats,
    CoverageStats,
    EnrichmentStats,
    StatsSummaryResponse,
    PropertyStatsResponse,
    NeighborhoodStatsResponse,
    WikipediaStatsResponse,
    CoverageStatsResponse,
    EnrichmentStatsResponse
)


class StatsAPIClient(BaseAPIClient):
    """API client for statistics and metrics data."""
    
    def __init__(self, config: APIClientConfig, logger: logging.Logger):
        """Initialize the Statistics API client.
        
        Args:
            config: API client configuration
            logger: Logger instance for structured logging
        """
        super().__init__(config, logger)
        self.logger.info(
            "Initialized Statistics API client",
            extra={"base_url": str(config.base_url)}
        )
    
    def get_summary_stats(self) -> DataSummaryStats:
        """Get overall data summary statistics.
        
        Provides high-level overview of all data sources including counts,
        geographic coverage, and key metrics across properties, neighborhoods,
        and Wikipedia content.
        
        Returns:
            Data summary statistics
            
        Raises:
            APIError: If request fails
        """
        self.logger.debug("Fetching summary statistics")
        
        # Make request
        response_data = self.get("stats/summary")
        
        # Validate and parse response
        response = StatsSummaryResponse(**response_data)
        
        self.logger.info(
            "Retrieved summary statistics",
            extra={
                "total_properties": response.data.total_properties,
                "total_neighborhoods": response.data.total_neighborhoods,
                "unique_cities": response.data.unique_cities
            }
        )
        
        return response.data
    
    def get_property_stats(self) -> PropertyStats:
        """Get detailed property statistics and distributions.
        
        Provides comprehensive analysis of property data including type distributions,
        price statistics, geographic breakdown, and feature analysis.
        
        Returns:
            Property statistics
            
        Raises:
            APIError: If request fails
        """
        self.logger.debug("Fetching property statistics")
        
        # Make request
        response_data = self.get("stats/properties")
        
        # Validate and parse response
        response = PropertyStatsResponse(**response_data)
        
        self.logger.info(
            "Retrieved property statistics",
            extra={"total_count": response.data.total_count}
        )
        
        return response.data
    
    def get_neighborhood_stats(self) -> NeighborhoodStats:
        """Get detailed neighborhood statistics and distributions.
        
        Provides comprehensive analysis of neighborhood data including geographic
        distribution, POI statistics, and characteristic analysis.
        
        Returns:
            Neighborhood statistics
            
        Raises:
            APIError: If request fails
        """
        self.logger.debug("Fetching neighborhood statistics")
        
        # Make request
        response_data = self.get("stats/neighborhoods")
        
        # Validate and parse response
        response = NeighborhoodStatsResponse(**response_data)
        
        self.logger.info(
            "Retrieved neighborhood statistics",
            extra={"total_count": response.data.total_count}
        )
        
        return response.data
    
    def get_wikipedia_stats(self) -> WikipediaStats:
        """Get detailed Wikipedia data statistics and quality metrics.
        
        Provides analysis of Wikipedia articles and summaries including confidence
        distributions, relevance scores, and geographic coverage.
        
        Returns:
            Wikipedia statistics
            
        Raises:
            APIError: If request fails
        """
        self.logger.debug("Fetching Wikipedia statistics")
        
        # Make request
        response_data = self.get("stats/wikipedia")
        
        # Validate and parse response
        response = WikipediaStatsResponse(**response_data)
        
        self.logger.info(
            "Retrieved Wikipedia statistics",
            extra={
                "total_articles": response.data.total_articles,
                "total_summaries": response.data.total_summaries
            }
        )
        
        return response.data
    
    def get_coverage_stats(self) -> CoverageStats:
        """Get geographic coverage and data distribution metrics.
        
        Shows how data is distributed across different locations and identifies
        the most data-rich cities and states.
        
        Returns:
            Coverage statistics
            
        Raises:
            APIError: If request fails
        """
        self.logger.debug("Fetching coverage statistics")
        
        # Make request
        response_data = self.get("stats/coverage")
        
        # Validate and parse response
        response = CoverageStatsResponse(**response_data)
        
        self.logger.info(
            "Retrieved coverage statistics",
            extra={
                "total_cities": response.data.coverage_summary.get("total_cities", 0),
                "total_states": response.data.coverage_summary.get("total_states", 0)
            }
        )
        
        return response.data
    
    def get_enrichment_stats(self) -> EnrichmentStats:
        """Get data enrichment success rates and quality metrics.
        
        Shows how effectively data enrichment processes are working including
        address expansion, feature normalization, and coordinate availability.
        
        Returns:
            Enrichment statistics
            
        Raises:
            APIError: If request fails
        """
        self.logger.debug("Fetching enrichment statistics")
        
        # Make request
        response_data = self.get("stats/enrichment")
        
        # Validate and parse response
        response = EnrichmentStatsResponse(**response_data)
        
        self.logger.info(
            "Retrieved enrichment statistics",
            extra={
                "overall_address_success": response.data.enrichment_success_summary.get(
                    "overall_address_success", 0
                ),
                "overall_feature_success": response.data.enrichment_success_summary.get(
                    "overall_feature_success", 0
                )
            }
        )
        
        return response.data
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get all available statistics in a single call.
        
        Convenience method that fetches all statistics endpoints and returns
        them in a single dictionary.
        
        Returns:
            Dictionary containing all statistics:
            - summary: Overall data summary
            - properties: Property statistics
            - neighborhoods: Neighborhood statistics
            - wikipedia: Wikipedia statistics
            - coverage: Coverage statistics
            - enrichment: Enrichment statistics
            
        Raises:
            APIError: If any request fails
        """
        self.logger.info("Fetching all statistics")
        
        all_stats = {}
        
        # Fetch each type of statistics
        try:
            all_stats["summary"] = self.get_summary_stats()
        except Exception as e:
            self.logger.warning(f"Failed to fetch summary stats: {e}")
            all_stats["summary"] = None
        
        try:
            all_stats["properties"] = self.get_property_stats()
        except Exception as e:
            self.logger.warning(f"Failed to fetch property stats: {e}")
            all_stats["properties"] = None
        
        try:
            all_stats["neighborhoods"] = self.get_neighborhood_stats()
        except Exception as e:
            self.logger.warning(f"Failed to fetch neighborhood stats: {e}")
            all_stats["neighborhoods"] = None
        
        try:
            all_stats["wikipedia"] = self.get_wikipedia_stats()
        except Exception as e:
            self.logger.warning(f"Failed to fetch Wikipedia stats: {e}")
            all_stats["wikipedia"] = None
        
        try:
            all_stats["coverage"] = self.get_coverage_stats()
        except Exception as e:
            self.logger.warning(f"Failed to fetch coverage stats: {e}")
            all_stats["coverage"] = None
        
        try:
            all_stats["enrichment"] = self.get_enrichment_stats()
        except Exception as e:
            self.logger.warning(f"Failed to fetch enrichment stats: {e}")
            all_stats["enrichment"] = None
        
        # Count successful fetches
        successful_fetches = sum(1 for v in all_stats.values() if v is not None)
        
        self.logger.info(
            f"Retrieved {successful_fetches}/6 statistics categories",
            extra={"successful": successful_fetches, "total": 6}
        )
        
        return all_stats