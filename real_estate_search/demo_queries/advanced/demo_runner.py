"""
Demo runner for advanced search queries.

This module orchestrates the execution of advanced search demos,
coordinating between search builders, executors, and display services.
"""

from typing import Optional, List
from elasticsearch import Elasticsearch
import logging

from ..property.models import PropertySearchResult
from ..result_models import (
    WikipediaSearchResult, MixedEntityResult
)
from .semantic_search import SemanticSearchBuilder
from .multi_entity_search import MultiEntitySearchBuilder
from .wikipedia_search import WikipediaSearchBuilder
from .search_executor import AdvancedSearchExecutor

logger = logging.getLogger(__name__)


class AdvancedDemoRunner:
    """Orchestrates advanced search demonstrations."""
    
    def __init__(self, es_client: Elasticsearch):
        """
        Initialize the demo runner.
        
        Args:
            es_client: Elasticsearch client instance
        """
        self.es_client = es_client
        self.semantic_builder = SemanticSearchBuilder()
        self.multi_builder = MultiEntitySearchBuilder()
        self.wiki_builder = WikipediaSearchBuilder()
        self.executor = AdvancedSearchExecutor(es_client)
    
    def run_semantic_search(
        self,
        reference_property_id: Optional[str] = None,
        size: int = 10
    ) -> PropertySearchResult:
        """
        Run semantic similarity search demo.
        
        Args:
            reference_property_id: Property to find similar ones to
            size: Number of similar properties to return
            
        Returns:
            PropertySearchResult with semantically similar properties
        """
        # Get reference property
        reference = None
        if reference_property_id:
            reference = self.executor.get_reference_property(reference_property_id)
        else:
            # Get random property if not specified
            reference = self.executor.get_random_property()
            if reference:
                reference_property_id = reference.listing_id
        
        if not reference:
            # Return empty result if no reference found
            return PropertySearchResult(
                query_name="Semantic Similarity Search",
                query_description="No reference property found with embedding",
                execution_time_ms=0,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl={"error": "No reference property found"}
            )
        
        # Build similarity search query
        search_request = self.semantic_builder.build_similarity_search(
            reference_embedding=reference.embedding,
            reference_property_id=reference_property_id,
            size=size
        )
        
        # Execute search
        response = self.executor.execute_semantic(search_request, reference)
        
        # Don't display anything here - let commands.py handle all display
        # The result object contains everything needed for display
        
        # Format query name with reference info
        addr = reference.address
        street = addr.street or 'Unknown'
        city = addr.city or 'Unknown'
        price_fmt = f"${reference.price:,.0f}" if reference.price else "Unknown"
        
        query_name = f"Semantic Similarity Search - Finding properties similar to: {street}, {city} ({reference.display_property_type}, {price_fmt})"
        
        # Return formatted result
        return PropertySearchResult(
            query_name="Demo 6: " + query_name,
            query_description=f"Finds properties semantically similar to reference property {reference_property_id} using AI embeddings and vector similarity",
            execution_time_ms=response.execution_time_ms,
            total_hits=response.total_hits,
            returned_hits=len(response.results),
            results=response.results,
            query_dsl=search_request.query,
            es_features=[
                "KNN Search - K-nearest neighbors for efficient vector similarity search",
                "Dense Vectors - 1024-dimensional embeddings for semantic understanding (voyage-3 model)",
                "Cosine Similarity - Vector distance metric for finding similar properties",
                "Function Score Query - Random sampling to find reference property",
                "Bool Query - Exclude reference property from results",
                "Vector Search at Scale - Efficient similarity search on large datasets"
            ],
            indexes_used=[
                "properties index - Real estate listings with AI embeddings",
                f"Searching for {size} properties most similar to reference property"
            ]
        )
    
    def run_multi_entity_search(
        self,
        query_text: str = "historic downtown",
        size: int = 5
    ) -> MixedEntityResult:
        """
        Run multi-entity combined search demo.
        
        Args:
            query_text: Search query text
            size: Number of results per entity type
            
        Returns:
            MixedEntityResult with mixed entity results
        """
        # Build multi-index search request
        search_request = self.multi_builder.build_multi_index_search(
            query_text=query_text,
            size_per_type=size
        )
        
        # Execute search
        response = self.executor.execute_multi_entity(search_request)
        
        # Don't display anything here - let commands.py handle all display
        # The result object contains everything needed for display
        
        # Return formatted result
        return MixedEntityResult(
            query_name=f"Demo 7: Multi-Entity Search - '{query_text}'",
            query_description=f"Unified search across properties, neighborhoods, and Wikipedia articles for '{query_text}', combining results from multiple data sources",
            execution_time_ms=response.execution_time_ms,
            total_hits=response.total_hits,
            returned_hits=len(response.property_results) + len(response.wikipedia_results) + len(response.neighborhood_results),
            property_results=response.property_results,
            wikipedia_results=response.wikipedia_results,
            neighborhood_results=response.neighborhood_results,
            query_dsl=search_request.query,
            es_features=[
                "Multi-Index Search - Query multiple indices in single request",
                "Cross-Index Ranking - Unified relevance scoring across different entity types",
                "Field Boosting - Weight different fields by importance (title^3, description^2)",
                "Index Aggregation - Count results by source index",
                "Highlighting - Show matching content snippets",
                "Fuzzy Matching - Handle typos with AUTO fuzziness"
            ],
            indexes_used=[
                "properties index - Real estate property listings",
                "neighborhoods index - Neighborhood demographics and descriptions",
                "wikipedia index - Geographic Wikipedia articles",
                f"Searching {', '.join(search_request.indices)} indices simultaneously"
            ]
        )
    
    def run_wikipedia_search(
        self,
        city: Optional[str] = "San Francisco",
        state: Optional[str] = "CA",
        topics: Optional[List[str]] = None,
        size: int = 10
    ) -> WikipediaSearchResult:
        """
        Run Wikipedia article search demo.
        
        Args:
            city: Filter by city
            state: Filter by state
            topics: Filter by topics/categories
            size: Number of results
            
        Returns:
            WikipediaSearchResult with Wikipedia articles
        """
        # Build Wikipedia search request
        search_request = self.wiki_builder.build_location_search(
            city=city,
            state=state,
            topics=topics,
            size=size
        )
        
        # Execute search
        response = self.executor.execute_wikipedia(search_request)
        
        # Don't display anything here - let commands.py handle all display
        # The result object contains everything needed for display
        
        # Additional searches for neighborhood associations
        if city:
            # Search for articles with neighborhood associations
            neighborhood_request = self.wiki_builder.build_neighborhood_association_search(
                city=city,
                state=state,
                size=10
            )
            
            try:
                neighborhood_response = self.executor.execute_wikipedia(neighborhood_request)
                if neighborhood_response.results:
                    # Convert results to dict format for display
                    articles = []
                    for article in neighborhood_response.results:
                        articles.append({
                            'title': article.title,
                            'city': article.city,
                            'state': article.state,
                            'neighborhood_names': [],  # Would need to be added to model
                            'neighborhood_ids': []
                        })
                    # Don't display - result object contains all data
                    pass
            except Exception as e:
                logger.error(f"Error searching for neighborhood associations: {e}")
            
            # Search for specific neighborhood (Temescal)
            logger.info("Searching for Temescal Neighborhood")
            
            temescal_request = self.wiki_builder.build_specific_neighborhood_search(
                neighborhood_name="Temescal",
                neighborhood_id="oak-temescal-006",
                size=5
            )
            
            try:
                temescal_response = self.executor.execute_wikipedia(temescal_request)
                if temescal_response.results:
                    # Display Temescal results
                    pass  # Display logic could be added here
            except Exception as e:
                logger.error(f"Error searching for Temescal: {e}")
        
        # Return formatted result
        # Build descriptive text based on what we're searching for
        if topics:
            search_desc = f"Searches Wikipedia articles about {', '.join(topics)} in {city}, {state}"
            filter_desc = f"Filtering for articles in {city}, {state} about {', '.join(topics)}"
        else:
            search_desc = f"Searches all Wikipedia articles in {city}, {state} with geographic filtering"
            filter_desc = f"Filtering for all articles with location data in {city}, {state}"
        
        return WikipediaSearchResult(
            query_name=f"Demo 8: Wikipedia Location & Topic Search",
            query_description=f"{search_desc}, demonstrating complex filtering and boosting strategies",
            execution_time_ms=response.execution_time_ms,
            total_hits=response.total_hits,
            returned_hits=len(response.results),
            results=response.results,
            query_dsl=search_request.query,
            es_features=[
                "Complex Bool Query - Combining must, filter, and should clauses",
                "Query vs Filter Context - Scoring vs non-scoring clauses",
                "Nested Bool Queries - OR conditions within AND logic",
                "Exists Query - Filter documents with specific fields",
                "Multi-Field Sorting - Primary (_score) and secondary (quality) sorts",
                "Boosting Strategies - Prefer high-quality and comprehensive articles",
                "Field-Specific Highlighting - Different fragment sizes per field"
            ],
            indexes_used=[
                "wikipedia index - Curated Wikipedia articles with location data",
                filter_desc
            ]
        )


def demo_semantic_search(
    es_client: Elasticsearch,
    reference_property_id: Optional[str] = None,
    size: int = 10
) -> PropertySearchResult:
    """
    Demo 6: Semantic similarity search using embeddings.
    
    Finds properties similar to a reference property using vector embeddings,
    demonstrating AI-powered semantic search capabilities.
    
    Args:
        es_client: Elasticsearch client
        reference_property_id: Property to find similar ones to
        size: Number of similar properties to return
        
    Returns:
        PropertySearchResult with semantically similar properties
    """
    runner = AdvancedDemoRunner(es_client)
    return runner.run_semantic_search(reference_property_id, size)


def demo_multi_entity_search(
    es_client: Elasticsearch,
    query_text: str = "historic downtown",
    size: int = 5
) -> MixedEntityResult:
    """
    Demo 7: Multi-entity combined search across different indices.
    
    Searches across properties, neighborhoods, and Wikipedia articles
    to provide comprehensive results from multiple data sources.
    
    Args:
        es_client: Elasticsearch client
        query_text: Search query text
        size: Number of results per entity type
        
    Returns:
        MixedEntityResult with mixed entity results
    """
    runner = AdvancedDemoRunner(es_client)
    return runner.run_multi_entity_search(query_text, size)


def demo_wikipedia_search(
    es_client: Elasticsearch,
    city: Optional[str] = "San Francisco",
    state: Optional[str] = "CA",
    topics: Optional[List[str]] = None,
    size: int = 10
) -> WikipediaSearchResult:
    """
    Demo 8: Wikipedia article search with location filtering.
    
    Searches Wikipedia articles with geographic and topical filters,
    demonstrating complex query construction.
    
    Args:
        es_client: Elasticsearch client
        city: Filter by city
        state: Filter by state
        topics: Filter by topics/categories
        size: Number of results
        
    Returns:
        WikipediaSearchResult with Wikipedia articles
    """
    runner = AdvancedDemoRunner(es_client)
    return runner.run_wikipedia_search(city, state, topics, size)