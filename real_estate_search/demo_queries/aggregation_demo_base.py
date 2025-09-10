"""
Aggregation-specific demo runner base class.

Provides common patterns for aggregation demos.
"""

from typing import Dict, Any, List
from elasticsearch import Elasticsearch

from .base_demo_runner import BaseDemoRunner
from .result_models import AggregationSearchResult
from .property.query_builder import PropertyQueryBuilder
from .aggregation.result_processor import AggregationResultProcessor
from ..models import PropertyListing
from .demo_config import demo_config


class AggregationDemoBase(BaseDemoRunner[AggregationSearchResult]):
    """
    Base class for aggregation demos.
    
    Provides common functionality for all aggregation-related demos
    including result processing and error handling.
    """
    
    def __init__(self, es_client: Elasticsearch):
        """Initialize aggregation demo runner."""
        super().__init__(es_client)
        self.query_builder = PropertyQueryBuilder()
        self.result_processor = AggregationResultProcessor()
    
    def create_error_result(
        self,
        demo_name: str,
        error_message: str,
        execution_time_ms: float,
        query_dsl: Dict[str, Any],
        **kwargs
    ) -> AggregationSearchResult:
        """Create an aggregation error result."""
        return AggregationSearchResult(
            query_name=demo_name,
            query_description=f"Error occurred: {error_message}",
            execution_time_ms=int(execution_time_ms),
            total_hits=0,
            returned_hits=0,
            aggregations={},
            top_properties=[],
            query_dsl=query_dsl,
            es_features=["Error occurred during execution"],
            indexes_used=[demo_config.indexes.properties_index]
        )
    
    def process_aggregation_response(
        self,
        response: Dict[str, Any],
        execution_time_ms: float,
        query_name: str,
        query_description: str,
        es_features: List[str],
        additional_context: str = "",
        include_top_properties: bool = False,
        **kwargs
    ) -> AggregationSearchResult:
        """
        Standard aggregation response processing.
        
        Args:
            response: Elasticsearch response
            execution_time_ms: Time taken for execution
            query_name: Name of the query
            query_description: Description of what the query does
            es_features: List of Elasticsearch features used
            additional_context: Additional context for indexes_used
            include_top_properties: Whether to include top properties in results
            **kwargs: Additional arguments
            
        Returns:
            AggregationSearchResult with processed data
        """
        # Extract data safely
        hits, total_count = self.safe_extract_hits(response)
        aggregations = self.safe_extract_aggregations(response)
        search_time_ms = self.safe_get_execution_time(response)
        
        # Convert hits to PropertyListing objects if needed
        top_properties = []
        if include_top_properties and hits:
            for hit in hits:
                try:
                    prop = PropertyListing.from_elasticsearch(hit['_source'])
                    top_properties.append(prop)
                except Exception as e:
                    self.logger.warning(f"Failed to convert property listing: {e}")
        
        # Build indexes used list
        indexes_used = self.build_indexes_used_list(
            demo_config.indexes.properties_index,
            additional_context
        )
        
        return AggregationSearchResult(
            query_name=query_name,
            query_description=query_description,
            execution_time_ms=int(search_time_ms or execution_time_ms),
            total_hits=total_count,
            returned_hits=len(top_properties),
            aggregations=aggregations,
            top_properties=top_properties,
            query_dsl=kwargs.get('query_dsl', {}),
            es_features=self.build_es_features_list(es_features),
            indexes_used=indexes_used
        )
    
    def run_neighborhood_stats_demo(
        self,
        size: int = None
    ) -> AggregationSearchResult:
        """Run neighborhood statistics aggregation demo."""
        if size is None:
            size = demo_config.aggregation_defaults.neighborhood_size
        
        def build_query():
            return PropertyQueryBuilder.neighborhood_stats_aggregation(size)
        
        def process_result(response, execution_time_ms, query_dsl=None, **kwargs):
            return self.process_aggregation_response(
                response=response,
                execution_time_ms=execution_time_ms,
                query_name="Demo 4: Neighborhood Statistics",
                query_description=f"Aggregates property data by neighborhood showing average prices, counts, and breakdowns for top {size} neighborhoods",
                es_features=[
                    "Terms Aggregation - Groups properties by neighborhood_id (like SQL GROUP BY)",
                    "Metric Aggregations - Calculates avg, min, max prices and other statistics",
                    "Nested Aggregations - Property type breakdown within each neighborhood",
                    "Sub-aggregations - Multiple metrics calculated per bucket",
                    "Ordering - Sorts neighborhoods by property count",
                    "Global Aggregations - Overall statistics across all properties"
                ],
                additional_context=f"Returns statistics for top {size} neighborhoods by property count",
                include_top_properties=False,
                query_dsl=query_dsl
            )
        
        return self.execute_demo(
            demo_name="Neighborhood Statistics Aggregation",
            query_builder_func=build_query,
            result_processor_func=process_result
        )
    
    def run_price_distribution_demo(
        self,
        interval: int = None,
        min_price: float = None,
        max_price: float = None
    ) -> AggregationSearchResult:
        """Run price distribution analysis demo."""
        # Use defaults from config
        if interval is None:
            interval = demo_config.aggregation_defaults.price_interval
        if min_price is None:
            min_price = demo_config.aggregation_defaults.min_price
        if max_price is None:
            max_price = demo_config.aggregation_defaults.max_price
        
        def build_query():
            return PropertyQueryBuilder.price_distribution_aggregation(interval, min_price, max_price)
        
        def process_result(response, execution_time_ms, query_dsl=None, **kwargs):
            return self.process_aggregation_response(
                response=response,
                execution_time_ms=execution_time_ms,
                query_name="Demo 5: Price Distribution Analysis",
                query_description=f"Creates histogram of property prices from ${min_price:,.0f} to ${max_price:,.0f} with ${interval:,.0f} intervals, showing top {demo_config.aggregation_defaults.top_properties_count} most expensive properties",
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
                additional_context=f"Analyzes price distribution across {(max_price - min_price) / interval:.0f} price ranges",
                include_top_properties=True,
                query_dsl=query_dsl
            )
        
        return self.execute_demo(
            demo_name="Price Distribution Analysis",
            query_builder_func=build_query,
            result_processor_func=process_result
        )