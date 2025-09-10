"""
Demo orchestration for property searches.

This module coordinates query building, search execution, and display
for property search demos. It provides the main entry points for
running various demo scenarios.
"""

from typing import Optional, List
from elasticsearch import Elasticsearch
import logging

from .models import PropertySearchResult
from ..result_models import AggregationSearchResult
from ..property_demo_base import PropertyDemoBase
from ..demo_config import demo_config

logger = logging.getLogger(__name__)


class PropertyDemoRunner(PropertyDemoBase):
    """
    Orchestrates property search demos.
    
    Uses the simplified base class to reduce code duplication
    and provide consistent demo execution patterns.
    """
    
    def __init__(self, es_client: Elasticsearch):
        super().__init__(es_client)
    
    def run_basic_search(
        self,
        query_text: str = None
    ) -> PropertySearchResult:
        """
        Run a basic property search demo.
        
        Args:
            query_text: Text to search for (uses config default if None)
            
        Returns:
            PropertySearchResult with search results
        """
        return self.run_basic_search_demo(query_text)
    
    def run_filtered_search(
        self,
        property_type: str = None,
        min_price: float = None,
        max_price: float = None,
        min_bedrooms: int = None,
        min_bathrooms: float = None
    ) -> PropertySearchResult:
        """
        Run a filtered property search demo.
        
        Args:
            property_type: Type of property (uses config default if None)
            min_price: Minimum price (uses config default if None)
            max_price: Maximum price (uses config default if None)
            min_bedrooms: Minimum bedrooms (uses config default if None)
            min_bathrooms: Minimum bathrooms (uses config default if None)
            
        Returns:
            PropertySearchResult with filtered properties
        """
        return self.run_filtered_search_demo(
            property_type=property_type,
            min_price=min_price,
            max_price=max_price,
            min_bedrooms=min_bedrooms,
            min_bathrooms=min_bathrooms
        )
    
    def run_geo_search(
        self,
        center_lat: float = None,
        center_lon: float = None,
        radius_km: float = None,
        property_type: str = None,
        max_price: Optional[float] = None
    ) -> PropertySearchResult:
        """
        Run a geo-distance search demo.
        
        Args:
            center_lat: Center latitude (uses config default if None)
            center_lon: Center longitude (uses config default if None)
            radius_km: Search radius in km (uses config default if None)
            property_type: Property type filter
            max_price: Optional price limit
            
        Returns:
            PropertySearchResult with nearby properties
        """
        return self.run_geo_search_demo(
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km,
            property_type=property_type,
            max_price=max_price
        )
    
    def run_price_range_search(
        self,
        min_price: float = None,
        max_price: float = None
    ) -> PropertySearchResult:
        """
        Run a price range search with statistics.
        
        Args:
            min_price: Minimum price (uses config default if None)
            max_price: Maximum price (uses config default if None)
            
        Returns:
            PropertySearchResult with properties in price range
        """
        # Use defaults from config
        if min_price is None:
            min_price = demo_config.property_defaults.min_price
        if max_price is None:
            max_price = demo_config.property_defaults.max_price
        
        def build_query():
            request = self.query_builder.price_range_with_stats(
                min_price=min_price,
                max_price=max_price,
                include_stats=True
            )
            return request.to_dict()
        
        def process_result(response, execution_time_ms):
            return self.process_property_response(
                response=response,
                execution_time_ms=execution_time_ms,
                query_name="Price Range Search with Statistics",
                query_description=f"Properties priced between ${min_price:,.0f} and ${max_price:,.0f} with statistical analysis",
                es_features=[
                    "Range Query - Filters properties within price boundaries",
                    "Stats Aggregation - Calculates price statistics (min/max/avg)",
                    "Histogram Aggregation - Price distribution analysis",
                    "Terms Aggregation - Property type breakdown",
                    "Sort by Price - Ascending price ordering"
                ],
                additional_context=f"Price range: ${min_price:,.0f} to ${max_price:,.0f}"
            )
        
        return self.execute_demo(
            demo_name="Price Range Search with Statistics",
            query_builder_func=build_query,
            result_processor_func=process_result
        )


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