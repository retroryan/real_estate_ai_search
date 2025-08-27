"""Advanced demo queries including semantic search and multi-entity search."""

from typing import Dict, Any, Optional, List
from elasticsearch import Elasticsearch
import logging

from .models import DemoQueryResult

logger = logging.getLogger(__name__)


def demo_semantic_search(
    es_client: Elasticsearch,
    size: int = 5
) -> DemoQueryResult:
    """
    Demo 6: Semantic similarity search using embeddings.
    
    Randomly selects a property and finds the most similar properties
    using cosine similarity of pre-computed embedding vectors.
    
    How it works:
    1. Randomly selects a reference property from the index
    2. Retrieves that property's embedding vector (1024 dimensions)
    3. Uses cosine similarity to find the most similar properties
    4. Returns top 5 matches excluding the reference property itself
    
    Args:
        es_client: Elasticsearch client
        size: Number of similar properties to return
        
    Returns:
        DemoQueryResult with semantically similar properties
    """
    # Always randomly pick a reference property
    reference_property_id = None
    embedding_vector = None
    
    try:
        import random
        # Get a random property with embeddings
        random_query = {
            "query": {
                "function_score": {
                    "query": {
                        "exists": {"field": "embedding"}
                    },
                    "random_score": {"seed": random.randint(1, 10000)}
                }
            },
            "size": 1,
            "_source": ["listing_id", "embedding", "address", "price", "bedrooms", "bathrooms", "property_type", "square_feet"]
        }
        random_response = es_client.search(index="properties", body=random_query)
        if random_response['hits']['hits']:
            reference_property_id = random_response['hits']['hits'][0]['_id']
            ref_data = random_response['hits']['hits'][0]['_source']
            embedding_vector = ref_data.get('embedding')
            logger.info(f"Randomly selected property: {reference_property_id}")
    except Exception as e:
        logger.error(f"Could not get random property: {e}")
        return DemoQueryResult(
            query_name="Semantic Similarity Search",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl={}
        )
    
    # Build semantic search query with embeddings excluding the reference property
    if embedding_vector and reference_property_id:
        query = {
            "query": {
                "bool": {
                    "must_not": [
                        {"term": {"_id": reference_property_id}}  # Exclude the reference property
                    ],
                    "must": [
                        {
                            "script_score": {
                                "query": {"exists": {"field": "embedding"}},
                                "script": {
                                    "source": "cosineSimilarity(params.vector, 'embedding') + 1.0",
                                    "params": {
                                        "vector": embedding_vector
                                    }
                                }
                            }
                        }
                    ]
                }
            },
            "size": size,
            "min_score": 1.0,  # Cosine similarity + 1 means minimum actual similarity of 0
            "_source": [
                "listing_id", "property_type", "price", "bedrooms", "bathrooms",
                "square_feet", "address", "description", "features"
            ]
        }
    else:
        # Fallback query if no embedding available
        query = {
            "query": {"match_all": {}},
            "size": size,
            "_source": [
                "listing_id", "property_type", "price", "bedrooms", "bathrooms",
                "square_feet", "address", "description"
            ]
        }
    
    try:
        response = es_client.search(index="properties", body=query)
        
        results = []
        for hit in response['hits']['hits']:
            result = hit['_source']
            result['_score'] = hit.get('_score', 0)
            results.append(result)
        
        # Get reference property details for query name
        ref_details = ""
        if reference_property_id:
            try:
                # We already have ref_data from the random selection
                ref_doc = es_client.get(index="properties", id=reference_property_id)
                if '_source' in ref_doc:
                    ref = ref_doc['_source']
                    ref_details = f"Finding properties similar to: {ref.get('address', {}).get('street', 'N/A')}, {ref.get('address', {}).get('city', 'N/A')} - {ref.get('bedrooms', 0)}bd/{ref.get('bathrooms', 0)}ba - ${ref.get('price', 0):,.0f} - {ref.get('property_type', 'N/A')}"
            except:
                ref_details = f"Finding properties similar to: {reference_property_id}"
        
        query_name = f"Semantic Similarity Search (Random Property)\n   {ref_details}"
        
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
            query_dsl=query if 'query' in locals() else {}
        )


def demo_multi_entity_search(
    es_client: Elasticsearch,
    query_text: str = "historic downtown",
    size_per_index: int = 5
) -> DemoQueryResult:
    """
    Demo 7: Multi-entity combined search.
    
    Searches across properties, neighborhoods, and Wikipedia articles
    in a single query using the multi-search API for efficiency.
    
    Args:
        es_client: Elasticsearch client
        query_text: Search query text
        size_per_index: Number of results per index
        
    Returns:
        DemoQueryResult with combined results from all indices
    """
    # Build multi-search request
    msearch_body = []
    
    # Properties search
    msearch_body.extend([
        {"index": "properties"},
        {
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": ["description^2", "features", "amenities", "address.city"],
                    "type": "best_fields"
                }
            },
            "size": size_per_index,
            "_source": ["listing_id", "property_type", "price", "bedrooms", "address", "description"]
        }
    ])
    
    # Neighborhoods search
    msearch_body.extend([
        {"index": "neighborhoods"},
        {
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": ["name^2", "description", "city"],
                    "type": "best_fields"
                }
            },
            "size": size_per_index,
            "_source": ["neighborhood_id", "name", "city", "state", "description"]
        }
    ])
    
    # Wikipedia search
    msearch_body.extend([
        {"index": "wikipedia"},
        {
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": ["title^2", "summary^1.5", "content"],
                    "type": "best_fields"
                }
            },
            "size": size_per_index,
            "_source": ["page_id", "title", "summary", "city", "state"]
        }
    ])
    
    try:
        responses = es_client.msearch(body=msearch_body)
        
        combined_results = []
        total_hits = 0
        execution_time = 0
        
        # Process each response
        for idx, response in enumerate(responses.get('responses', [])):
            if 'error' in response:
                logger.error(f"Error in multi-search index {idx}: {response['error']}")
                continue
            
            entity_type = ['properties', 'neighborhoods', 'wikipedia'][idx]
            execution_time = max(execution_time, response.get('took', 0))
            total_hits += response['hits']['total']['value']
            
            for hit in response['hits']['hits']:
                result = hit['_source']
                result['_entity_type'] = entity_type
                result['_score'] = hit.get('_score', 0)
                combined_results.append(result)
        
        # Sort combined results by score
        combined_results.sort(key=lambda x: x.get('_score', 0), reverse=True)
        
        return DemoQueryResult(
            query_name=f"Multi-Entity Search: '{query_text}' (searching: properties, neighborhoods, wikipedia)",
            execution_time_ms=execution_time,
            total_hits=total_hits,
            returned_hits=len(combined_results),
            results=combined_results,
            query_dsl={
                "multi_search": True,
                "searches": [
                    {"index": "properties", "query": msearch_body[1]},
                    {"index": "neighborhoods", "query": msearch_body[3]},
                    {"index": "wikipedia", "query": msearch_body[5]}
                ]
            }
        )
    except Exception as e:
        logger.error(f"Error in multi-entity search: {e}")
        return DemoQueryResult(
            query_name="Multi-Entity Search",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl={"multi_search": True}
        )


def demo_wikipedia_search(
    es_client: Elasticsearch,
    query_text: str = "golden gate park",
    city: Optional[str] = None,
    state: Optional[str] = None,
    size: int = 10
) -> DemoQueryResult:
    """
    Demo 8: Wikipedia article search.
    
    Searches Wikipedia articles with optional location filtering
    to find relevant local knowledge and context.
    
    Args:
        es_client: Elasticsearch client
        query_text: Search query text
        city: Optional city filter
        state: Optional state filter
        size: Number of results
        
    Returns:
        DemoQueryResult with Wikipedia articles
    """
    # Build query with optional location filters
    must_clauses = [
        {
            "multi_match": {
                "query": query_text,
                "fields": [
                    "title^3",
                    "summary^2",
                    "content",
                    "topics"
                ],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        }
    ]
    
    filter_clauses = []
    if city:
        filter_clauses.append({"term": {"city.keyword": city}})
    if state:
        filter_clauses.append({"term": {"state.keyword": state}})
    
    query = {
        "query": {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses if filter_clauses else None
            }
        } if filter_clauses else {"bool": {"must": must_clauses}},
        "size": size,
        "_source": [
            "page_id", "title", "url", "summary", "city", "state",
            "location", "article_quality_score", "topics"
        ],
        "highlight": {
            "fields": {
                "summary": {"fragment_size": 150},
                "content": {"fragment_size": 200}
            }
        },
        "sort": [
            "_score",
            {"article_quality_score": {"order": "desc", "missing": "_last"}}
        ]
    }
    
    # Clean up query if no filters
    if not filter_clauses:
        query["query"] = must_clauses[0]
    
    try:
        response = es_client.search(index="wikipedia", body=query)
        
        results = []
        for hit in response['hits']['hits']:
            result = hit['_source']
            result['_score'] = hit.get('_score', 0)
            if 'highlight' in hit:
                result['_highlights'] = hit['highlight']
            results.append(result)
        
        location_filter = []
        if city:
            location_filter.append(f"city={city}")
        if state:
            location_filter.append(f"state={state}")
        location_str = f" ({', '.join(location_filter)})" if location_filter else ""
        
        return DemoQueryResult(
            query_name=f"Wikipedia Search: '{query_text}'{location_str}",
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