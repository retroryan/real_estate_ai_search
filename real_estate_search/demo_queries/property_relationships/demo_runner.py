"""
Demo runner for property relationships using denormalized index.

Orchestrates property relationship demonstrations using the denormalized
property_relationships index for single-query retrieval.
"""

from typing import Optional
from elasticsearch import Elasticsearch

from ..relationship_demo_base import RelationshipDemoBase
from ..result_models import MixedEntityResult
from ..demo_config import demo_config
from .query_builder import PropertyRelationshipsQueryBuilder


class PropertyRelationshipDemoRunner(RelationshipDemoBase):
    """
    Orchestrates property relationship demos using base class patterns.
    """
    
    def __init__(self, es_client: Elasticsearch):
        """Initialize property relationship demo runner."""
        super().__init__(es_client)
        self.query_builder = PropertyRelationshipsQueryBuilder()
    
    def run_single_property_demo(
        self,
        property_id: Optional[str] = None
    ) -> MixedEntityResult:
        """
        Get complete property context with a single query.
        
        Args:
            property_id: Optional property ID, otherwise random
            
        Returns:
            Complete property with neighborhood and Wikipedia data
        """
        return self.execute_single_property_query(property_id)
    
    def run_neighborhood_demo(
        self,
        neighborhood_name: Optional[str] = None
    ) -> MixedEntityResult:
        """
        Get all properties in a neighborhood with a single query.
        
        Args:
            neighborhood_name: Neighborhood to search (uses default if None)
            
        Returns:
            Properties in the neighborhood
        """
        neighborhood = neighborhood_name or demo_config.relationship_defaults.default_neighborhood
        return self.execute_neighborhood_query(neighborhood)
    
    def run_location_demo(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None
    ) -> MixedEntityResult:
        """
        Search by location with full context in a single query.
        
        Args:
            city: City name (uses default if None)
            state: State code (uses default if None)
            
        Returns:
            Properties in location with full context
        """
        city = city or demo_config.relationship_defaults.default_city
        state = state or demo_config.relationship_defaults.default_state
        
        query_dsl = self.query_builder.build_search_query(
            city=city,
            state=state,
            size=5
        )
        
        # Override sort to sort by price descending
        query_dsl["sort"] = [{"price": {"order": "desc"}}]
        
        return self.execute_demo(
            demo_name=f"Location: {city}, {state}",
            query_builder_func=lambda: query_dsl,
            result_processor_func=lambda resp, time_ms, **kwargs: self.process_denormalized_response(
                resp, time_ms,
                query_name=f"Location: {city}, {state}",
                query_description=f"Properties in {city}, {state} with full context",
                **kwargs
            ),
            index_name=self.index_name
        )
    
    def run_complete_demo(self) -> MixedEntityResult:
        """
        Run complete property relationships demo with multiple queries.
        
        Returns:
            Combined results from all demo queries
        """
        # Run three demo queries
        result1 = self.run_single_property_demo()
        result2 = self.run_neighborhood_demo()
        result3 = self.run_location_demo()
        
        # Combine execution times
        total_time = (
            result1.execution_time_ms + 
            result2.execution_time_ms + 
            result3.execution_time_ms
        )
        
        # Combine unique properties
        unique_properties = self._combine_unique_properties(
            [result1, result2, result3],
            max_results=10
        )
        
        # Build combined result
        return MixedEntityResult(
            query_name="Property Relationships via Denormalized Index",
            query_description="Single-query retrieval using denormalized index",
            execution_time_ms=total_time,
            total_hits=result1.total_hits + result2.total_hits + result3.total_hits,
            returned_hits=len(unique_properties),
            property_results=unique_properties,
            wikipedia_results=result1.wikipedia_results[:5],
            neighborhood_results=result1.neighborhood_results,
            query_dsl=self._build_demo_query_dsl(total_time),
            es_features=self._get_demo_features(),
            indexes_used=self._get_demo_indexes()
        )
    
    def _combine_unique_properties(self, results: list, max_results: int) -> list:
        """Combine unique properties from multiple results."""
        unique_properties = []
        seen_ids = set()
        
        for result in results:
            for prop in result.property_results:
                if prop.listing_id not in seen_ids:
                    unique_properties.append(prop)
                    seen_ids.add(prop.listing_id)
                    if len(unique_properties) >= max_results:
                        return unique_properties
        
        return unique_properties
    
    def _build_demo_query_dsl(self, total_time: int) -> dict:
        """Build query DSL description for demo."""
        return {
            "description": "Denormalized index enables single-query retrieval",
            "comparison": {
                "before": "3-6 queries, 200+ lines of code",
                "after": "1 query, ~20 lines of code",
                "performance": f"Total time for 3 operations: {total_time}ms"
            },
            "benefits": [
                "Single query retrieves all related data",
                "No JOIN operations required",
                "Optimized for read performance",
                "Simplified application logic",
                "Consistent data snapshot"
            ]
        }
    
    def _get_demo_features(self) -> list:
        """Get Elasticsearch features for demo."""
        return [
            "Denormalized Index - All related data in single document",
            "Embedded Documents - Neighborhood and Wikipedia data included",
            "Single Query Retrieval - No additional lookups needed",
            "Filter Context - Efficient non-scoring queries",
            "Term Queries - Exact matching on fields",
            "Function Score - Random property selection"
        ]
    
    def _get_demo_indexes(self) -> list:
        """Get index descriptions for demo."""
        return [
            "property_relationships index - Denormalized property data",
            "Contains embedded neighborhood and Wikipedia data",
            "Optimized for read-heavy workloads"
        ]