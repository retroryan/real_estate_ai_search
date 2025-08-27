"""
Refactored demo queries for property-neighborhood-Wikipedia relationships.

This module demonstrates advanced Elasticsearch patterns for entity relationships:

CORE CONCEPTS:
1. CROSS-INDEX RELATIONSHIPS: Joining data across multiple indices using IDs
2. MULTI-STEP QUERIES: Building context through sequential queries
3. MSEARCH API: Executing multiple queries efficiently in one request
4. TYPE SAFETY: Using Pydantic models to ensure data integrity
5. COMPREHENSIVE DOCUMENTATION: Each query explains what and why

ARCHITECTURAL PATTERNS:
- Repository Pattern: Query builders encapsulate Elasticsearch logic
- Entity Pattern: Strongly-typed models for each data type
- Builder Pattern: Composable query construction
- Result Pattern: Type-safe result handling with proper validation

PERFORMANCE OPTIMIZATIONS:
- Source filtering to reduce network overhead
- Batch queries with msearch when possible
- Appropriate query types for each use case
- Caching strategies for repeated lookups
"""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple, Union
from elasticsearch import Elasticsearch

from .models import DemoQueryResult
from .base_models import (
    PropertyListing,
    Neighborhood,
    WikipediaArticle,
    SearchHit,
    SearchRequest,
    SearchResponse,
    EntityType,
    IndexName,
    QueryType,
    Address,
    PropertyFeatures,
    Demographics
)

logger = logging.getLogger(__name__)


# ============================================================================
# QUERY BUILDERS
# ============================================================================

class PropertyNeighborhoodQueryBuilder:
    """
    Query builder for property-neighborhood-Wikipedia relationships.
    
    This class encapsulates all the Elasticsearch query logic, providing
    a clean interface for building complex multi-index queries.
    
    DESIGN PRINCIPLES:
    - Single Responsibility: Each method builds one type of query
    - Open/Closed: Easy to extend with new query types
    - Interface Segregation: Methods grouped by entity type
    - Dependency Inversion: Depends on abstractions (SearchRequest)
    """
    
    @staticmethod
    def random_property_with_neighborhood() -> SearchRequest:
        """
        Build query to get a random property that has a neighborhood.
        
        ELASTICSEARCH CONCEPTS:
        
        1. FUNCTION_SCORE QUERY:
           - Modifies document scores using mathematical functions
           - Used here with random_score for sampling
           - Useful for A/B testing, demos, and data exploration
        
        2. EXISTS QUERY:
           - Filters documents where a field exists and has a non-null value
           - More efficient than range queries or script queries
           - Perfect for checking foreign key relationships
        
        3. RANDOM SCORING:
           - Each query execution returns different results
           - Optional seed parameter for reproducible randomness
           - Uniform distribution across all matching documents
        
        PERFORMANCE NOTES:
        - Random scoring has O(n) complexity where n = matching docs
        - Use small size parameter to limit processing
        - Consider caching if used frequently with same seed
        """
        return SearchRequest(
            index=IndexName.PROPERTIES.value,
            query={
                "function_score": {
                    "query": {
                        "exists": {
                            "field": "neighborhood_id"
                        }
                    },
                    "random_score": {
                        # Seed makes randomness reproducible for testing
                        # Remove seed for true randomness in production
                        "seed": 42,
                        "field": "_seq_no"  # Use document sequence number for better distribution
                    },
                    "boost_mode": "replace"  # Use only random score, ignore query score
                }
            },
            size=1,
            _source=True  # Get all fields for demonstration
        )
    
    @staticmethod
    def property_by_id(property_id: str) -> SearchRequest:
        """
        Build query to get a specific property by listing ID.
        
        ELASTICSEARCH CONCEPTS:
        
        1. TERM QUERY VS GET API:
           - Term query allows consistent pattern across all lookups
           - GET API is faster for document _id lookups
           - Term query works with any field, not just _id
        
        2. KEYWORD FIELDS:
           - listing_id.keyword ensures exact matching
           - No analysis performed (preserves case, punctuation)
           - Faster than analyzed text fields
        
        3. SOURCE FILTERING:
           - Could use _source to limit returned fields
           - Full document returned here for demo purposes
           - Production should only fetch needed fields
        """
        return SearchRequest(
            index=IndexName.PROPERTIES.value,
            query={
                "term": {
                    "listing_id.keyword": property_id
                }
            },
            size=1,
            _source=True
        )
    
    @staticmethod
    def neighborhood_by_id(neighborhood_id: str) -> SearchRequest:
        """
        Build query to get neighborhood by ID.
        
        ELASTICSEARCH CONCEPTS:
        
        1. FOREIGN KEY PATTERN:
           - Properties store neighborhood_id as reference
           - This query retrieves the referenced document
           - Similar to SQL JOIN but requires separate query
        
        2. DENORMALIZATION TRADEOFFS:
           - Could embed neighborhood in each property (faster reads)
           - Separate documents allow independent updates
           - Balance between query performance and data consistency
        
        3. CACHING OPPORTUNITY:
           - Neighborhoods change rarely
           - Good candidate for application-level caching
           - Reduces unnecessary Elasticsearch queries
        """
        return SearchRequest(
            index=IndexName.NEIGHBORHOODS.value,
            query={
                "term": {
                    "neighborhood_id.keyword": neighborhood_id
                }
            },
            size=1,
            _source=True
        )
    
    @staticmethod
    def neighborhood_by_name(name: str) -> SearchRequest:
        """
        Build query to find neighborhood by name.
        
        ELASTICSEARCH CONCEPTS:
        
        1. MATCH QUERY:
           - Analyzes the search text (lowercase, stemming)
           - Handles variations in spelling and case
           - Better for user-provided input than term query
        
        2. FUZZY MATCHING:
           - Could add fuzziness parameter for typo tolerance
           - fuzziness: "AUTO" adjusts based on term length
           - Useful for user interfaces
        
        3. PHRASE MATCHING:
           - Could use match_phrase for exact ordering
           - "Pacific Heights" vs "Heights Pacific"
           - Trade-off between precision and recall
        """
        return SearchRequest(
            index=IndexName.NEIGHBORHOODS.value,
            query={
                "match": {
                    "name": {
                        "query": name,
                        "operator": "and",  # All terms must match
                        "fuzziness": "AUTO"  # Handle typos automatically
                    }
                }
            },
            size=1,
            _source=True
        )
    
    @staticmethod
    def properties_in_neighborhood(
        neighborhood_id: str,
        limit: int = 10,
        sort_field: str = "price"
    ) -> SearchRequest:
        """
        Build query to find all properties in a neighborhood.
        
        ELASTICSEARCH CONCEPTS:
        
        1. REVERSE LOOKUP:
           - Finding all documents that reference another document
           - Like SQL: WHERE foreign_key = value
           - Can be expensive with many matches
        
        2. SORTING:
           - Default relevance score meaningless for term queries
           - Sort by price, date, or other meaningful fields
           - Use desc for high-to-low, asc for low-to-high
        
        3. PAGINATION:
           - Size parameter limits returned documents
           - Use from parameter for pagination
           - Consider search_after for deep pagination
        
        4. SOURCE FILTERING:
           - Only return fields needed for display
           - Reduces network traffic significantly
           - Critical for performance with large documents
        """
        return SearchRequest(
            index=IndexName.PROPERTIES.value,
            query={
                "term": {
                    "neighborhood_id.keyword": neighborhood_id
                }
            },
            size=limit,
            sort=[
                {sort_field: {"order": "desc", "missing": "_last"}}
            ],
            _source={
                "includes": [
                    "listing_id", "address", "price", "property_type",
                    "bedrooms", "bathrooms", "square_feet", "amenities"
                ]
            }
        )
    
    @staticmethod
    def wikipedia_by_page_id(
        page_id: str,
        exclude_content: bool = True
    ) -> SearchRequest:
        """
        Build query to get Wikipedia article by page ID.
        
        ELASTICSEARCH CONCEPTS:
        
        1. LARGE DOCUMENT HANDLING:
           - Wikipedia articles can be 100KB+ each
           - full_content field contains entire HTML
           - Exclude large fields unless needed
        
        2. SOURCE FILTERING PATTERNS:
           - includes: Whitelist specific fields
           - excludes: Blacklist specific fields
           - Can combine both for complex filtering
        
        3. FIELD RETRIEVAL STRATEGIES:
           - Metadata only: Fast, for relationship mapping
           - Summary only: Medium, for display
           - Full content: Slow, for detailed analysis
        """
        source_filter = {
            "excludes": ["full_content", "embedding"]
        } if exclude_content else True
        
        return SearchRequest(
            index=IndexName.WIKIPEDIA.value,
            query={
                "term": {
                    "page_id.keyword": page_id
                }
            },
            size=1,
            _source=source_filter
        )
    
    @staticmethod
    def wikipedia_by_location(
        city: str,
        state: str,
        limit: int = 5
    ) -> SearchRequest:
        """
        Build query to find Wikipedia articles about a location.
        
        ELASTICSEARCH CONCEPTS:
        
        1. BOOL QUERY STRUCTURE:
           - must: All conditions must match (AND)
           - should: At least one should match (OR)  
           - filter: Must match but doesn't affect score
           - must_not: Must not match (NOT)
        
        2. SCORING VS FILTERING:
           - Queries in 'must' and 'should' affect relevance score
           - Queries in 'filter' don't affect score (faster)
           - Use filter for yes/no conditions (state)
           - Use must/should for relevance (city mentions)
        
        3. FIELD BOOSTING:
           - title^2 gives title matches double weight
           - Prioritizes articles with city in title
           - Can chain multiple fields with different boosts
        
        4. MATCH VS TERM:
           - match: Analyzed, handles variations
           - term: Exact match only
           - Use match for city names (case-insensitive)
           - Use term for state codes (exact match)
        """
        return SearchRequest(
            index=IndexName.WIKIPEDIA.value,
            query={
                "bool": {
                    "must": [
                        {
                            "match": {
                                "best_city": {
                                    "query": city,
                                    "operator": "and"
                                }
                            }
                        }
                    ],
                    "filter": [
                        {
                            "term": {
                                "best_state.keyword": state
                            }
                        }
                    ],
                    "should": [
                        {
                            "match": {
                                "title": {
                                    "query": city,
                                    "boost": 2.0
                                }
                            }
                        },
                        {
                            "match": {
                                "summary": city
                            }
                        }
                    ],
                    "minimum_should_match": 0  # Should clauses are optional
                }
            },
            size=limit,
            sort=["_score"],  # Sort by relevance
            _source={
                "excludes": ["full_content", "embedding"]
            }
        )


# ============================================================================
# DEMO IMPLEMENTATIONS
# ============================================================================

class PropertyNeighborhoodWikiDemo:
    """
    Demo implementation with type safety and comprehensive documentation.
    
    This class demonstrates best practices for:
    - Building complex multi-step queries
    - Handling Elasticsearch responses with type safety
    - Managing relationships between entities
    - Performance monitoring and optimization
    - Error handling and logging
    """
    
    def __init__(self, es_client: Elasticsearch):
        """Initialize with Elasticsearch client."""
        self.es_client = es_client
        self.query_builder = PropertyNeighborhoodQueryBuilder()
    
    def execute_search(
        self,
        request: SearchRequest
    ) -> Tuple[Optional[SearchResponse], int]:
        """
        Execute a search request and measure performance.
        
        Args:
            request: Search request configuration
            
        Returns:
            Tuple of (response, execution_time_ms)
        """
        start_time = time.time()
        
        try:
            response = self.es_client.search(
                index=request.index,
                body=request.to_dict()
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            search_response = SearchResponse.from_elasticsearch(response)
            
            return search_response, execution_time
            
        except Exception as e:
            logger.error(f"Search execution error: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            return None, execution_time
    
    def demo_property_with_full_context(
        self,
        property_id: Optional[str] = None
    ) -> DemoQueryResult:
        """
        Demonstrate property with neighborhood and Wikipedia context.
        
        QUERY FLOW:
        1. Get property (random or specific)
        2. Follow neighborhood_id foreign key
        3. Extract Wikipedia correlations from neighborhood
        4. Fetch Wikipedia articles by page_id
        5. Combine all data with relationship metadata
        
        PERFORMANCE CONSIDERATIONS:
        - Multiple round trips to Elasticsearch (latency accumulates)
        - Could use msearch to parallelize Wikipedia lookups
        - Consider caching neighborhoods (change rarely)
        - Source filtering reduces network overhead
        
        RELATIONSHIP MAPPING:
        Property -> Neighborhood (via neighborhood_id)
        Neighborhood -> Wikipedia (via wikipedia_correlations)
        
        This demonstrates a common pattern in Elasticsearch:
        following references between documents to build context.
        """
        results = []
        total_execution_time = 0
        
        # Step 1: Get property
        if property_id:
            request = self.query_builder.property_by_id(property_id)
            logger.info(f"Getting property by ID: {property_id}")
        else:
            request = self.query_builder.random_property_with_neighborhood()
            logger.info("Getting random property with neighborhood")
        
        response, exec_time = self.execute_search(request)
        total_execution_time += exec_time
        
        if not response or not response.hits:
            logger.warning("No property found")
            return DemoQueryResult(
                query_name="Property with Full Context",
                execution_time_ms=total_execution_time,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=request.to_dict()
            )
        
        # Convert to typed entity
        property_entity = response.to_entities()[0]
        if not isinstance(property_entity, PropertyListing):
            logger.error("Invalid property entity type")
            return DemoQueryResult(
                query_name="Property with Full Context",
                execution_time_ms=total_execution_time,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=request.to_dict()
            )
        
        results.append(property_entity.model_dump(exclude_none=True))
        
        # Step 2: Get neighborhood if property has neighborhood_id
        neighborhood_entity = None
        if property_entity.neighborhood_id:
            logger.info(f"Getting neighborhood: {property_entity.neighborhood_id}")
            request = self.query_builder.neighborhood_by_id(property_entity.neighborhood_id)
            response, exec_time = self.execute_search(request)
            total_execution_time += exec_time
            
            if response and response.hits:
                neighborhood_entity = response.to_entities()[0]
                if isinstance(neighborhood_entity, Neighborhood):
                    # Add entity type for backward compatibility
                    neighborhood_dict = neighborhood_entity.model_dump(exclude_none=True)
                    neighborhood_dict['_entity_type'] = 'neighborhood'
                    results.append(neighborhood_dict)
        
        # Step 3: Get Wikipedia articles from neighborhood correlations
        if neighborhood_entity and isinstance(neighborhood_entity, Neighborhood):
            wiki_corr = neighborhood_entity.wikipedia_correlations
            
            if wiki_corr:
                # Get primary article
                if 'primary_wiki_article' in wiki_corr:
                    primary = wiki_corr['primary_wiki_article']
                    if primary and 'page_id' in primary:
                        logger.info(f"Getting primary Wikipedia article: {primary['page_id']}")
                        request = self.query_builder.wikipedia_by_page_id(primary['page_id'])
                        response, exec_time = self.execute_search(request)
                        total_execution_time += exec_time
                        
                        if response and response.hits:
                            wiki_entity = response.to_entities()[0]
                            if isinstance(wiki_entity, WikipediaArticle):
                                wiki_dict = wiki_entity.model_dump(exclude_none=True)
                                wiki_dict['_entity_type'] = 'wikipedia_primary'
                                wiki_dict['_relationship'] = 'primary_article'
                                wiki_dict['_confidence'] = primary.get('confidence', 0.0)
                                results.append(wiki_dict)
                
                # Get related articles
                if 'related_wiki_articles' in wiki_corr:
                    related_articles = wiki_corr['related_wiki_articles']
                    if isinstance(related_articles, list):
                        for related in related_articles[:3]:  # Limit to 3
                            if related and 'page_id' in related:
                                logger.info(f"Getting related Wikipedia article: {related['page_id']}")
                                request = self.query_builder.wikipedia_by_page_id(
                                    related['page_id'],
                                    exclude_content=True  # Only need metadata
                                )
                                response, exec_time = self.execute_search(request)
                                total_execution_time += exec_time
                                
                                if response and response.hits:
                                    wiki_entity = response.to_entities()[0]
                                    if isinstance(wiki_entity, WikipediaArticle):
                                        wiki_dict = wiki_entity.model_dump(exclude_none=True)
                                        wiki_dict['_entity_type'] = 'wikipedia_related'
                                        wiki_dict['_relationship'] = related.get('relationship', 'related')
                                        wiki_dict['_confidence'] = related.get('confidence', 0.0)
                                        results.append(wiki_dict)
        
        # Build descriptive query name
        query_name = f"Property: {property_entity.address.street if property_entity.address else 'Unknown'}"
        if neighborhood_entity:
            query_name += f" in {neighborhood_entity.name}"
        
        return DemoQueryResult(
            query_name=query_name,
            execution_time_ms=total_execution_time,
            total_hits=len(results),
            returned_hits=len(results),
            results=results,
            query_dsl={
                "description": "Multi-step relationship traversal",
                "execution_time_ms": total_execution_time,
                "steps": [
                    "1. Get property (random or by ID)",
                    "2. Lookup neighborhood by foreign key",
                    "3. Extract Wikipedia correlations",
                    "4. Fetch Wikipedia articles"
                ]
            }
        )
    
    def demo_neighborhood_properties_and_wiki(
        self,
        neighborhood_name: str = "Pacific Heights"
    ) -> DemoQueryResult:
        """
        Demonstrate neighborhood with all its properties and Wikipedia articles.
        
        QUERY FLOW:
        1. Find neighborhood by name (fuzzy matching)
        2. Get all properties in neighborhood (reverse lookup)
        3. Extract Wikipedia correlations from neighborhood
        4. Return combined results
        
        OPTIMIZATION OPPORTUNITIES:
        - Use msearch to parallelize property and Wikipedia lookups
        - Implement pagination for neighborhoods with many properties
        - Cache neighborhood lookups (change rarely)
        - Use aggregations to get property statistics
        """
        results = []
        total_execution_time = 0
        
        # Step 1: Find neighborhood by name
        logger.info(f"Searching for neighborhood: {neighborhood_name}")
        request = self.query_builder.neighborhood_by_name(neighborhood_name)
        response, exec_time = self.execute_search(request)
        total_execution_time += exec_time
        
        if not response or not response.hits:
            logger.warning(f"Neighborhood not found: {neighborhood_name}")
            return DemoQueryResult(
                query_name=f"Neighborhood: {neighborhood_name}",
                execution_time_ms=total_execution_time,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=request.to_dict()
            )
        
        # Get neighborhood entity
        neighborhood_entity = response.to_entities()[0]
        if not isinstance(neighborhood_entity, Neighborhood):
            logger.error("Invalid neighborhood entity type")
            return DemoQueryResult(
                query_name=f"Neighborhood: {neighborhood_name}",
                execution_time_ms=total_execution_time,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=request.to_dict()
            )
        
        neighborhood_dict = neighborhood_entity.model_dump(exclude_none=True)
        neighborhood_dict['_entity_type'] = 'neighborhood'
        results.append(neighborhood_dict)
        
        # Step 2: Get properties in neighborhood
        logger.info(f"Getting properties in neighborhood: {neighborhood_entity.neighborhood_id}")
        request = self.query_builder.properties_in_neighborhood(
            neighborhood_entity.neighborhood_id,
            limit=5
        )
        response, exec_time = self.execute_search(request)
        total_execution_time += exec_time
        
        if response and response.hits:
            for property_entity in response.to_entities():
                if isinstance(property_entity, PropertyListing):
                    prop_dict = property_entity.model_dump(exclude_none=True)
                    prop_dict['_entity_type'] = 'property'
                    prop_dict['_relationship'] = 'in_neighborhood'
                    results.append(prop_dict)
        
        # Step 3: Add Wikipedia correlations (already in neighborhood data)
        wiki_count = 0
        if neighborhood_entity.wikipedia_correlations:
            wiki_corr = neighborhood_entity.wikipedia_correlations
            
            # Primary article
            if 'primary_wiki_article' in wiki_corr:
                primary = wiki_corr['primary_wiki_article']
                if primary:
                    wiki_article = {
                        'page_id': primary.get('page_id'),
                        'title': primary.get('title'),
                        '_entity_type': 'wikipedia',
                        '_relationship': 'primary_article',
                        '_confidence': primary.get('confidence', 0.0)
                    }
                    results.append(wiki_article)
                    wiki_count += 1
            
            # Related articles
            if 'related_wiki_articles' in wiki_corr:
                related = wiki_corr['related_wiki_articles']
                if isinstance(related, list):
                    for article in related[:3]:
                        if article:
                            wiki_article = {
                                'page_id': article.get('page_id'),
                                'title': article.get('title'),
                                '_entity_type': 'wikipedia',
                                '_relationship': article.get('relationship', 'related'),
                                '_confidence': article.get('confidence', 0.0)
                            }
                            results.append(wiki_article)
                            wiki_count += 1
        
        property_count = len([r for r in results if r.get('_entity_type') == 'property'])
        
        return DemoQueryResult(
            query_name=f"{neighborhood_entity.name}: {property_count} properties, {wiki_count} Wikipedia articles",
            execution_time_ms=total_execution_time,
            total_hits=len(results),
            returned_hits=len(results),
            results=results,
            query_dsl={
                "description": "Neighborhood with all related entities",
                "execution_time_ms": total_execution_time
            }
        )
    
    def demo_location_wikipedia_context(
        self,
        city: str = "San Francisco",
        state: str = "CA"
    ) -> DemoQueryResult:
        """
        Demonstrate location-based search across properties and Wikipedia.
        
        MSEARCH OPTIMIZATION:
        - Executes multiple queries in single request
        - Reduces network round trips
        - Parallel execution on Elasticsearch side
        - Better performance for related queries
        
        USE CASES:
        - City overview pages
        - Market analysis by location
        - Historical context for real estate
        - Tourism and relocation guides
        """
        # Build multi-search request
        msearch_body = []
        
        # Properties in location
        msearch_body.extend([
            {"index": IndexName.PROPERTIES.value},
            {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"address.city.keyword": city}},
                            {"term": {"address.state.keyword": state}}
                        ]
                    }
                },
                "size": 5,
                "_source": {
                    "includes": [
                        "listing_id", "address", "price", "property_type",
                        "bedrooms", "bathrooms", "neighborhood_id"
                    ]
                }
            }
        ])
        
        # Wikipedia articles about location
        msearch_body.extend([
            {"index": IndexName.WIKIPEDIA.value},
            {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"best_city": city}}
                        ],
                        "filter": [
                            {"term": {"best_state.keyword": state}}
                        ],
                        "should": [
                            {"match": {"title": {"query": city, "boost": 2.0}}}
                        ]
                    }
                },
                "size": 5,
                "_source": {
                    "excludes": ["full_content", "embedding"]
                }
            }
        ])
        
        try:
            start_time = time.time()
            responses = self.es_client.msearch(body=msearch_body)
            execution_time = int((time.time() - start_time) * 1000)
            
            results = []
            
            # Process property results
            prop_response = responses['responses'][0]
            if 'hits' in prop_response:
                for hit in prop_response['hits']['hits']:
                    prop_dict = hit['_source']
                    prop_dict['_entity_type'] = 'property'
                    results.append(prop_dict)
            
            # Process Wikipedia results
            wiki_response = responses['responses'][1]
            if 'hits' in wiki_response:
                for hit in wiki_response['hits']['hits']:
                    wiki_dict = hit['_source']
                    wiki_dict['_entity_type'] = 'wikipedia'
                    wiki_dict['_relevance'] = 'location_context'
                    results.append(wiki_dict)
            
            return DemoQueryResult(
                query_name=f"Location: {city}, {state}",
                execution_time_ms=execution_time,
                total_hits=len(results),
                returned_hits=len(results),
                results=results,
                query_dsl={
                    "type": "msearch",
                    "description": "Multi-search for properties and Wikipedia by location",
                    "execution_time_ms": execution_time
                }
            )
            
        except Exception as e:
            logger.error(f"Location search error: {e}")
            return DemoQueryResult(
                query_name=f"Location: {city}, {state}",
                execution_time_ms=0,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl={"type": "msearch", "error": str(e)}
            )


# ============================================================================
# PUBLIC API FUNCTIONS
# ============================================================================

def demo_property_with_full_context(
    es_client: Elasticsearch,
    property_id: Optional[str] = None,
    size: int = 5
) -> DemoQueryResult:
    """
    Demo: Property with full neighborhood and Wikipedia context.
    
    This is the public API function that wraps the demo implementation.
    It provides backward compatibility while using the new type-safe implementation.
    
    Args:
        es_client: Elasticsearch client
        property_id: Optional specific property ID
        size: Number of related Wikipedia articles (unused in new implementation)
        
    Returns:
        DemoQueryResult with property, neighborhood, and Wikipedia data
    """
    demo = PropertyNeighborhoodWikiDemo(es_client)
    return demo.demo_property_with_full_context(property_id)


def demo_neighborhood_properties_and_wiki(
    es_client: Elasticsearch,
    neighborhood_name: str = "Pacific Heights",
    max_properties: int = 5,
    max_wikipedia: int = 3
) -> DemoQueryResult:
    """
    Demo: Neighborhood with its properties and Wikipedia articles.
    
    Args:
        es_client: Elasticsearch client
        neighborhood_name: Name of neighborhood to search
        max_properties: Maximum properties to return (unused - fixed at 5)
        max_wikipedia: Maximum Wikipedia articles (unused - uses correlations)
        
    Returns:
        DemoQueryResult with neighborhood, properties, and Wikipedia data
    """
    demo = PropertyNeighborhoodWikiDemo(es_client)
    return demo.demo_neighborhood_properties_and_wiki(neighborhood_name)


def demo_location_wikipedia_context(
    es_client: Elasticsearch,
    city: str = "San Francisco",
    state: str = "CA",
    limit: int = 10
) -> DemoQueryResult:
    """
    Demo: Location-based search across properties and Wikipedia.
    
    Args:
        es_client: Elasticsearch client
        city: City to search
        state: State code
        limit: Maximum results (unused - fixed at 5 each)
        
    Returns:
        DemoQueryResult with properties and Wikipedia articles
    """
    demo = PropertyNeighborhoodWikiDemo(es_client)
    return demo.demo_location_wikipedia_context(city, state)