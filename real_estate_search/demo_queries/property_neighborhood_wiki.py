"""
Demo queries showing relationships between properties, neighborhoods, and Wikipedia articles.

This module demonstrates how to query and display real estate properties
along with their associated neighborhood information and Wikipedia articles,
showing the full context available from the data pipeline.
"""

from typing import Dict, Any, Optional, List
from elasticsearch import Elasticsearch
import logging

from .models import DemoQueryResult

logger = logging.getLogger(__name__)


def demo_property_with_full_context(
    es_client: Elasticsearch,
    property_id: Optional[str] = None,
    size: int = 5
) -> DemoQueryResult:
    """
    Demo: Property with full neighborhood and Wikipedia context.
    
    This demo shows how to retrieve a property listing along with its
    associated neighborhood information and related Wikipedia articles,
    demonstrating the full data enrichment from the pipeline.
    
    If no property_id is provided, it randomly selects a property that has
    neighborhood relationships.
    
    The query performs:
    1. Gets a property (random or specified)
    2. Retrieves its associated neighborhood using neighborhood_id
    3. Gets Wikipedia articles related to that neighborhood
    4. Combines all the data to show full context
    
    Args:
        es_client: Elasticsearch client
        property_id: Optional specific property ID to lookup
        size: Number of related Wikipedia articles to retrieve
        
    Returns:
        DemoQueryResult with property, neighborhood, and Wikipedia data
    """
    results = []
    
    # Step 1: Get a property
    if not property_id:
        # Get a random property with a neighborhood_id
        random_query = {
            "query": {
                "function_score": {
                    "query": {
                        "exists": {"field": "neighborhood_id"}
                    },
                    "random_score": {"seed": 42}
                }
            },
            "size": 1,
            "_source": True
        }
        
        try:
            response = es_client.search(index="real_estate_properties", body=random_query)
            if response['hits']['hits']:
                property_data = response['hits']['hits'][0]['_source']
                property_id = response['hits']['hits'][0]['_id']
                logger.info(f"Selected property: {property_id}")
            else:
                return DemoQueryResult(
                    query_name="Property with Full Context",
                    execution_time_ms=0,
                    total_hits=0,
                    returned_hits=0,
                    results=[],
                    query_dsl={}
                )
        except Exception as e:
            logger.error(f"Error selecting random property: {e}")
            return DemoQueryResult(
                query_name="Property with Full Context",
                execution_time_ms=0,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl={}
            )
    else:
        # Get specified property
        try:
            response = es_client.get(index="real_estate_properties", id=property_id)
            property_data = response['_source']
        except Exception as e:
            logger.error(f"Error getting property {property_id}: {e}")
            return DemoQueryResult(
                query_name="Property with Full Context",
                execution_time_ms=0,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl={}
            )
    
    # Add property to results
    property_data['_entity_type'] = 'property'
    results.append(property_data)
    
    # Step 2: Get the neighborhood if property has neighborhood_id
    neighborhood_data = None
    if 'neighborhood_id' in property_data and property_data['neighborhood_id']:
        neighborhood_id = property_data['neighborhood_id']
        
        try:
            # Search for neighborhood by ID
            neighborhood_query = {
                "query": {
                    "term": {
                        "neighborhood_id": neighborhood_id
                    }
                },
                "size": 1,
                "_source": True
            }
            
            response = es_client.search(index="real_estate_neighborhoods", body=neighborhood_query)
            if response['hits']['hits']:
                neighborhood_data = response['hits']['hits'][0]['_source']
                neighborhood_data['_entity_type'] = 'neighborhood'
                results.append(neighborhood_data)
                logger.info(f"Found neighborhood: {neighborhood_data.get('name', 'Unknown')}")
        except Exception as e:
            logger.error(f"Error getting neighborhood {neighborhood_id}: {e}")
    
    # Step 3: Get Wikipedia articles if neighborhood has wikipedia_correlations
    wikipedia_articles = []
    if neighborhood_data and 'wikipedia_correlations' in neighborhood_data:
        wiki_corr = neighborhood_data['wikipedia_correlations']
        
        # Get primary Wikipedia article if it exists
        if 'primary_wiki_article' in wiki_corr and wiki_corr['primary_wiki_article']:
            primary = wiki_corr['primary_wiki_article']
            page_id = primary.get('page_id')
            
            if page_id:
                try:
                    wiki_query = {
                        "query": {
                            "term": {
                                "page_id": page_id
                            }
                        },
                        "size": 1,
                        "_source": True
                    }
                    
                    response = es_client.search(index="real_estate_wikipedia", body=wiki_query)
                    if response['hits']['hits']:
                        wiki_data = response['hits']['hits'][0]['_source']
                        wiki_data['_entity_type'] = 'wikipedia_primary'
                        wiki_data['_relationship'] = 'primary_article'
                        wiki_data['_confidence'] = primary.get('confidence', 0.0)
                        results.append(wiki_data)
                        wikipedia_articles.append(wiki_data)
                        logger.info(f"Found primary Wikipedia article: {wiki_data.get('title', 'Unknown')}")
                except Exception as e:
                    logger.error(f"Error getting Wikipedia article {page_id}: {e}")
        
        # Get related Wikipedia articles
        if 'related_wiki_articles' in wiki_corr and wiki_corr['related_wiki_articles']:
            for related in wiki_corr['related_wiki_articles'][:size]:
                page_id = related.get('page_id')
                if page_id:
                    try:
                        wiki_query = {
                            "query": {
                                "term": {
                                    "page_id": page_id
                                }
                            },
                            "size": 1,
                            "_source": ["page_id", "title", "summary", "city", "state"]
                        }
                        
                        response = es_client.search(index="real_estate_wikipedia", body=wiki_query)
                        if response['hits']['hits']:
                            wiki_data = response['hits']['hits'][0]['_source']
                            wiki_data['_entity_type'] = 'wikipedia_related'
                            wiki_data['_relationship'] = related.get('relationship', 'related')
                            wiki_data['_confidence'] = related.get('confidence', 0.0)
                            results.append(wiki_data)
                            wikipedia_articles.append(wiki_data)
                    except Exception as e:
                        logger.error(f"Error getting related Wikipedia article {page_id}: {e}")
    
    # Build descriptive query name
    query_name = f"Property with Full Context: {property_data.get('address', {}).get('street', 'Unknown')}"
    if neighborhood_data:
        query_name += f" in {neighborhood_data.get('name', 'Unknown')}"
    if wikipedia_articles:
        query_name += f" ({len(wikipedia_articles)} Wikipedia articles)"
    
    return DemoQueryResult(
        query_name=query_name,
        execution_time_ms=0,  # Combined query, no single execution time
        total_hits=len(results),
        returned_hits=len(results),
        results=results,
        query_dsl={
            "description": "Multi-step query to get property with neighborhood and Wikipedia context",
            "steps": [
                "1. Get property by ID or random",
                "2. Lookup neighborhood by neighborhood_id",
                "3. Lookup Wikipedia articles from neighborhood.wikipedia_correlations"
            ]
        }
    )


def demo_neighborhood_properties_and_wiki(
    es_client: Elasticsearch,
    neighborhood_name: str = "Pacific Heights",
    max_properties: int = 5,
    max_wikipedia: int = 3
) -> DemoQueryResult:
    """
    Demo: Neighborhood with its properties and Wikipedia articles.
    
    This demo shows how to find a neighborhood and display all its
    associated properties and Wikipedia articles, demonstrating
    the reverse relationship from neighborhood to properties.
    
    Args:
        es_client: Elasticsearch client
        neighborhood_name: Name of neighborhood to search for
        max_properties: Maximum number of properties to show
        max_wikipedia: Maximum number of Wikipedia articles to show
        
    Returns:
        DemoQueryResult with neighborhood, properties, and Wikipedia data
    """
    results = []
    
    # Step 1: Find the neighborhood by name
    neighborhood_query = {
        "query": {
            "match": {
                "name": neighborhood_name
            }
        },
        "size": 1,
        "_source": True
    }
    
    try:
        response = es_client.search(index="real_estate_neighborhoods", body=neighborhood_query)
        if not response['hits']['hits']:
            return DemoQueryResult(
                query_name=f"Neighborhood '{neighborhood_name}' with Properties and Wikipedia",
                execution_time_ms=0,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=neighborhood_query
            )
        
        neighborhood_data = response['hits']['hits'][0]['_source']
        neighborhood_id = neighborhood_data.get('neighborhood_id')
        neighborhood_data['_entity_type'] = 'neighborhood'
        results.append(neighborhood_data)
        
    except Exception as e:
        logger.error(f"Error finding neighborhood: {e}")
        return DemoQueryResult(
            query_name=f"Neighborhood '{neighborhood_name}' with Properties and Wikipedia",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=neighborhood_query
        )
    
    # Step 2: Find all properties in this neighborhood
    if neighborhood_id:
        properties_query = {
            "query": {
                "term": {
                    "neighborhood_id": neighborhood_id
                }
            },
            "size": max_properties,
            "_source": ["listing_id", "address", "price", "bedrooms", "bathrooms", "property_type", "square_feet"]
        }
        
        try:
            response = es_client.search(index="real_estate_properties", body=properties_query)
            for hit in response['hits']['hits']:
                prop = hit['_source']
                prop['_entity_type'] = 'property'
                prop['_relationship'] = 'in_neighborhood'
                results.append(prop)
        except Exception as e:
            logger.error(f"Error finding properties: {e}")
    
    # Step 3: Get Wikipedia articles from neighborhood
    if 'wikipedia_correlations' in neighborhood_data:
        wiki_corr = neighborhood_data['wikipedia_correlations']
        
        # Primary article
        if 'primary_wiki_article' in wiki_corr and wiki_corr['primary_wiki_article']:
            primary = wiki_corr['primary_wiki_article']
            wiki_article = {
                'page_id': primary.get('page_id'),
                'title': primary.get('title'),
                'url': primary.get('url'),
                '_entity_type': 'wikipedia',
                '_relationship': 'primary_article',
                '_confidence': primary.get('confidence', 0.0)
            }
            results.append(wiki_article)
        
        # Related articles
        if 'related_wiki_articles' in wiki_corr and wiki_corr['related_wiki_articles']:
            for related in wiki_corr['related_wiki_articles'][:max_wikipedia]:
                wiki_article = {
                    'page_id': related.get('page_id'),
                    'title': related.get('title'),
                    'url': related.get('url'),
                    '_entity_type': 'wikipedia',
                    '_relationship': related.get('relationship', 'related'),
                    '_confidence': related.get('confidence', 0.0)
                }
                results.append(wiki_article)
    
    property_count = len([r for r in results if r.get('_entity_type') == 'property'])
    wiki_count = len([r for r in results if r.get('_entity_type') == 'wikipedia'])
    
    return DemoQueryResult(
        query_name=f"Neighborhood '{neighborhood_data.get('name', neighborhood_name)}' with {property_count} Properties and {wiki_count} Wikipedia Articles",
        execution_time_ms=0,
        total_hits=len(results),
        returned_hits=len(results),
        results=results,
        query_dsl={
            "description": "Multi-step query to get neighborhood with all related entities",
            "neighborhood_query": neighborhood_query,
            "properties_query": properties_query if 'properties_query' in locals() else None
        }
    )


def demo_location_wikipedia_context(
    es_client: Elasticsearch,
    city: str = "San Francisco",
    state: str = "CA",
    limit: int = 10
) -> DemoQueryResult:
    """
    Demo: Location-based Wikipedia context for properties.
    
    This demo shows how to find properties and their related Wikipedia
    articles based on location, demonstrating how Wikipedia data
    provides geographical and historical context for real estate.
    
    Args:
        es_client: Elasticsearch client
        city: City to search in
        state: State to search in
        limit: Maximum number of results
        
    Returns:
        DemoQueryResult with properties and location-relevant Wikipedia articles
    """
    # Multi-search query for properties and Wikipedia articles in the same location
    msearch_body = []
    
    # Properties in location
    msearch_body.extend([
        {"index": "real_estate_properties"},
        {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"address.city.keyword": city}},
                        {"term": {"address.state.keyword": state}}
                    ]
                }
            },
            "size": limit // 2,
            "_source": ["listing_id", "address", "price", "neighborhood_id", "property_type", "bedrooms"]
        }
    ])
    
    # Wikipedia articles about this location
    msearch_body.extend([
        {"index": "real_estate_wikipedia"},
        {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"city": city}},
                        {"match": {"title": city}},
                        {"match": {"summary": city}}
                    ],
                    "filter": [
                        {"term": {"state.keyword": state}}
                    ]
                }
            },
            "size": limit // 2,
            "_source": ["page_id", "title", "summary", "city", "state"]
        }
    ])
    
    try:
        responses = es_client.msearch(body=msearch_body)
        
        results = []
        
        # Process properties
        prop_response = responses['responses'][0]
        if 'hits' in prop_response:
            for hit in prop_response['hits']['hits']:
                prop = hit['_source']
                prop['_entity_type'] = 'property'
                results.append(prop)
        
        # Process Wikipedia articles
        wiki_response = responses['responses'][1]
        if 'hits' in wiki_response:
            for hit in wiki_response['hits']['hits']:
                wiki = hit['_source']
                wiki['_entity_type'] = 'wikipedia'
                wiki['_relevance'] = 'location_context'
                results.append(wiki)
        
        return DemoQueryResult(
            query_name=f"Location Context: {city}, {state} - Properties with Wikipedia Articles",
            execution_time_ms=max(
                prop_response.get('took', 0),
                wiki_response.get('took', 0)
            ),
            total_hits=len(results),
            returned_hits=len(results),
            results=results,
            query_dsl={
                "multi_search": True,
                "queries": [
                    {"index": "real_estate_properties", "filter": f"city={city}, state={state}"},
                    {"index": "real_estate_wikipedia", "filter": f"city={city}, state={state}"}
                ]
            }
        )
        
    except Exception as e:
        logger.error(f"Error in location Wikipedia context search: {e}")
        return DemoQueryResult(
            query_name=f"Location Context: {city}, {state}",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl={"multi_search": True}
        )