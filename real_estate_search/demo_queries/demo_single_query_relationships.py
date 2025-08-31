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
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from .models import DemoQueryResult
from ..indexer.enums import IndexName

logger = logging.getLogger(__name__)
console = Console()


class SimplifiedRelationshipDemo:
    """
    Demonstrates single-query property relationships using denormalized index.
    
    The denormalized index contains all property, neighborhood, and Wikipedia
    data in a single document, enabling efficient single-query retrieval.
    """
    
    def __init__(self, es_client: Elasticsearch):
        """Initialize with Elasticsearch client."""
        self.es_client = es_client
        
    def demo_single_query_property(self, property_id: str = None) -> DemoQueryResult:
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
                        "listing_id.keyword": property_id
                    }
                }
            }
        else:
            # Random property
            query = {
                "query": {
                    "function_score": {
                        "query": {"match_all": {}},
                        "random_score": {"seed": 42}
                    }
                },
                "size": 1
            }
        
        # ONE query gets everything!
        try:
            response = self.es_client.search(
                index=IndexName.PROPERTY_RELATIONSHIPS,
                body=query
            )
            
            if not response['hits']['hits']:
                return DemoQueryResult(
                    query_name="Single Query Property Relationships",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    total_hits=0,
                    returned_hits=0,
                    results=[],
                    query_dsl=query
                )
            
            # All data immediately available
            property_data = response['hits']['hits'][0]['_source']
            
            # Extract embedded data - no additional queries needed!
            neighborhood = property_data.get('neighborhood', {})
            wikipedia_articles = property_data.get('wikipedia_articles', [])
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return DemoQueryResult(
                query_name=f"Property: {property_data.get('address', {}).get('street', 'Unknown')}",
                execution_time_ms=execution_time,
                total_hits=1,
                returned_hits=1,
                results=[property_data],
                query_dsl={
                    "description": "SINGLE query retrieves all relationships",
                    "query": query,
                    "execution_time_ms": execution_time,
                    "data_retrieved": {
                        "property": "Complete property data",
                        "neighborhood": "Embedded neighborhood data",
                        "wikipedia_articles": f"{len(wikipedia_articles)} articles"
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Query error: {e}")
            return DemoQueryResult(
                query_name="Single Query Property Relationships",
                execution_time_ms=int((time.time() - start_time) * 1000),
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl={"error": str(e)}
            )
    
    def demo_neighborhood_properties_simplified(self, neighborhood_name: str) -> DemoQueryResult:
        """
        Get all properties in a neighborhood with a single query.
        
        The denormalized structure allows filtering by embedded
        neighborhood fields without additional lookups.
        
        Args:
            neighborhood_name: Neighborhood to search
            
        Returns:
            All properties with full context
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
            
            return DemoQueryResult(
                query_name=f"Neighborhood: {neighborhood_name}",
                execution_time_ms=execution_time,
                total_hits=response['hits']['total']['value'],
                returned_hits=len(results),
                results=results,
                query_dsl=query
            )
            
        except Exception as e:
            logger.error(f"Query error: {e}")
            return DemoQueryResult(
                query_name=f"Neighborhood: {neighborhood_name}",
                execution_time_ms=int((time.time() - start_time) * 1000),
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl={"error": str(e)}
            )
    
    def demo_location_search_simplified(self, city: str, state: str) -> DemoQueryResult:
        """
        Search by location with full context in a single query.
        
        Location-based filtering with complete property context
        retrieved from the denormalized index.
        
        Args:
            city: City name
            state: State code
            
        Returns:
            Properties with complete context
        """
        start_time = time.time()
        
        query = {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"address.city.keyword": city}},
                        {"term": {"address.state.keyword": state}}
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
            
            return DemoQueryResult(
                query_name=f"Location: {city}, {state}",
                execution_time_ms=execution_time,
                total_hits=response['hits']['total']['value'],
                returned_hits=len(results),
                results=results,
                query_dsl=query
            )
            
        except Exception as e:
            logger.error(f"Query error: {e}")
            return DemoQueryResult(
                query_name=f"Location: {city}, {state}",
                execution_time_ms=int((time.time() - start_time) * 1000),
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl={"error": str(e)}
            )


def display_denormalized_structure(es_client: Elasticsearch):
    """
    Display the structure of the denormalized index.
    
    Shows how data from multiple indices is combined into a single document.
    """
    console.print("\n[bold cyan]Denormalized Index Structure[/bold cyan]")
    console.print("=" * 70)
    
    # Show index structure
    console.print("\n[bold]The property_relationships index combines:[/bold]")
    console.print("• Property data (from properties index)")
    console.print("• Neighborhood data (from neighborhoods index)")
    console.print("• Wikipedia articles (from wikipedia index)")
    console.print("\nThis enables single-query retrieval of all related data.\n")
    
    # Show sample document structure
    sample_structure = """{
  "listing_id": "prop_123",
  "property_type": "condo",
  "price": 850000,
  "bedrooms": 2,
  "address": {
    "street": "123 Main St",
    "city": "San Francisco",
    "state": "CA"
  },
  "neighborhood": {
    "neighborhood_id": "nhood_456",
    "name": "Pacific Heights",
    "walkability_score": 92,
    "amenities": ["parks", "restaurants", "shopping"]
  },
  "wikipedia_articles": [
    {
      "page_id": "wiki_789",
      "title": "Pacific Heights, San Francisco",
      "summary": "Pacific Heights is a neighborhood...",
      "relationship_type": "primary",
      "confidence": 0.95
    }
  ]
}"""
    console.print(Panel(sample_structure, title="Sample Document Structure", border_style="cyan"))
    
    console.print("\n[bold yellow]Key Benefits:[/bold yellow]")
    console.print("• Single query retrieves all data")
    console.print("• No JOIN operations required")
    console.print("• Optimized for read performance")
    console.print("• Simplified application logic")
    console.print("• Consistent data snapshot")


def demo_simplified_relationships(es_client: Elasticsearch) -> DemoQueryResult:
    """
    Main demo entry point showing simplified relationship queries.
    
    Args:
        es_client: Elasticsearch client
        
    Returns:
        DemoQueryResult with comparison data
    """
    console.print("\n[bold cyan]Demo 10: Property Relationships via Denormalized Index[/bold cyan]")
    console.print("=" * 70)
    
    # First show the index structure
    display_denormalized_structure(es_client)
    
    # Then run actual demo
    demo = SimplifiedRelationshipDemo(es_client)
    
    console.print("\n[bold]Running Denormalized Index Queries:[/bold]")
    console.print("-" * 50)
    
    # Demo 1: Single property with full context
    console.print("\n[cyan]1. Random Property with Full Context (1 query):[/cyan]")
    result1 = demo.demo_single_query_property()
    
    if result1.results:
        property = result1.results[0]
        console.print(f"   Property: {property.get('address', {}).get('street', 'Unknown')}")
        console.print(f"   Neighborhood: {property.get('neighborhood', {}).get('name', 'N/A')}")
        console.print(f"   Wikipedia Articles: {len(property.get('wikipedia_articles', []))}")
        console.print(f"   [green]Query Time: {result1.execution_time_ms}ms[/green]")
    else:
        console.print(f"   [yellow]No data in index yet - run data pipeline to populate[/yellow]")
        console.print(f"   [green]Query Time: {result1.execution_time_ms}ms[/green]")
    
    # Demo 2: Neighborhood search
    console.print("\n[cyan]2. Neighborhood Properties (1 query):[/cyan]")
    result2 = demo.demo_neighborhood_properties_simplified("Pacific Heights")
    console.print(f"   Found {result2.total_hits} properties")
    console.print(f"   [green]Query Time: {result2.execution_time_ms}ms[/green]")
    
    # Demo 3: Location search
    console.print("\n[cyan]3. Location Search (1 query):[/cyan]")
    result3 = demo.demo_location_search_simplified("San Francisco", "CA")
    console.print(f"   Found {result3.total_hits} properties")
    console.print(f"   [green]Query Time: {result3.execution_time_ms}ms[/green]")
    
    total_time = result1.execution_time_ms + result2.execution_time_ms + result3.execution_time_ms
    
    console.print("\n[green]✓ Denormalized index demo complete![/green]")
    console.print(f"[yellow]Total query time for 3 operations: {total_time}ms[/yellow]")
    console.print("[yellow]All data retrieved with single queries per operation[/yellow]")
    
    # Return combined results
    all_results = []
    if result1.results:
        all_results.extend(result1.results)
    if result2.results:
        all_results.extend(result2.results)
    if result3.results:
        all_results.extend(result3.results)
    
    return DemoQueryResult(
        query_name="Property Relationships via Denormalized Index",
        execution_time_ms=total_time,
        total_hits=result1.total_hits + result2.total_hits + result3.total_hits,
        returned_hits=len(all_results),
        results=all_results[:10],  # Limit to 10 for display
        query_dsl={
            "description": "Denormalized index enables single-query retrieval",
            "comparison": {
                "before": "3-6 queries, 200+ lines of code",
                "after": "1 query, ~20 lines of code",
                "performance": "Single-query retrieval"
            }
        }
    )


def main():
    """Standalone entry point for the simplified demo."""
    from ..config import AppConfig
    from ..infrastructure.elasticsearch_client import ElasticsearchClientFactory
    
    console.print("\n[bold cyan]Simplified Property Relationships Demo[/bold cyan]")
    console.print("=" * 70)
    
    # Load configuration
    try:
        config = AppConfig.from_yaml("real_estate_search/config.yaml")
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        return
    
    # Create Elasticsearch client
    try:
        client_factory = ElasticsearchClientFactory(config.elasticsearch)
        es_client = client_factory.create_client()
    except Exception as e:
        console.print(f"[red]Failed to create Elasticsearch client: {e}[/red]")
        return
    
    # Check connection
    if not es_client.ping():
        console.print("[red]Cannot connect to Elasticsearch[/red]")
        return
    
    console.print("[green]✓ Connected to Elasticsearch[/green]")
    
    # Check if property_relationships index exists
    if not es_client.indices.exists(index=IndexName.PROPERTY_RELATIONSHIPS):
        console.print("[yellow]Warning: property_relationships index does not exist[/yellow]")
        console.print("[yellow]Run the data pipeline with relationship building enabled[/yellow]")
        return
    
    # Run the demo
    demo_simplified_relationships(es_client)


if __name__ == "__main__":
    main()