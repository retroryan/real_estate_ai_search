"""
Refactored demo queries with Pydantic models and comprehensive Elasticsearch query documentation.

This module demonstrates best practices for:
1. Type-safe data handling with Pydantic
2. Clear query documentation explaining Elasticsearch concepts
3. Proper error handling and logging
4. Modular query construction

ELASTICSEARCH CONCEPTS DEMONSTRATED:
- Multi-index queries: Searching across properties, neighborhoods, and wikipedia indices
- Document relationships: Using IDs to link documents across indices
- Query DSL: Various query types (term, match, function_score, bool)
- Source filtering: Optimizing network traffic by selecting specific fields
- Aggregations: Getting statistics about result sets
- Scoring: Understanding and using relevance scores
"""

from typing import Dict, Any, Optional, List, Tuple
from elasticsearch import Elasticsearch
import logging
import time

from .models import DemoQueryResult
from .models_enhanced import (
    PropertyEntity,
    NeighborhoodEntity, 
    WikipediaEntity,
    ElasticsearchHit,
    EntityType,
    RelationshipType,
    QueryContext,
    SearchResult
)

logger = logging.getLogger(__name__)


class RelationshipQueryBuilder:
    """
    Builder class for constructing relationship queries between entities.
    
    This class encapsulates the logic for building Elasticsearch queries
    that traverse relationships between properties, neighborhoods, and Wikipedia articles.
    """
    
    def __init__(self, es_client: Elasticsearch):
        """Initialize with Elasticsearch client."""
        self.es_client = es_client
    
    def get_random_property_query(self) -> Dict[str, Any]:
        """
        Build a query to get a random property with neighborhood relationship.
        
        ELASTICSEARCH CONCEPTS:
        1. FUNCTION SCORE QUERY: Modifies document scores using functions
           - Used here with random_score to get random documents
           - Useful for sampling, A/B testing, or demonstrations
        
        2. EXISTS QUERY: Filters documents where a field exists
           - Ensures we only get properties with neighborhood_id
           - More efficient than checking for non-null values
        
        3. RANDOM SCORING: Each query execution returns different results
           - Seed parameter makes randomness reproducible if needed
           - Without seed, results are truly random each time
        
        Returns:
            Elasticsearch query DSL for random property selection
        """
        return {
            "query": {
                "function_score": {
                    # Base query: only properties with neighborhood relationships
                    "query": {
                        "exists": {
                            "field": "neighborhood_id"
                        }
                    },
                    # Apply random scoring to get different results each time
                    "random_score": {
                        # Optional: use seed for reproducible randomness
                        # "seed": 42
                    },
                    # How to combine query score with function score
                    "boost_mode": "replace"  # Ignore original score, use only random
                }
            },
            "size": 1,  # Only need one random document
            "_source": True  # Fetch all fields for the property
        }
    
    def get_property_by_id_query(self, property_id: str) -> Dict[str, Any]:
        """
        Build a query to get a specific property by ID.
        
        ELASTICSEARCH CONCEPTS:
        1. TERM QUERY: Exact match on a keyword field
           - Used for ID lookups (no analysis performed)
           - Faster than match query for exact values
        
        2. _ID vs CUSTOM ID FIELD:
           - Could use GET API with document _id
           - Using term query on listing_id allows same pattern for all lookups
        
        Args:
            property_id: The property listing ID
            
        Returns:
            Elasticsearch query DSL for specific property
        """
        return {
            "query": {
                "term": {
                    "listing_id": property_id
                }
            },
            "size": 1,
            "_source": True
        }
    
    def get_neighborhood_by_id_query(self, neighborhood_id: str) -> Dict[str, Any]:
        """
        Build a query to get a neighborhood by ID.
        
        ELASTICSEARCH CONCEPTS:
        1. CROSS-INDEX RELATIONSHIPS:
           - Properties store neighborhood_id as foreign key
           - This query retrieves the referenced neighborhood document
           - Similar to SQL JOIN but requires separate query
        
        2. DENORMALIZATION TRADEOFFS:
           - Could embed neighborhood data in each property (faster reads)
           - Separate documents allow independent updates (better data integrity)
        
        Args:
            neighborhood_id: The neighborhood ID from property
            
        Returns:
            Elasticsearch query DSL for neighborhood lookup
        """
        return {
            "query": {
                "term": {
                    "neighborhood_id": neighborhood_id
                }
            },
            "size": 1,
            "_source": True  # Get all neighborhood fields
        }
    
    def get_wikipedia_by_id_query(self, page_id: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Build a query to get a Wikipedia article by page ID.
        
        ELASTICSEARCH CONCEPTS:
        1. SOURCE FILTERING:
           - _source parameter limits returned fields
           - Reduces network traffic for large documents
           - Wikipedia articles can be 100KB+ each
        
        2. FIELD SELECTION STRATEGY:
           - Full content only when needed (expensive)
           - Summary fields for display (lightweight)
           - Metadata for relationship mapping
        
        Args:
            page_id: Wikipedia page ID
            fields: Optional list of fields to return
            
        Returns:
            Elasticsearch query DSL for Wikipedia article
        """
        query = {
            "query": {
                "term": {
                    "page_id": page_id
                }
            },
            "size": 1
        }
        
        # Optimize field selection based on use case
        if fields:
            query["_source"] = fields
        else:
            # Default: exclude large full_content field
            query["_source"] = {
                "excludes": ["full_content", "embedding"]
            }
        
        return query
    
    def get_properties_by_neighborhood_query(
        self, 
        neighborhood_id: str, 
        max_properties: int = 10,
        sort_by: str = "price"
    ) -> Dict[str, Any]:
        """
        Build a query to get all properties in a neighborhood.
        
        ELASTICSEARCH CONCEPTS:
        1. REVERSE RELATIONSHIP QUERY:
           - Finding all properties that reference a neighborhood
           - Like SQL: SELECT * FROM properties WHERE neighborhood_id = X
        
        2. SORTING:
           - Default relevance score not meaningful for term queries
           - Sort by price, date, or other fields for better UX
        
        3. SIZE LIMITING:
           - Prevent returning thousands of documents
           - Use pagination for large result sets in production
        
        Args:
            neighborhood_id: The neighborhood to search for
            max_properties: Maximum number of properties to return
            sort_by: Field to sort results by
            
        Returns:
            Elasticsearch query DSL for properties in neighborhood
        """
        return {
            "query": {
                "term": {
                    "neighborhood_id": neighborhood_id
                }
            },
            "size": max_properties,
            "sort": [
                {sort_by: {"order": "desc"}}  # Most expensive first for demo
            ],
            "_source": {
                # Only get fields needed for display
                "includes": [
                    "listing_id", "address", "price", "property_type",
                    "bedrooms", "bathrooms", "square_feet", "amenities"
                ]
            }
        }
    
    def get_wikipedia_by_location_query(
        self,
        city: str,
        state: str,
        max_articles: int = 5
    ) -> Dict[str, Any]:
        """
        Build a query to find Wikipedia articles about a location.
        
        ELASTICSEARCH CONCEPTS:
        1. BOOL QUERY:
           - Combines multiple conditions with AND/OR logic
           - must: All conditions must match (AND)
           - should: At least one should match (OR)
           - filter: Like must but doesn't affect score
        
        2. MATCH vs TERM:
           - match: Analyzes text, handles variations
           - term: Exact match, no analysis
           - Use match for city names (handles case, spelling)
        
        3. SCORING BOOST:
           - title^2 gives title matches 2x weight
           - Prioritizes articles with location in title
        
        Args:
            city: City name to search for
            state: State abbreviation
            max_articles: Maximum articles to return
            
        Returns:
            Elasticsearch query DSL for location-based Wikipedia search
        """
        return {
            "query": {
                "bool": {
                    # Both city and state should match
                    "must": [
                        {
                            "match": {
                                "best_city": {
                                    "query": city,
                                    "operator": "and"  # All terms must match
                                }
                            }
                        },
                        {
                            "term": {
                                "best_state": state  # Exact match for state code
                            }
                        }
                    ],
                    # Boost articles with location in title
                    "should": [
                        {
                            "match": {
                                "title": {
                                    "query": city,
                                    "boost": 2.0  # Double weight for title matches
                                }
                            }
                        }
                    ]
                }
            },
            "size": max_articles,
            "_source": {
                # Exclude large fields for performance
                "excludes": ["full_content", "embedding"]
            },
            # Sort by relevance score (default)
            "sort": ["_score"]
        }


class PropertyNeighborhoodWikiDemo:
    """
    Refactored demo class using Pydantic models for type safety.
    
    This class demonstrates best practices for:
    - Handling Elasticsearch responses with type safety
    - Building complex multi-step queries
    - Managing relationships between entities
    - Error handling and logging
    """
    
    def __init__(self, es_client: Elasticsearch):
        """Initialize with Elasticsearch client and query builder."""
        self.es_client = es_client
        self.query_builder = RelationshipQueryBuilder(es_client)
    
    def execute_query_with_timing(
        self, 
        index: str, 
        query: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], int]:
        """
        Execute a query and measure execution time.
        
        Args:
            index: Index to search
            query: Query DSL
            
        Returns:
            Tuple of (response dict, execution time in ms)
        """
        start_time = time.time()
        try:
            response = self.es_client.search(index=index, body=query)
            execution_time = int((time.time() - start_time) * 1000)
            return response, execution_time
        except Exception as e:
            logger.error(f"Query execution error on index {index}: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            return None, execution_time
    
    def get_property_with_full_context(
        self,
        property_id: Optional[str] = None
    ) -> DemoQueryResult:
        """
        Get a property with its neighborhood and Wikipedia context.
        
        QUERY FLOW:
        1. Get property (random or specific)
        2. Use property.neighborhood_id to get neighborhood
        3. Use neighborhood.wikipedia_correlations to get Wikipedia articles
        4. Combine all data with relationship metadata
        
        This demonstrates a common pattern in Elasticsearch:
        - Following references between documents (like foreign keys)
        - Enriching results with related data
        - Building complete context from multiple indices
        
        Args:
            property_id: Optional specific property ID
            
        Returns:
            DemoQueryResult with typed entities
        """
        results: List[SearchResult] = []
        query_context = QueryContext(
            query_type="property_with_context",
            parent_entity=None,
            relationship_chain=[],
            execution_time_ms=0
        )
        
        # Step 1: Get property
        if property_id:
            query = self.query_builder.get_property_by_id_query(property_id)
            query_context.add_relationship(f"property_lookup:{property_id}")
        else:
            query = self.query_builder.get_random_property_query()
            query_context.add_relationship("random_property_selection")
        
        response, exec_time = self.execute_query_with_timing("properties", query)
        query_context.execution_time_ms += exec_time
        
        if not response or not response['hits']['hits']:
            logger.warning("No property found")
            return DemoQueryResult(
                query_name="Property with Full Context",
                execution_time_ms=query_context.execution_time_ms,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=query
            )
        
        # Convert to typed entity
        hit = ElasticsearchHit(**response['hits']['hits'][0])
        property_entity = hit.to_entity()
        
        if not isinstance(property_entity, PropertyEntity):
            logger.error("Invalid property entity type")
            return DemoQueryResult(
                query_name="Property with Full Context",
                execution_time_ms=query_context.execution_time_ms,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=query
            )
        
        results.append(SearchResult(entity=property_entity))
        query_context.parent_entity = property_entity
        
        # Step 2: Get neighborhood if property has neighborhood_id
        if property_entity.neighborhood_id:
            query = self.query_builder.get_neighborhood_by_id_query(
                property_entity.neighborhood_id
            )
            query_context.add_relationship(f"neighborhood_lookup:{property_entity.neighborhood_id}")
            
            response, exec_time = self.execute_query_with_timing("neighborhoods", query)
            query_context.execution_time_ms += exec_time
            
            if response and response['hits']['hits']:
                hit = ElasticsearchHit(**response['hits']['hits'][0])
                neighborhood_entity = hit.to_entity()
                
                if isinstance(neighborhood_entity, NeighborhoodEntity):
                    results.append(SearchResult(entity=neighborhood_entity))
                    query_context.parent_entity = neighborhood_entity
                    
                    # Step 3: Get Wikipedia articles from neighborhood correlations
                    # Primary article
                    if neighborhood_entity.primary_wiki_article:
                        wiki_corr = neighborhood_entity.primary_wiki_article
                        query = self.query_builder.get_wikipedia_by_id_query(wiki_corr.page_id)
                        query_context.add_relationship(f"primary_wiki:{wiki_corr.page_id}")
                        
                        response, exec_time = self.execute_query_with_timing("wikipedia", query)
                        query_context.execution_time_ms += exec_time
                        
                        if response and response['hits']['hits']:
                            hit = ElasticsearchHit(**response['hits']['hits'][0])
                            wiki_entity = hit.to_entity()
                            
                            if isinstance(wiki_entity, WikipediaEntity):
                                # Add relationship metadata
                                wiki_entity._entity_type = EntityType.WIKIPEDIA_PRIMARY
                                wiki_entity._relationship = RelationshipType.PRIMARY_ARTICLE
                                wiki_entity._confidence = wiki_corr.confidence
                                results.append(SearchResult(entity=wiki_entity))
                    
                    # Related articles
                    for wiki_corr in neighborhood_entity.related_wiki_articles[:3]:
                        query = self.query_builder.get_wikipedia_by_id_query(
                            wiki_corr.page_id,
                            fields=["page_id", "title", "summary", "city", "state"]
                        )
                        query_context.add_relationship(f"related_wiki:{wiki_corr.page_id}")
                        
                        response, exec_time = self.execute_query_with_timing("wikipedia", query)
                        query_context.execution_time_ms += exec_time
                        
                        if response and response['hits']['hits']:
                            hit = ElasticsearchHit(**response['hits']['hits'][0])
                            wiki_entity = hit.to_entity()
                            
                            if isinstance(wiki_entity, WikipediaEntity):
                                # Add relationship metadata
                                wiki_entity._entity_type = EntityType.WIKIPEDIA_RELATED
                                wiki_entity._relationship = wiki_corr.relationship
                                wiki_entity._confidence = wiki_corr.confidence
                                results.append(SearchResult(entity=wiki_entity))
        
        # Build query name with context
        query_name = f"Property with Full Context: {property_entity.listing_id}"
        if query_context.parent_entity and isinstance(query_context.parent_entity, NeighborhoodEntity):
            query_name += f" in {query_context.parent_entity.name}"
        
        # Convert SearchResult objects to dicts for backward compatibility
        result_dicts = []
        for result in results:
            entity_dict = result.entity.model_dump(exclude_none=True)
            result_dicts.append(entity_dict)
        
        return DemoQueryResult(
            query_name=query_name,
            execution_time_ms=query_context.execution_time_ms,
            total_hits=len(results),
            returned_hits=len(results),
            results=result_dicts,
            query_dsl={
                "description": "Multi-step relationship traversal query",
                "relationship_chain": query_context.relationship_chain,
                "execution_time_ms": query_context.execution_time_ms
            }
        )


def demo_property_with_full_context_refactored(
    es_client: Elasticsearch,
    property_id: Optional[str] = None
) -> DemoQueryResult:
    """
    Refactored demo using Pydantic models for type safety.
    
    This function demonstrates:
    - Type-safe entity handling
    - Clear relationship traversal
    - Comprehensive error handling
    - Performance tracking
    
    Args:
        es_client: Elasticsearch client
        property_id: Optional property ID
        
    Returns:
        DemoQueryResult with strongly-typed entities
    """
    demo = PropertyNeighborhoodWikiDemo(es_client)
    return demo.get_property_with_full_context(property_id)