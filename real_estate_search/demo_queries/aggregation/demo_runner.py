"""
Demo orchestration for aggregation queries.

This module coordinates the flow of aggregation demos by combining
query building, execution, result processing, and display.
"""

import logging
from typing import Optional

from elasticsearch import Elasticsearch

from ..result_models import AggregationSearchResult
from ..demo_config import demo_config
from ..aggregation_demo_base import AggregationDemoBase

logger = logging.getLogger(__name__)


class AggregationDemoRunner(AggregationDemoBase):
    """
    Orchestrates aggregation demos.
    
    Uses the simplified base class to reduce code duplication
    and provide consistent demo execution patterns.
    """
    
    def __init__(self, es_client: Elasticsearch):
        super().__init__(es_client)


def demo_neighborhood_stats(
    es_client: Elasticsearch,
    size: int = None
) -> AggregationSearchResult:
    """
    Demo 4: Neighborhood statistics aggregation.
    
    Args:
        es_client: Elasticsearch client instance
        size: Maximum number of neighborhoods to analyze
        
    Returns:
        AggregationSearchResult with statistics and metadata
    """
    runner = AggregationDemoRunner(es_client)
    return runner.run_neighborhood_stats_demo(size)


def demo_price_distribution(
    es_client: Elasticsearch,
    interval: int = None,
    min_price: float = None,
    max_price: float = None
) -> AggregationSearchResult:
    """
    Demo 5: Price distribution analysis with top properties.
    
    Args:
        es_client: Elasticsearch client instance
        interval: Bucket width for price histogram
        min_price: Minimum price for range filter
        max_price: Maximum price for range filter
        
    Returns:
        AggregationSearchResult with distribution data and top properties
    """
    runner = AggregationDemoRunner(es_client)
    return runner.run_price_distribution_demo(interval, min_price, max_price)