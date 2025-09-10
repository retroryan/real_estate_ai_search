"""
Demo orchestration for property searches.

This module coordinates query building, search execution, and display
for property search demos. It provides the main entry points for
running various demo scenarios.
"""

from typing import Optional, List
from elasticsearch import Elasticsearch
import logging

from .query_builder import PropertyQueryBuilder
from .search_executor import PropertySearchExecutor
from .display_service import PropertyDisplayService
from .models import PropertySearchResult
from ..result_models import AggregationSearchResult
from ..display_formatter import PropertyDisplayFormatter

logger = logging.getLogger(__name__)


class PropertyDemoRunner:
    """
    Orchestrates property search demos.
    
    Coordinates between query building, search execution, and display
    to provide complete demo workflows.
    """
    
    def __init__(self, es_client: Elasticsearch):
        self.es_client = es_client
        self.executor = PropertySearchExecutor(es_client=self.es_client)
        self.display_service = PropertyDisplayService()
    
    def run_basic_search(
        self,
        query_text: str = "modern home with pool"
    ) -> PropertySearchResult:
        """
        Run a basic property search demo.
        
        Args:
            query_text: Text to search for
            
        Returns:
            PropertySearchResult with search results
        """
        # Display search criteria
        self.display_service.display_search_criteria(
            title="🔍 Basic Property Search",
            criteria={"query": query_text}
        )
        
        # Build query
        request = PropertyQueryBuilder.basic_search(query_text)
        
        # Execute search
        result = self.executor.execute_basic_search(request, query_text)
        
        # Display results
        self.display_service.display_basic_search_results(result)
        
        return result
    
    def run_filtered_search(
        self,
        property_type: str = "single-family",
        min_price: float = 300000,
        max_price: float = 800000,
        min_bedrooms: int = 3,
        min_bathrooms: float = 2.0
    ) -> PropertySearchResult:
        """
        Run a filtered property search demo.
        
        Args:
            property_type: Type of property
            min_price: Minimum price
            max_price: Maximum price  
            min_bedrooms: Minimum bedrooms
            min_bathrooms: Minimum bathrooms
            
        Returns:
            PropertySearchResult with filtered properties
        """
        # Display search criteria
        self.display_service.display_search_criteria(
            title="🔍 Filtered Property Search",
            criteria={
                "property_type": property_type,
                "price_range": {"min": min_price, "max": max_price},
                "bedrooms": min_bedrooms,
                "bathrooms": min_bathrooms
            }
        )
        
        # Build query
        request = PropertyQueryBuilder.filtered_search(
            property_type=property_type,
            min_price=min_price,
            max_price=max_price,
            min_bedrooms=min_bedrooms,
            min_bathrooms=min_bathrooms
        )
        
        # Create filter description
        filters_desc = f"Filter properties by: {PropertyDisplayFormatter.format_property_type(property_type)} type, ${min_price:,.0f}-${max_price:,.0f} price range, {min_bedrooms}+ bedrooms, {min_bathrooms}+ bathrooms"
        
        # Execute search
        result = self.executor.execute_filtered_search(request, filters_desc)
        
        # Display results
        self.display_service.display_filtered_search_results(result)
        
        return result
    
    def run_geo_search(
        self,
        center_lat: float = 37.7749,  # San Francisco
        center_lon: float = -122.4194,
        radius_km: float = 5.0,
        max_price: Optional[float] = 1000000
    ) -> PropertySearchResult:
        """
        Run a geo-distance search demo.
        
        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            radius_km: Search radius in km
            max_price: Optional price limit
            
        Returns:
            PropertySearchResult with nearby properties
        """
        # Display search criteria
        criteria = {
            "location": {"lat": center_lat, "lon": center_lon},
            "radius": radius_km
        }
        if max_price:
            criteria["price_range"] = {"min": 0, "max": max_price}
        
        self.display_service.display_search_criteria(
            title="🗺️  Geo-Distance Property Search",
            criteria=criteria
        )
        
        # Build query
        request = PropertyQueryBuilder.geo_search(
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km,
            max_price=max_price
        )
        
        # Execute search
        result = self.executor.execute_geo_search(
            request, center_lat, center_lon, radius_km
        )
        
        # Display results
        self.display_service.display_geo_search_results(result, radius_km)
        
        return result
    
    def run_price_range_search(
        self,
        min_price: float = 400000,
        max_price: float = 800000
    ) -> AggregationSearchResult:
        """
        Run a price range search with aggregation statistics.
        
        Args:
            min_price: Minimum price
            max_price: Maximum price
            
        Returns:
            AggregationSearchResult with properties and statistics
        """
        # Display search criteria
        self.display_service.display_search_criteria(
            title="📊 Price Range Analysis",
            criteria={
                "price_range": {"min": min_price, "max": max_price}
            }
        )
        
        # Build query
        request = PropertyQueryBuilder.price_range_with_stats(
            min_price=min_price,
            max_price=max_price,
            include_stats=True
        )
        
        # Execute search
        result = self.executor.execute_price_range_with_stats(
            request, min_price, max_price
        )
        
        # Display results
        self.display_service.display_aggregation_results(result)
        
        return result


# Public functions for demo execution
def demo_basic_property_search(
    es_client: Elasticsearch,
    query_text: str = "family home with pool",
    size: int = 10
) -> PropertySearchResult:
    """
    Demo 1: Basic property search using multi-match query.
    
    Args:
        es_client: Elasticsearch client
        query_text: Text to search for
        size: Maximum results (not currently used)
        
    Returns:
        PropertySearchResult with search results
    """
    runner = PropertyDemoRunner(es_client=es_client)
    return runner.run_basic_search(query_text)


def demo_filtered_property_search(
    es_client: Elasticsearch,
    property_type: str = "single-family",
    min_price: float = 300000,
    max_price: float = 800000,
    min_bedrooms: int = 3,
    min_bathrooms: float = 2.0,
    amenities: Optional[List[str]] = None
) -> PropertySearchResult:
    """
    Demo 2: Filtered property search with multiple criteria.
    
    Args:
        es_client: Elasticsearch client
        property_type: Type of property
        min_price: Minimum price
        max_price: Maximum price
        min_bedrooms: Minimum bedrooms
        min_bathrooms: Minimum bathrooms
        amenities: Required amenities (not currently used)
        
    Returns:
        PropertySearchResult with filtered properties
    """
    runner = PropertyDemoRunner(es_client=es_client)
    return runner.run_filtered_search(
        property_type=property_type,
        min_price=min_price,
        max_price=max_price,
        min_bedrooms=min_bedrooms,
        min_bathrooms=min_bathrooms
    )


def demo_geo_distance_search(
    es_client: Elasticsearch,
    center_lat: float = 37.7749,
    center_lon: float = -122.4194,
    radius_km: float = 5.0,
    property_type: Optional[str] = None,
    max_price: Optional[float] = None
) -> PropertySearchResult:
    """
    Demo 3: Geo-distance search for properties near a location.
    
    Args:
        es_client: Elasticsearch client
        center_lat: Center latitude
        center_lon: Center longitude
        radius_km: Search radius in km
        property_type: Optional property type filter (not currently used)
        max_price: Optional maximum price
        
    Returns:
        PropertySearchResult with nearby properties
    """
    runner = PropertyDemoRunner(es_client=es_client)
    return runner.run_geo_search(
        center_lat=center_lat,
        center_lon=center_lon,
        radius_km=radius_km,
        max_price=max_price
    )


def demo_price_range_search(
    es_client: Elasticsearch,
    min_price: float = 400000,
    max_price: float = 800000
) -> AggregationSearchResult:
    """
    Demo 4: Price range search with aggregation statistics.
    
    Args:
        es_client: Elasticsearch client
        min_price: Minimum price
        max_price: Maximum price
        
    Returns:
        AggregationSearchResult with properties and statistics
    """
    runner = PropertyDemoRunner(es_client=es_client)
    return runner.run_price_range_search(
        min_price=min_price,
        max_price=max_price
    )