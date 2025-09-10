"""
Demo showing property relationship queries using denormalized index.

This module demonstrates how a denormalized property_relationships index
enables single-query retrieval of properties with their complete context
including neighborhood data and related Wikipedia articles.
"""

import logging
import time
from typing import Dict, Any, List
from elasticsearch import Elasticsearch

from .result_models import MixedEntityResult
from ..models import WikipediaArticle
from ..models import PropertyListing
from ..indexer.enums import IndexName

logger = logging.getLogger(__name__)


class SimplifiedRelationshipDemo:
    """
    Demonstrates single-query property relationships using denormalized index.
    
    The denormalized index contains all property, neighborhood, and Wikipedia
    data in a single document, enabling efficient single-query retrieval.
    """
    
    def __init__(self, es_client: Elasticsearch):
        """Initialize with Elasticsearch client."""
        self.es_client = es_client
        
    def demo_single_query_property(self, property_id: str = None) -> MixedEntityResult:
        """
        Get complete property context with a single query.
        
        The denormalized index contains:
        - All property fields
        - Embedded neighborhood data
        - Related Wikipedia articles
        
        This enables single-query retrieval of all related data.
        
        Args:
            property_id: Optional property ID, otherwise random
            
        Returns:
            Complete property with neighborhood and Wikipedia data
        """
        start_time = time.time()
        
        # Build single query
        if property_id:
            query = {
                "query": {
                    "term": {
                        "listing_id": property_id
                    }
                },
                "size": 1
            }
        else:
            # Random property selection
            query = {
                "query": {
                    "function_score": {
                        "query": {"match_all": {}},
                        "random_score": {"seed": 42}
                    }
                },
                "size": 1
            }
        
        try:
            # Single query retrieves everything!
            response = self.es_client.search(
                index=IndexName.PROPERTY_RELATIONSHIPS,
                body=query
            )
            
            if not response['hits']['hits']:
                return MixedEntityResult(
                    query_name="Single Query Property Relationships",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    total_hits=0,
                    returned_hits=0,
                    property_results=[],
                    wikipedia_results=[],
                    neighborhood_results=[],
                    query_dsl=query
                )
            
            # All data immediately available
            property_data = response['hits']['hits'][0]['_source']
            
            # Extract embedded data - no additional queries needed!
            neighborhood = property_data.get('neighborhood', {})
            wikipedia_articles = property_data.get('wikipedia_articles', [])
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return MixedEntityResult(
                query_name=f"Property: {property_data.get('address', {}).get('street', 'Unknown')}",
                execution_time_ms=execution_time,
                total_hits=1,
                returned_hits=1,
                property_results=[PropertyListing.from_elasticsearch(property_data)],
                wikipedia_results=[WikipediaArticle(
                    page_id=str(a.get('page_id', '')),
                    title=a.get('title', ''),
                    long_summary=a.get('long_summary'),
                    short_summary=a.get('short_summary'),
                    city=a.get('city'),
                    state=a.get('state'),
                    url=a.get('url')
                ) for a in wikipedia_articles],
                neighborhood_results=[neighborhood] if neighborhood else [],
                query_dsl={
                    "description": "SINGLE query retrieves all relationships",
                    "query": query,
                    "execution_time_ms": execution_time,
                    "data_retrieved": {
                        "property": "Full property data",
                        "neighborhood": "Embedded neighborhood data",
                        "wikipedia": f"{len(wikipedia_articles)} related articles"
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Query error: {e}")
            return MixedEntityResult(
                query_name="Single Query Property Relationships",
                execution_time_ms=int((time.time() - start_time) * 1000),
                total_hits=0,
                returned_hits=0,
                property_results=[],
                wikipedia_results=[],
                neighborhood_results=[],
                query_dsl={"error": str(e)}
            )
    
    def demo_neighborhood_properties_simplified(self, neighborhood_name: str) -> MixedEntityResult:
        """
        Get all properties in a neighborhood with a single query.
        
        The denormalized structure allows filtering by embedded
        neighborhood fields without additional lookups.
        
        Args:
            neighborhood_name: Neighborhood to search
            
        Returns:
            Properties in the neighborhood
        """
        start_time = time.time()
        
        query = {
            "query": {
                "match": {
                    "neighborhood.name": neighborhood_name
                }
            },
            "size": 10
        }
        
        try:
            response = self.es_client.search(
                index=IndexName.PROPERTY_RELATIONSHIPS,
                body=query
            )
            
            results = []
            for hit in response['hits']['hits']:
                results.append(hit['_source'])
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return MixedEntityResult(
                query_name=f"Neighborhood: {neighborhood_name}",
                execution_time_ms=execution_time,
                total_hits=response['hits']['total']['value'],
                returned_hits=len(results),
                property_results=[PropertyListing.from_elasticsearch(r) for r in results],
                wikipedia_results=[],
                neighborhood_results=[],
                query_dsl=query
            )
            
        except Exception as e:
            logger.error(f"Query error: {e}")
            return MixedEntityResult(
                query_name=f"Neighborhood: {neighborhood_name}",
                execution_time_ms=int((time.time() - start_time) * 1000),
                total_hits=0,
                returned_hits=0,
                property_results=[],
                wikipedia_results=[],
                neighborhood_results=[],
                query_dsl={"error": str(e)}
            )
    
    def demo_location_search_simplified(self, city: str, state: str) -> MixedEntityResult:
        """
        Search by location with full context in a single query.
        
        Location-based filtering with complete property context
        retrieved from the denormalized index.
        
        Args:
            city: City name
            state: State code
            
        Returns:
            Properties in the location with full context
        """
        start_time = time.time()
        
        query = {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"address.city": city.lower()}},
                        {"term": {"address.state": state}}
                    ]
                }
            },
            "size": 5,
            "sort": [{"price": {"order": "desc"}}]
        }
        
        try:
            response = self.es_client.search(
                index=IndexName.PROPERTY_RELATIONSHIPS,
                body=query
            )
            
            results = []
            for hit in response['hits']['hits']:
                results.append(hit['_source'])
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return MixedEntityResult(
                query_name=f"Location: {city}, {state}",
                execution_time_ms=execution_time,
                total_hits=response['hits']['total']['value'],
                returned_hits=len(results),
                property_results=[PropertyListing.from_elasticsearch(r) for r in results],
                wikipedia_results=[],
                neighborhood_results=[],
                query_dsl=query
            )
            
        except Exception as e:
            logger.error(f"Query error: {e}")
            return MixedEntityResult(
                query_name=f"Location: {city}, {state}",
                execution_time_ms=int((time.time() - start_time) * 1000),
                total_hits=0,
                returned_hits=0,
                property_results=[],
                wikipedia_results=[],
                neighborhood_results=[],
                query_dsl={"error": str(e)}
            )


def demo_simplified_relationships(es_client: Elasticsearch) -> MixedEntityResult:
    """
    Main demo entry point showing simplified relationship queries.
    
    Args:
        es_client: Elasticsearch client
        
    Returns:
        MixedEntityResult with demonstration results
    """
    # Run actual demo
    demo = SimplifiedRelationshipDemo(es_client)
    
    # Demo 1: Single property with full context
    result1 = demo.demo_single_query_property()
    
    # Demo 2: Neighborhood search
    result2 = demo.demo_neighborhood_properties_simplified("Pacific Heights")
    
    # Demo 3: Location search
    result3 = demo.demo_location_search_simplified("Oakland", "CA")
    
    total_time = result1.execution_time_ms + result2.execution_time_ms + result3.execution_time_ms
    
    # Combine results - removing duplicates
    unique_properties = []
    seen_ids = set()
    
    for result in [result1, result2, result3]:
        for prop in result.property_results:
            if prop.listing_id not in seen_ids:
                unique_properties.append(prop)
                seen_ids.add(prop.listing_id)
                if len(unique_properties) >= 10:
                    break
    
    return MixedEntityResult(
        query_name="Demo 10: Property Relationships via Denormalized Index",
        query_description="Demonstrates single-query retrieval using denormalized index structure for optimal read performance",
        execution_time_ms=total_time,
        total_hits=result1.total_hits + result2.total_hits + result3.total_hits,
        returned_hits=len(unique_properties),
        property_results=unique_properties,
        wikipedia_results=result1.wikipedia_results[:5] if result1.wikipedia_results else [],
        neighborhood_results=result1.neighborhood_results,
        query_dsl={
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
        },
        es_features=[
            "Denormalized Index - All related data in single document",
            "Embedded Documents - Neighborhood and Wikipedia data included",
            "Single Query Retrieval - No additional lookups needed",
            "Filter Context - Efficient non-scoring queries",
            "Term Queries - Exact matching on fields",
            "Function Score - Random property selection"
        ],
        indexes_used=[
            "property_relationships index - Denormalized property data",
            "Contains embedded neighborhood and Wikipedia data",
            "Optimized for read-heavy workloads"
        ]
    )