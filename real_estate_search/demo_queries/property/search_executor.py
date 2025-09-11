"""
Search execution and result processing for property queries.

This module handles Elasticsearch interaction, response processing,
and conversion to typed result models. No display logic or formatting.
"""

from typing import Dict, Any, Optional, List, Tuple
from elasticsearch import Elasticsearch
import logging
from pydantic import BaseModel

from ...models.search import SearchRequest, SearchResponse
from ...models.results import PropertySearchResult, AggregationSearchResult
from ..display_formatter import PropertyDisplayFormatter
from ...models import PropertyListing

logger = logging.getLogger(__name__)


class PropertySearchExecutor(BaseModel):
    """
    Executes property searches against Elasticsearch and processes results.
    
    This class handles all Elasticsearch interactions and converts raw
    responses into strongly-typed result objects.
    """
    
    es_client: Elasticsearch
    
    class Config:
        arbitrary_types_allowed = True
    
    def execute(self, request: SearchRequest) -> Tuple[Optional[SearchResponse], int]:
        """
        Execute a search request and measure timing.
        
        Args:
            request: SearchRequest to execute
            
        Returns:
            Tuple of (SearchResponse or None, execution time in ms)
        """
        import time
        start_time = time.time()
        
        try:
            response = self.es_client.search(
                index=request.index,
                body=request.to_dict()
            )
            execution_time = int((time.time() - start_time) * 1000)
            return SearchResponse.from_elasticsearch(response), execution_time
            
        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            return None, execution_time
    
    def process_results(self, response: SearchResponse) -> List[PropertyListing]:
        """
        Convert Elasticsearch hits to PropertyListing objects.
        
        Args:
            response: SearchResponse from Elasticsearch
            
        Returns:
            List of PropertyListing objects
        """
        results = []
        for hit in response.hits:
            try:
                # Add score to source data for PropertyListing
                source_data = hit.source.copy()
                if hit.score is not None:
                    source_data['_score'] = hit.score
                results.append(PropertyListing(**source_data))
            except Exception as e:
                logger.warning(f"Failed to parse property result: {e}")
                continue
        return results
    
    def execute_basic_search(
        self,
        request: SearchRequest,
        query_text: str
    ) -> PropertySearchResult:
        """
        Execute a basic property search and return results.
        
        Args:
            request: SearchRequest to execute
            query_text: Original query text for documentation
            
        Returns:
            PropertySearchResult with search results
        """
        response, exec_time = self.execute(request)
        
        if not response:
            return PropertySearchResult(
                query_name="Basic Property Search",
                execution_time_ms=exec_time,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=request.to_dict(),
                already_displayed=True
            )
        
        results = self.process_results(response)
        
        return PropertySearchResult(
            query_name=f"Basic Property Search: '{query_text}'",
            query_description=f"Full-text search for '{query_text}' across property descriptions, amenities, and addresses with fuzzy matching to handle typos",
            execution_time_ms=exec_time,
            total_hits=response.total_hits,
            returned_hits=len(results),
            results=results,
            query_dsl=request.to_dict(),
            es_features=[
                "Multi-Match Query: Searches across multiple fields simultaneously",
                "Field Boosting: Weights description 2x, amenities 1.5x for relevance",
                "Fuzzy Matching: AUTO fuzziness handles typos and variations",
                "Highlighting: Shows matched text fragments in results",
                "Query Context: Calculates relevance scores for ranking"
            ],
            indexes_used=[
                "properties index: 420 real estate listings",
                "Fields searched: description, amenities, address.street, address.city, neighborhood_id"
            ],
            explanation=f"Searched for '{query_text}' across description, amenities, and address fields with fuzzy matching",
            already_displayed=True  # Mark as displayed since PropertyDisplayService shows it
        )
    
    def execute_filtered_search(
        self,
        request: SearchRequest,
        filters_desc: str
    ) -> PropertySearchResult:
        """
        Execute a filtered property search and return results.
        
        Args:
            request: SearchRequest to execute
            filters_desc: Description of filters for documentation
            
        Returns:
            PropertySearchResult with filtered results
        """
        response, exec_time = self.execute(request)
        
        if not response:
            return PropertySearchResult(
                query_name="Filtered Property Search",
                execution_time_ms=exec_time,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=request.to_dict(),
                already_displayed=True
            )
        
        results = self.process_results(response)
        
        return PropertySearchResult(
            query_name="Filtered Property Search",
            query_description=filters_desc,
            execution_time_ms=exec_time,
            total_hits=response.total_hits,
            returned_hits=len(results),
            results=results,
            query_dsl=request.to_dict(),
            es_features=[
                "Bool Query with Filters: Combines multiple criteria using filter context",
                "Filter Context: Non-scoring queries cached for performance",
                "Range Queries: Numeric filtering for price, bedrooms, bathrooms",
                "Term Query: Exact matching on property type",
                "Sort by Price: Results ordered by price ascending"
            ],
            indexes_used=[
                "properties index: 420 real estate listings",
                "Filtered fields: property_type, price, bedrooms, bathrooms"
            ],
            explanation=filters_desc,
            already_displayed=True  # Mark as displayed since PropertyDisplayService shows it
        )
    
    def execute_geo_search(
        self,
        request: SearchRequest,
        center_lat: float,
        center_lon: float,
        radius_km: float
    ) -> PropertySearchResult:
        """
        Execute a geo-distance search and return results.
        
        Args:
            request: SearchRequest to execute
            center_lat: Center latitude
            center_lon: Center longitude
            radius_km: Search radius
            
        Returns:
            PropertySearchResult with geo-filtered results
        """
        response, exec_time = self.execute(request)
        
        if not response:
            return PropertySearchResult(
                query_name="Geo-Distance Property Search",
                execution_time_ms=exec_time,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=request.to_dict(),
                already_displayed=True
            )
        
        results = self.process_results(response)
        
        return PropertySearchResult(
            query_name="Geo-Distance Property Search",
            query_description=f"Find properties within {radius_km}km radius of coordinates ({center_lat:.4f}, {center_lon:.4f}) with optional price filtering",
            execution_time_ms=exec_time,
            total_hits=response.total_hits,
            returned_hits=len(results),
            results=results,
            query_dsl=request.to_dict(),
            es_features=[
                "Geo-Distance Query: Filters documents within radius of a point",
                "Geo-Point Field: Uses address.location field for coordinates",
                "Distance Sorting: Results ordered by distance from center",
                "Distance Calculation: Arc method for accurate distances",
                "Combined Filters: Geo filter with optional price constraints"
            ],
            indexes_used=[
                "properties index: 420 real estate listings with geo-coordinates",
                "Geo field: address.location (lat/lon pairs)",
                f"Search area: {radius_km}km radius in San Francisco area"
            ],
            explanation=f"Properties within {radius_km}km of ({center_lat}, {center_lon})",
            already_displayed=True  # Mark as displayed since PropertyDisplayService shows it
        )
    
    def execute_price_range_with_stats(
        self,
        request: SearchRequest,
        min_price: float,
        max_price: float
    ) -> AggregationSearchResult:
        """
        Execute a price range search with aggregations.
        
        Args:
            request: SearchRequest to execute
            min_price: Minimum price
            max_price: Maximum price
            
        Returns:
            AggregationSearchResult with statistics
        """
        response, exec_time = self.execute(request)
        
        if not response:
            return AggregationSearchResult(
                query_name="Price Range Search with Analytics",
                execution_time_ms=exec_time,
                total_hits=0,
                returned_hits=0,
                top_properties=[],
                query_dsl=request.to_dict(),
                aggregations=None
            )
        
        results = self.process_results(response)
        
        # Process aggregations
        aggregations = None
        if response.aggregations:
            aggregations = {}
            
            if 'price_stats' in response.aggregations:
                stats = response.aggregations['price_stats']
                aggregations['price_stats'] = {
                    "min": stats.get('min', 0),
                    "max": stats.get('max', 0),
                    "avg": stats.get('avg', 0),
                    "sum": stats.get('sum', 0),
                    "count": stats.get('count', 0)
                }
            
            if 'property_types' in response.aggregations:
                aggregations['property_types'] = response.aggregations['property_types']
            
            if 'price_histogram' in response.aggregations:
                aggregations['price_histogram'] = response.aggregations['price_histogram']
            
            if 'bedroom_stats' in response.aggregations:
                aggregations['bedroom_stats'] = response.aggregations['bedroom_stats']
        
        return AggregationSearchResult(
            query_name="Price Range Search with Analytics",
            query_description=f"Search properties in ${min_price:,.0f}-${max_price:,.0f} range with statistical aggregations for market analysis",
            execution_time_ms=exec_time,
            total_hits=response.total_hits,
            returned_hits=len(results),
            top_properties=results,
            query_dsl=request.to_dict(),
            aggregations=aggregations,
            es_features=[
                "Range Query: Filter properties by price range",
                "Stats Aggregation: Calculate min, max, avg, sum statistics",
                "Histogram Aggregation: Price distribution in $100k buckets",
                "Terms Aggregation: Group by property types",
                "Multi-Aggregation: Multiple analytics in single query"
            ],
            indexes_used=[
                "properties index: 420 real estate listings",
                "Aggregation fields: price, property_type, bedrooms",
                "Statistical analysis across matching properties"
            ],
            explanation=f"Properties ${min_price:,.0f}-${max_price:,.0f} with statistical analysis"
        )