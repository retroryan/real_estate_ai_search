"""
Relationship-specific demo runner base class.

Provides common patterns for demos using the denormalized
property_relationships index that contains embedded neighborhood
and Wikipedia data.
"""

from typing import Dict, Any, Optional, List
from elasticsearch import Elasticsearch

from .base_demo_runner import BaseDemoRunner
from .result_models import MixedEntityResult
from ..models import PropertyListing, WikipediaArticle
from .demo_config import demo_config
from ..indexer.enums import IndexName


class RelationshipDemoBase(BaseDemoRunner[MixedEntityResult]):
    """
    Base class for property relationship demos.
    
    Handles queries against the denormalized property_relationships
    index that contains embedded neighborhood and Wikipedia data.
    """
    
    def __init__(self, es_client: Elasticsearch):
        """
        Initialize relationship demo runner.
        
        Args:
            es_client: Elasticsearch client
        """
        super().__init__(es_client)
        self.index_name = IndexName.PROPERTY_RELATIONSHIPS.value
    
    def create_error_result(
        self,
        demo_name: str,
        error_message: str,
        execution_time_ms: float,
        query_dsl: Dict[str, Any],
        **kwargs
    ) -> MixedEntityResult:
        """Create a relationship search error result."""
        return MixedEntityResult(
            query_name=demo_name,
            query_description=f"Error occurred: {error_message}",
            execution_time_ms=int(execution_time_ms),
            total_hits=0,
            returned_hits=0,
            property_results=[],
            wikipedia_results=[],
            neighborhood_results=[],
            query_dsl=query_dsl,
            es_features=["Error occurred during relationship query"],
            indexes_used=[self.index_name]
        )
    
    def process_denormalized_response(
        self,
        response: Dict[str, Any],
        execution_time_ms: float,
        query_name: str,
        query_description: str,
        **kwargs
    ) -> MixedEntityResult:
        """
        Process response from denormalized index into MixedEntityResult.
        
        Args:
            response: Elasticsearch response
            execution_time_ms: Time taken for execution
            query_name: Name of the query
            query_description: Description of what the query does
            **kwargs: Additional arguments
            
        Returns:
            MixedEntityResult with extracted entities
        """
        # Extract hits
        hits, total_count = self.safe_extract_hits(response)
        
        # Process results
        property_results = []
        wikipedia_results = []
        neighborhood_results = []
        
        for hit in hits:
            source = hit.get('_source', {})
            
            # Extract property data
            try:
                prop = PropertyListing.from_elasticsearch(source)
                property_results.append(prop)
            except Exception as e:
                self.logger.warning(f"Failed to extract property: {e}")
            
            # Extract embedded neighborhood data
            neighborhood = source.get('neighborhood', {})
            if neighborhood and neighborhood not in neighborhood_results:
                neighborhood_results.append(neighborhood)
            
            # Extract embedded Wikipedia articles
            articles = source.get('wikipedia_articles', [])
            for article in articles:
                try:
                    wiki = WikipediaArticle(
                        page_id=str(article.get('page_id', '')),
                        title=article.get('title', ''),
                        long_summary=article.get('long_summary'),
                        short_summary=article.get('short_summary'),
                        city=article.get('city'),
                        state=article.get('state'),
                        url=article.get('url')
                    )
                    if wiki not in wikipedia_results:
                        wikipedia_results.append(wiki)
                except Exception as e:
                    self.logger.warning(f"Failed to extract Wikipedia article: {e}")
        
        # Build result
        return MixedEntityResult(
            query_name=query_name,
            query_description=query_description,
            execution_time_ms=int(execution_time_ms),
            total_hits=total_count,
            returned_hits=len(property_results),
            property_results=property_results,
            wikipedia_results=wikipedia_results[:5],  # Limit Wikipedia results
            neighborhood_results=neighborhood_results[:3],  # Limit neighborhood results
            query_dsl=kwargs.get('query_dsl', {}),
            es_features=kwargs.get('es_features', [
                "Denormalized Index - All related data in single document",
                "Embedded Documents - Neighborhood and Wikipedia data included",
                "Single Query Retrieval - No additional lookups needed",
                f"Query executed in {execution_time_ms}ms"
            ]),
            indexes_used=[
                f"{self.index_name} - Denormalized property data",
                "Contains embedded neighborhood and Wikipedia data"
            ]
        )
    
    def execute_single_property_query(
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
        # Build query
        if property_id:
            query_dsl = {
                "query": {
                    "term": {
                        "listing_id": property_id
                    }
                },
                "size": 1
            }
            query_name = f"Property: {property_id}"
        else:
            query_dsl = {
                "query": {
                    "function_score": {
                        "query": {"match_all": {}},
                        "random_score": {"seed": demo_config.relationship_defaults.random_seed}
                    }
                },
                "size": 1
            }
            query_name = "Random Property with Full Context"
        
        # Execute using base pattern
        return self.execute_demo(
            demo_name=query_name,
            query_builder_func=lambda: query_dsl,
            result_processor_func=lambda resp, time_ms, **kwargs: self.process_denormalized_response(
                resp, time_ms,
                query_name=query_name,
                query_description="Single query retrieves property with all relationships",
                **kwargs
            ),
            index_name=self.index_name
        )
    
    def execute_neighborhood_query(
        self,
        neighborhood_name: str,
        size: int = 10
    ) -> MixedEntityResult:
        """
        Get all properties in a neighborhood with a single query.
        
        Args:
            neighborhood_name: Neighborhood to search
            size: Number of results to return
            
        Returns:
            Properties in the neighborhood
        """
        query_dsl = {
            "query": {
                "match": {
                    "neighborhood.name": neighborhood_name
                }
            },
            "size": size
        }
        
        return self.execute_demo(
            demo_name=f"Neighborhood: {neighborhood_name}",
            query_builder_func=lambda: query_dsl,
            result_processor_func=lambda resp, time_ms, **kwargs: self.process_denormalized_response(
                resp, time_ms,
                query_name=f"Neighborhood: {neighborhood_name}",
                query_description=f"Properties in {neighborhood_name} with embedded data",
                **kwargs
            ),
            index_name=self.index_name
        )