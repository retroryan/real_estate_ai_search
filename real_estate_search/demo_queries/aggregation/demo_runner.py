"""
Demo orchestration for aggregation queries.

This module coordinates the flow of aggregation demos by combining
query building, execution, result processing, and display.
"""

import logging
from typing import Optional

from elasticsearch import Elasticsearch

from ..result_models import AggregationSearchResult
from ...models import PropertyListing
from .constants import (
    DEFAULT_NEIGHBORHOOD_SIZE,
    DEFAULT_PRICE_INTERVAL,
    DEFAULT_MIN_PRICE,
    DEFAULT_MAX_PRICE,
    PROPERTIES_INDEX
)
from .query_builder import AggregationQueryBuilder
from .result_processor import AggregationResultProcessor
from .display_service import AggregationDisplayService

logger = logging.getLogger(__name__)


def demo_neighborhood_stats(
    es_client: Elasticsearch,
    size: int = DEFAULT_NEIGHBORHOOD_SIZE
) -> AggregationSearchResult:
    """
    Demo 4: Neighborhood statistics aggregation.
    
    Aggregates property data by neighborhood showing average prices,
    property counts, and property type breakdowns.
    
    Args:
        es_client: Elasticsearch client instance
        size: Maximum number of neighborhoods to analyze
        
    Returns:
        AggregationSearchResult with statistics and metadata
    """
    # Initialize services
    query_builder = AggregationQueryBuilder()
    result_processor = AggregationResultProcessor()
    display_service = AggregationDisplayService()
    
    # Build query
    query = query_builder.build_neighborhood_stats_query(size)
    
    try:
        # Execute query
        logger.info(f"Executing neighborhood statistics aggregation for top {size} neighborhoods")
        response = es_client.search(index=PROPERTIES_INDEX, body=query)
        
        # Process results
        results = result_processor.process_neighborhood_aggregations(response)
        
        # Extract global statistics
        global_stats = result_processor.extract_global_stats(response)
        
        # Display results
        display_service.display_neighborhood_stats(response, results, size)
        
        # Create result object
        return AggregationSearchResult(
            query_name="Demo 4: Neighborhood Statistics Aggregation",
            query_description=(
                f"Aggregates property data by neighborhood showing average prices, "
                f"counts, and breakdowns for top {size} neighborhoods"
            ),
            execution_time_ms=response.get('took', 0),
            total_hits=global_stats.total_properties,
            returned_hits=0,  # Aggregations don't return documents
            aggregations=response.get('aggregations', {}),
            top_properties=[],  # No documents returned
            query_dsl=query,
            es_features=[
                "Terms Aggregation - Groups properties by neighborhood_id (like SQL GROUP BY)",
                "Metric Aggregations - Calculates avg, min, max prices and other statistics",
                "Nested Aggregations - Property type breakdown within each neighborhood",
                "Sub-aggregations - Multiple metrics calculated per bucket",
                "Ordering - Sorts neighborhoods by property count",
                "Global Aggregations - Overall statistics across all properties"
            ],
            indexes_used=[
                "properties index - Real estate property listings",
                f"Returns statistics for top {size} neighborhoods by property count"
            ]
        )
        
    except Exception as e:
        logger.error(f"Error in neighborhood stats aggregation: {e}")
        
        # Return error result
        return AggregationSearchResult(
            query_name="Demo 4: Neighborhood Statistics Aggregation",
            query_description=f"Error occurred: {str(e)}",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            aggregations={},
            top_properties=[],
            query_dsl=query,
            es_features=["Error occurred during execution"],
            indexes_used=["properties index"]
        )


def demo_price_distribution(
    es_client: Elasticsearch,
    interval: int = DEFAULT_PRICE_INTERVAL,
    min_price: float = DEFAULT_MIN_PRICE,
    max_price: float = DEFAULT_MAX_PRICE
) -> AggregationSearchResult:
    """
    Demo 5: Price distribution analysis with top 5 most expensive properties.
    
    Creates histogram of property prices and analyzes distribution
    across property types.
    
    Args:
        es_client: Elasticsearch client instance
        interval: Bucket width for price histogram
        min_price: Minimum price for range filter
        max_price: Maximum price for range filter
        
    Returns:
        AggregationSearchResult with distribution data and top properties
    """
    # Initialize services
    query_builder = AggregationQueryBuilder()
    result_processor = AggregationResultProcessor()
    display_service = AggregationDisplayService()
    
    # Build query
    query = query_builder.build_price_distribution_query(interval, min_price, max_price)
    
    try:
        # Execute query
        logger.info(
            f"Executing price distribution analysis from ${min_price:,.0f} to ${max_price:,.0f} "
            f"with ${interval:,.0f} intervals"
        )
        response = es_client.search(index=PROPERTIES_INDEX, body=query)
        
        # Process aggregation results
        histogram_results = result_processor.process_price_distribution(response, interval)
        
        # Extract additional statistics
        percentiles = result_processor.extract_percentiles(response)
        type_stats = result_processor.extract_property_type_stats(response)
        
        # Extract top properties from hits
        property_results = []
        if 'hits' in response and 'hits' in response['hits']:
            for hit in response['hits']['hits']:
                property_results.append(hit['_source'])
        
        # Convert raw property dicts to PropertyListing objects
        top_properties = [PropertyListing.from_elasticsearch(prop) for prop in property_results]
        
        # Display results
        display_service.display_price_distribution(
            response, 
            histogram_results, 
            interval, 
            min_price, 
            max_price
        )
        
        # Create result object
        total_hits = response['hits']['total']['value'] if 'hits' in response else 0
        
        return AggregationSearchResult(
            query_name="Demo 5: Price Distribution Analysis",
            query_description=(
                f"Creates histogram of property prices from ${min_price:,.0f} to ${max_price:,.0f} "
                f"with ${interval:,.0f} intervals, showing top 5 most expensive properties"
            ),
            execution_time_ms=response.get('took', 0),
            total_hits=total_hits,
            returned_hits=len(top_properties),
            aggregations=response.get('aggregations', {}),
            top_properties=top_properties,
            query_dsl=query,
            es_features=[
                "Histogram Aggregation - Creates fixed-size price range buckets",
                "Range Query - Filters properties within price boundaries",
                "Percentiles Aggregation - Calculates price distribution percentiles",
                "Stats Aggregation - Multiple metrics (min/max/avg/sum) in one aggregation",
                "Nested Terms Aggregation - Property type breakdown per price bucket",
                "Extended Bounds - Forces consistent histogram range",
                "Min Doc Count - Omits empty buckets for cleaner results",
                "Sort - Orders results by price descending"
            ],
            indexes_used=[
                "properties index - Real estate property listings",
                f"Analyzes price distribution across {(max_price - min_price) / interval:.0f} price ranges"
            ]
        )
        
    except Exception as e:
        logger.error(f"Error in price distribution analysis: {e}")
        
        # Return error result
        return AggregationSearchResult(
            query_name="Demo 5: Price Distribution Analysis",
            query_description=f"Error occurred: {str(e)}",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            aggregations={},
            top_properties=[],
            query_dsl=query,
            es_features=["Error occurred during execution"],
            indexes_used=["properties index"]
        )