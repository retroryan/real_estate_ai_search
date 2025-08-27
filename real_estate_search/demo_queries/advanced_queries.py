"""
Advanced search demo queries including semantic similarity and multi-entity search.

ADVANCED ELASTICSEARCH CONCEPTS:
- KNN (k-nearest neighbor) search for semantic similarity using vectors
- Script Score queries for custom ranking algorithms
- Multi-index search patterns
- Complex bool query combinations
- Query and filter context interactions
"""

from typing import Dict, Any, Optional, List
from elasticsearch import Elasticsearch
import logging
import random

from .models import DemoQueryResult

logger = logging.getLogger(__name__)


def demo_semantic_search(
    es_client: Elasticsearch,
    reference_property_id: Optional[str] = None,
    size: int = 10
) -> DemoQueryResult:
    """
    Demo 6: Semantic similarity search using embeddings.
    
    ELASTICSEARCH CONCEPTS:
    - KNN SEARCH: k-nearest neighbor for vector similarity
    - SCRIPT SCORE: Custom scoring using Painless scripts
    - DENSE VECTORS: Storing and searching embeddings
    - COSINE SIMILARITY: Vector similarity metric
    
    Finds properties similar to a reference property using vector embeddings,
    demonstrating AI-powered semantic search capabilities.
    
    Args:
        es_client: Elasticsearch client
        reference_property_id: Property to find similar ones to
        size: Number of similar properties to return
        
    Returns:
        DemoQueryResult with semantically similar properties
    """
    
    # First, get a reference property (random if not specified)
    if not reference_property_id:
        # RANDOM SAMPLING: Get a random document for demonstration
        random_query = {
            # FUNCTION SCORE QUERY: Modify document scores with functions
            "query": {
                "function_score": {
                    "query": {"match_all": {}},
                    # RANDOM SCORE: Randomize results for sampling
                    "random_score": {"seed": random.randint(1, 10000)}
                }
            },
            "size": 1
        }
        
        try:
            random_response = es_client.search(index="properties", body=random_query)
            if random_response['hits']['hits']:
                reference_property_id = random_response['hits']['hits'][0]['_id']
        except Exception as e:
            logger.error(f"Error getting random property: {e}")
            reference_property_id = "prop-001"
    
    # First get the reference property's embedding
    reference_embedding = None
    ref_property_details = {}
    
    try:
        # Get reference property with its embedding
        if reference_property_id:
            ref_doc = es_client.get(index="properties", id=reference_property_id)
            if 'embedding' in ref_doc.get('_source', {}):
                reference_embedding = ref_doc['_source']['embedding']
                ref_property_details = {
                    'address': ref_doc['_source'].get('address', {}),
                    'property_type': ref_doc['_source'].get('property_type', 'Unknown'),
                    'price': ref_doc['_source'].get('price', 0),
                    'bedrooms': ref_doc['_source'].get('bedrooms', 0),
                    'bathrooms': ref_doc['_source'].get('bathrooms', 0),
                    'square_feet': ref_doc['_source'].get('square_feet', 0)
                }
                # Log property details for context
                addr = ref_property_details['address']
                street = addr.get('street', 'Unknown street')
                city = addr.get('city', 'Unknown city')
                price_fmt = f"${ref_property_details['price']:,.0f}" if ref_property_details['price'] else "Unknown price"
                beds = ref_property_details['bedrooms']
                baths = ref_property_details['bathrooms']
                sqft = ref_property_details['square_feet']
                prop_type = ref_property_details['property_type']
                
                logger.info(f"\n" + "="*60 + 
                           f"\n🔍 REFERENCE PROPERTY FOR SIMILARITY SEARCH:" +
                           f"\n{'-'*60}" +
                           f"\nProperty ID: {reference_property_id}" +
                           f"\nAddress: {street}, {city}" +
                           f"\nType: {prop_type}" +
                           f"\nPrice: {price_fmt}" +
                           f"\nSize: {beds}bd/{baths}ba | {sqft} sqft" +
                           f"\n" + "="*60)
            else:
                logger.warning(f"Reference property {reference_property_id} has no embedding")
                return DemoQueryResult(
                    query_name="Semantic Similarity Search",
                    execution_time_ms=0,
                    total_hits=0,
                    returned_hits=0,
                    results=[],
                    query_dsl={"error": "Reference property has no embedding"}
                )
    except Exception as e:
        logger.error(f"Error getting reference property: {e}")
        return DemoQueryResult(
            query_name="Semantic Similarity Search",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl={"error": str(e)}
        )
    
    # Build the KNN semantic similarity query
    # KNN is the modern, efficient way to do vector similarity in Elasticsearch
    query = {
        # KNN SEARCH: K-Nearest Neighbors for vector similarity
        # This is much more efficient than script_score for dense_vector fields
        "knn": {
            "field": "embedding",  # The dense_vector field containing embeddings
            "query_vector": reference_embedding,  # The reference vector to compare against
            "k": size + 1,  # Number of neighbors to find (+1 as reference might be included)
            "num_candidates": 100  # Number of candidates per shard (higher = more accurate but slower)
        },
        # FILTER: Exclude the reference property from results
        "query": {
            "bool": {
                "must_not": [
                    {"term": {"_id": reference_property_id}}
                ]
            }
        },
        "size": size,
        "_source": [
            "listing_id", "property_type", "price", "bedrooms", "bathrooms",
            "square_feet", "address", "description", "features"
        ]
    }
    
    try:
        
        response = es_client.search(index="properties", body=query)
        
        results = []
        for hit in response['hits']['hits']:
            result = hit['_source']
            # Include similarity score for transparency
            result['_similarity_score'] = hit['_score']
            result['_reference_property'] = reference_property_id
            results.append(result)
        
        # Create descriptive query name with reference property info
        query_name = f"Semantic Similarity Search - Finding properties similar to: {street}, {city} ({prop_type}, {price_fmt})"
        
        return DemoQueryResult(
            query_name=query_name,
            execution_time_ms=response.get('took', 0),
            total_hits=response['hits']['total']['value'],
            returned_hits=len(results),
            results=results,
            query_dsl=query
        )
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        return DemoQueryResult(
            query_name="Semantic Similarity Search",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=query
        )


def demo_multi_entity_search(
    es_client: Elasticsearch,
    query_text: str = "historic downtown",
    size: int = 5
) -> DemoQueryResult:
    """
    Demo 7: Multi-entity combined search across different indices.
    
    ELASTICSEARCH CONCEPTS:
    - MULTI-INDEX SEARCH: Query multiple indices in one request
    - INDEX BOOSTING: Weight importance of different indices
    - CROSS-INDEX RANKING: Unified relevance scoring
    - RESULT DISCRIMINATION: Identify source index of each result
    
    Searches across properties, neighborhoods, and Wikipedia articles
    to provide comprehensive results from multiple data sources.
    
    Args:
        es_client: Elasticsearch client
        query_text: Search query text
        size: Number of results per entity type
        
    Returns:
        DemoQueryResult with mixed entity results
    """
    
    # MULTI-INDEX QUERY: Search multiple indices simultaneously
    # This is more efficient than separate queries
    query = {
        "query": {
            # MULTI_MATCH across all text fields in all indices
            "multi_match": {
                "query": query_text,
                # FIELD PATTERNS: Use wildcards to match fields across indices
                "fields": [
                    # Property fields
                    "description^2",
                    "features^1.5",
                    "amenities",
                    "address.city",
                    "neighborhood_name",
                    
                    # Neighborhood fields (will be ignored if not present)
                    "name^3",
                    "demographics.description",
                    
                    # Wikipedia fields
                    "title^3",
                    "summary^2",
                    "content",
                    "categories"
                ],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        },
        
        # AGGREGATION: Count results by index for overview
        "aggs": {
            "by_index": {
                # INDEX AGGREGATION: Group by _index metadata field
                "terms": {
                    "field": "_index",
                    "size": 10
                }
            }
        },
        
        "size": size * 3,  # Get more since we're searching multiple indices
        
        # Include index name in results for discrimination
        "_source": {
            "includes": ["*"]  # All fields
        },
        
        # HIGHLIGHT: Works across all indices
        "highlight": {
            "fields": {
                "*": {}  # Highlight any matching field
            },
            "pre_tags": ["<mark>"],
            "post_tags": ["</mark>"]
        }
    }
    
    # INDEX SPECIFICATION: Can use wildcards or comma-separated list
    indices = "properties,neighborhoods,wikipedia"
    # Alternative patterns:
    # indices = "*"  # Search all indices
    # indices = "prop*,neigh*"  # Wildcard patterns
    # indices = ["properties", "neighborhoods"]  # List format
    
    try:
        response = es_client.search(
            index=indices,  # Multiple indices
            body=query,
            # INDEX BOOST: Weight certain indices as more important
            # Can be specified in URL: "properties^2,neighborhoods^1.5,wikipedia"
        )
        
        # Process results and add entity type
        results = []
        for hit in response['hits']['hits']:
            result = hit['_source']
            
            # ADD METADATA: Include index and type information
            result['_index'] = hit['_index']
            result['_id'] = hit['_id']
            result['_score'] = hit['_score']
            
            # ENTITY TYPE DETECTION: Based on index name
            if 'properties' in hit['_index']:
                result['_entity_type'] = 'property'
            elif 'neighborhoods' in hit['_index']:
                result['_entity_type'] = 'neighborhood'
            elif 'wikipedia' in hit['_index']:
                result['_entity_type'] = 'wikipedia'
            else:
                result['_entity_type'] = 'unknown'
            
            # Add highlights if present
            if 'highlight' in hit:
                result['_highlights'] = hit['highlight']
            
            results.append(result)
        
        # Include aggregation results
        aggregations = {}
        if 'aggregations' in response:
            aggregations = response['aggregations']
        
        return DemoQueryResult(
            query_name=f"Multi-Entity Search: '{query_text}' (searching: {indices})",
            execution_time_ms=response.get('took', 0),
            total_hits=response['hits']['total']['value'],
            returned_hits=len(results),
            results=results,
            aggregations=aggregations,
            query_dsl=query
        )
    except Exception as e:
        logger.error(f"Error in multi-entity search: {e}")
        return DemoQueryResult(
            query_name="Multi-Entity Search",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=query
        )


def demo_wikipedia_search(
    es_client: Elasticsearch,
    city: Optional[str] = "San Francisco",
    state: Optional[str] = "California",
    topics: Optional[List[str]] = None,
    size: int = 10
) -> DemoQueryResult:
    """
    Demo 8: Wikipedia article search with location filtering.
    
    ELASTICSEARCH CONCEPTS:
    - COMPLEX BOOL QUERIES: Combining multiple conditions
    - QUERY vs FILTER CONTEXT: When to use each
    - FIELD EXISTENCE CHECKS: Using exists query
    - MULTI-FIELD SORTING: Primary and secondary sort orders
    - NULL HANDLING: Dealing with missing values in sorts
    
    Searches Wikipedia articles with geographic and topical filters,
    demonstrating complex query construction.
    
    Args:
        es_client: Elasticsearch client
        city: Filter by city
        state: Filter by state
        topics: Filter by topics/categories
        size: Number of results
        
    Returns:
        DemoQueryResult with Wikipedia articles
    """
    if topics is None:
        topics = ["history", "culture", "landmark"]
    
    # BUILD COMPLEX BOOL QUERY
    # Demonstrates query vs filter context usage
    
    # MUST CLAUSES: Query context - affects scoring
    must_clauses = []
    
    # Add topic search if provided
    if topics:
        must_clauses.append({
            "multi_match": {
                "query": " ".join(topics),
                "fields": [
                    "title^2",      # Article title most important
                    "summary^1.5",  # Summary quite important
                    "categories",   # Categories/topics
                    "content"       # Full content
                ],
                "type": "best_fields"
            }
        })
    
    # FILTER CLAUSES: Filter context - no scoring, cacheable
    filter_clauses = []
    
    # Geographic filters
    if city:
        filter_clauses.append({
            # NESTED BOOL: OR condition within AND
            "bool": {
                "should": [  # OR - match any of these
                    {"match": {"city": city}},  # Match city field
                    {"match": {"title": city}}  # Also check title for city name
                ],
                "minimum_should_match": 1  # At least one must match
            }
        })
    
    if state:
        filter_clauses.append({
            "bool": {
                "should": [
                    {"match": {"state": state}},  # Match state field
                    {"term": {"state": state.upper()}}  # Also try uppercase (UT vs Utah)
                ],
                "minimum_should_match": 1
            }
        })
    
    # Ensure articles have city data  
    filter_clauses.append({
        "exists": {"field": "city"}  # Only articles with city field
    })
    
    query = {
        "query": {
            "bool": {
                # QUERY CONTEXT: Scoring queries
                "must": must_clauses if must_clauses else [{"match_all": {}}],
                
                # FILTER CONTEXT: Non-scoring filters
                "filter": filter_clauses,
                
                # BOOSTING: Prefer certain articles
                "should": [
                    # Boost high-quality articles
                    {"range": {"article_quality_score": {"gte": 0.8, "boost": 2.0}}},
                    # Boost if title contains the city
                    {"match": {"title": {"query": city or "", "boost": 1.5}}},
                    # Boost comprehensive articles
                    {"range": {"content_length": {"gte": 5000, "boost": 1.2}}}
                ]
            }
        } if filter_clauses else {"bool": {"must": must_clauses}},
        
        "size": size,
        
        "_source": [
            "page_id", "title", "url", "summary", "city", "state",
            "location", "article_quality_score", "topics"
        ],
        
        # HIGHLIGHTING: Show matching content
        "highlight": {
            "fields": {
                "summary": {"fragment_size": 150},
                "content": {"fragment_size": 200}
            }
        },
        
        # COMPLEX SORTING: Multiple sort criteria
        "sort": [
            "_score",  # Primary: relevance
            # Secondary: quality score (handle nulls)
            {"article_quality_score": {"order": "desc", "missing": "_last"}}
        ]
    }
    
    # Clean up query if no filters
    if not filter_clauses:
        query['query'] = {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}
    
    try:
        response = es_client.search(index="wikipedia", body=query)
        
        results = []
        for hit in response['hits']['hits']:
            result = hit['_source']
            result['_score'] = hit['_score']
            
            # Add highlights
            if 'highlight' in hit:
                result['_highlights'] = hit['highlight']
            
            # Add computed relevance info
            result['_relevance_factors'] = {
                'score': hit['_score'],
                'has_location': 'location' in result,
                'quality_score': result.get('article_quality_score', 0)
            }
            
            results.append(result)
        
        return DemoQueryResult(
            query_name=f"Wikipedia Search",
            execution_time_ms=response.get('took', 0),
            total_hits=response['hits']['total']['value'],
            returned_hits=len(results),
            results=results,
            query_dsl=query
        )
    except Exception as e:
        logger.error(f"Error in Wikipedia search: {e}")
        return DemoQueryResult(
            query_name="Wikipedia Search",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=query
        )
