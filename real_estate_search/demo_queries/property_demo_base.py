"""
Property-specific demo runner base class.

Provides common patterns for property search demos.
"""

from typing import Dict, Any, Optional, List
from elasticsearch import Elasticsearch

from .base_demo_runner import BaseDemoRunner
from .property.models import PropertySearchResult
from .property.query_builder import PropertyQueryBuilder
from ..models import PropertyListing
from .demo_config import demo_config


class PropertyDemoBase(BaseDemoRunner[PropertySearchResult]):
    """
    Base class for property search demos.
    
    Provides common functionality for all property-related demos
    including result processing and error handling.
    """
    
    def __init__(self, es_client: Elasticsearch):
        """Initialize property demo runner."""
        super().__init__(es_client)
        self.query_builder = PropertyQueryBuilder()
    
    def create_error_result(
        self,
        demo_name: str,
        error_message: str,
        execution_time_ms: float,
        query_dsl: Dict[str, Any],
        **kwargs
    ) -> PropertySearchResult:
        """Create a property search error result."""
        return PropertySearchResult(
            query_name=demo_name,
            query_description=f"Error occurred: {error_message}",
            execution_time_ms=int(execution_time_ms),
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=query_dsl,
            es_features=["Error occurred during execution"],
            indexes_used=[demo_config.indexes.properties_index]
        )
    
    def process_property_response(
        self,
        response: Dict[str, Any],
        execution_time_ms: float,
        query_name: str,
        query_description: str,
        es_features: List[str],
        additional_context: str = "",
        **kwargs
    ) -> PropertySearchResult:
        """
        Standard property response processing.
        
        Args:
            response: Elasticsearch response
            execution_time_ms: Time taken for execution
            query_name: Name of the query
            query_description: Description of what the query does
            es_features: List of Elasticsearch features used
            additional_context: Additional context for indexes_used
            **kwargs: Additional arguments (e.g., query_dsl)
            
        Returns:
            PropertySearchResult with processed data
        """
        # Extract data safely
        hits, total_count = self.safe_extract_hits(response)
        search_time_ms = self.safe_get_execution_time(response)
        
        # Convert hits to PropertyListing objects
        property_results = []
        for hit in hits:
            try:
                prop = PropertyListing.from_elasticsearch(hit['_source'])
                property_results.append(prop)
            except Exception as e:
                self.logger.warning(f"Failed to convert property listing: {e}")
        
        # Build indexes used list
        indexes_used = self.build_indexes_used_list(
            demo_config.indexes.properties_index,
            additional_context
        )
        
        return PropertySearchResult(
            query_name=query_name,
            query_description=query_description,
            execution_time_ms=int(search_time_ms or execution_time_ms),
            total_hits=total_count,
            returned_hits=len(property_results),
            results=property_results,
            query_dsl=kwargs.get('query_dsl', {}),
            es_features=self.build_es_features_list(es_features),
            indexes_used=indexes_used
        )
    
    def run_basic_search_demo(
        self,
        query_text: str = None
    ) -> PropertySearchResult:
        """Run basic property search demo."""
        if query_text is None:
            query_text = demo_config.property_defaults.query_text
        
        def build_query():
            request = self.query_builder.basic_search(query_text)
            return request.to_dict()
        
        def process_result(response, execution_time_ms):
            return self.process_property_response(
                response=response,
                execution_time_ms=execution_time_ms,
                query_name="Demo 1: Basic Property Search",
                query_description=f"Multi-match search across property fields for: '{query_text}'",
                es_features=[
                    "Multi-Match Query - Searches across multiple text fields",
                    "Field Boosting - Gives higher weight to description and features",
                    "Fuzzy Matching - AUTO fuzziness for typo tolerance",
                    "Highlighting - Shows matched text snippets",
                    "Source Filtering - Returns only needed fields"
                ],
                additional_context=f"Searching for properties matching: '{query_text}'"
            )
        
        return self.execute_demo(
            demo_name="Basic Property Search",
            query_builder_func=build_query,
            result_processor_func=process_result
        )
    
    def run_filtered_search_demo(
        self,
        property_type: str = None,
        min_price: float = None,
        max_price: float = None,
        min_bedrooms: int = None,
        min_bathrooms: float = None
    ) -> PropertySearchResult:
        """Run filtered property search demo."""
        # Use defaults from config
        property_type = property_type or demo_config.property_defaults.property_type
        min_price = min_price or demo_config.property_defaults.min_price
        max_price = max_price or demo_config.property_defaults.max_price
        min_bedrooms = min_bedrooms or demo_config.property_defaults.min_bedrooms
        min_bathrooms = min_bathrooms or demo_config.property_defaults.min_bathrooms
        
        def build_query():
            request = self.query_builder.filtered_search(
                property_type=property_type,
                min_price=min_price,
                max_price=max_price,
                min_bedrooms=min_bedrooms,
                min_bathrooms=min_bathrooms
            )
            return request.to_dict()
        
        def process_result(response, execution_time_ms):
            return self.process_property_response(
                response=response,
                execution_time_ms=execution_time_ms,
                query_name="Demo 2: Filtered Property Search",
                query_description=f"Filter properties by type ({property_type}), price (${min_price:,.0f}-${max_price:,.0f}), bedrooms ({min_bedrooms}+), bathrooms ({min_bathrooms}+)",
                es_features=[
                    "Bool Query - Combines multiple filter conditions",
                    "Term Filters - Exact matches for property type",
                    "Range Filters - Numeric ranges for price, bedrooms, bathrooms",
                    "Match Filters - Text matching for amenities",
                    "Sort by Price - Ascending price ordering"
                ],
                additional_context=f"Filtering by: {property_type}, ${min_price:,.0f}-${max_price:,.0f}, {min_bedrooms}+ bed, {min_bathrooms}+ bath"
            )
        
        return self.execute_demo(
            demo_name="Filtered Property Search",
            query_builder_func=build_query,
            result_processor_func=process_result
        )
    
    def run_geo_search_demo(
        self,
        center_lat: float = None,
        center_lon: float = None,
        radius_km: float = None,
        property_type: str = None,
        max_price: float = None
    ) -> PropertySearchResult:
        """Run geo-distance search demo."""
        # Use defaults from config
        center_lat = center_lat or demo_config.property_defaults.geo_center_lat
        center_lon = center_lon or demo_config.property_defaults.geo_center_lon
        radius_km = radius_km or demo_config.property_defaults.geo_radius_km
        
        def build_query():
            request = self.query_builder.geo_search(
                center_lat=center_lat,
                center_lon=center_lon,
                radius_km=radius_km,
                property_type=property_type,
                max_price=max_price
            )
            return request.to_dict()
        
        def process_result(response, execution_time_ms):
            return self.process_property_response(
                response=response,
                execution_time_ms=execution_time_ms,
                query_name="Demo 3: Geo-Distance Property Search",
                query_description=f"Find properties within {radius_km}km of coordinates ({center_lat}, {center_lon})",
                es_features=[
                    "Geo-Distance Query - Searches within geographic radius",
                    "Geographic Coordinates - Lat/lon based location filtering",
                    "Distance Sorting - Orders results by proximity to center point",
                    "Geo-Point Field - Efficient geographic indexing",
                    "Radius Search - Configurable search distance in kilometers"
                ],
                additional_context=f"Within {radius_km}km of ({center_lat}, {center_lon})"
            )
        
        return self.execute_demo(
            demo_name="Geo-Distance Property Search",
            query_builder_func=build_query,
            result_processor_func=process_result
        )