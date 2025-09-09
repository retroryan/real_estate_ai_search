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

from .result_models import MixedEntityResult
from ..models import WikipediaArticle
from ..models import PropertyListing
from ..converters import PropertyConverter
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
                property_results=[PropertyConverter.from_elasticsearch(property_data)],
                wikipedia_results=[WikipediaArticle(
                    page_id=str(a.get('page_id', '')),
                    title=a.get('title', ''),
                    summary=a.get('summary', ''),
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
                        "property": "Complete property data",
                        "neighborhood": "Embedded neighborhood data",
                        "wikipedia_articles": f"{len(wikipedia_articles)} articles"
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
            
            return MixedEntityResult(
                query_name=f"Neighborhood: {neighborhood_name}",
                execution_time_ms=execution_time,
                total_hits=response['hits']['total']['value'],
                returned_hits=len(results),
                property_results=PropertyConverter.from_elasticsearch_batch(results),
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
            Properties with complete context
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
                property_results=PropertyConverter.from_elasticsearch_batch(results),
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
    
    console.print("\n[bold yellow]Key Benefits:[/bold yellow]")
    console.print("• Single query retrieves all data")
    console.print("• No JOIN operations required")
    console.print("• Optimized for read performance")
    console.print("• Simplified application logic")
    console.print("• Consistent data snapshot")


def demo_simplified_relationships(es_client: Elasticsearch) -> MixedEntityResult:
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
    
    console.print("\n[bold cyan]Running Denormalized Index Queries[/bold cyan]")
    console.print("=" * 70)
    
    # Demo 1: Single property with full context
    console.print("\n[bold]Query 1: Random Property with Full Context[/bold]")
    result1 = demo.demo_single_query_property()
    
    # Display query
    query_panel = Panel(
        f"""[cyan]Query Type:[/cyan] Single document retrieval
[cyan]Index:[/cyan] property_relationships  
[cyan]Method:[/cyan] Random selection with function_score

[yellow]Elasticsearch Query:[/yellow]
{{
  "query": {{
    "function_score": {{
      "query": {{"match_all": {{}}}},
      "random_score": {{"seed": 42}}
    }}
  }},
  "size": 1
}}""",
        title="[bold cyan]Query[/bold cyan]",
        border_style="cyan"
    )
    console.print(query_panel)
    
    if result1.property_results:
        property = result1.property_results[0].__dict__
        
        # Create results table
        results_table = Table(title="Query Results", box=box.ROUNDED)
        results_table.add_column("Field", style="cyan")
        results_table.add_column("Value", style="white")
        
        results_table.add_row("Property Address", property.get('address', {}).get('street', 'Unknown'))
        results_table.add_row("City", f"{property.get('address', {}).get('city', 'N/A')}, {property.get('address', {}).get('state', 'N/A')}")
        results_table.add_row("Price", f"${property.get('price', 0):,.0f}" if property.get('price') else 'N/A')
        results_table.add_row("Bedrooms/Bathrooms", f"{property.get('bedrooms', 'N/A')} bed / {property.get('bathrooms', 'N/A')} bath")
        results_table.add_row("Neighborhood", property.get('neighborhood', {}).get('name', 'N/A'))
        results_table.add_row("Wikipedia Articles", str(len(property.get('wikipedia_articles', []))))
        results_table.add_row("[green]Query Time[/green]", f"[green]{result1.execution_time_ms}ms[/green]")
        
        console.print(results_table)
    else:
        console.print(f"[yellow]No data in index yet - run data pipeline to populate[/yellow]")
        console.print(f"[green]Query Time: {result1.execution_time_ms}ms[/green]")
    
    # Demo 2: Neighborhood search
    console.print("\n[bold]Query 2: Neighborhood Properties Search[/bold]")
    result2 = demo.demo_neighborhood_properties_simplified("Pacific Heights")
    
    query_panel2 = Panel(
        f"""[cyan]Query Type:[/cyan] Neighborhood filtering
[cyan]Index:[/cyan] property_relationships
[cyan]Target:[/cyan] Pacific Heights

[yellow]Elasticsearch Query:[/yellow]
{{
  "query": {{
    "match": {{
      "neighborhood.name": "Pacific Heights"
    }}
  }},
  "size": 10
}}""",
        title="[bold cyan]Query[/bold cyan]",
        border_style="cyan"
    )
    console.print(query_panel2)
    
    results_panel2 = Panel(
        f"""[cyan]Properties Found:[/cyan] {result2.total_hits}
[cyan]Results Returned:[/cyan] {min(result2.returned_hits, 10)}
[green]Query Time:[/green] {result2.execution_time_ms}ms""",
        title="[bold]Results Summary[/bold]",
        border_style="green"
    )
    console.print(results_panel2)
    
    # Demo 3: Location search
    console.print("\n[bold]Query 3: Location-Based Search[/bold]")
    result3 = demo.demo_location_search_simplified("Oakland", "CA")
    
    query_panel3 = Panel(
        f"""[cyan]Query Type:[/cyan] Location filtering with price sort
[cyan]Index:[/cyan] property_relationships
[cyan]Location:[/cyan] Oakland, CA

[yellow]Elasticsearch Query:[/yellow]
{{
  "query": {{
    "bool": {{
      "filter": [
        {{"term": {{"address.city": "oakland"}}}},
        {{"term": {{"address.state": "CA"}}}}
      ]
    }}
  }},
  "size": 5,
  "sort": [{{"price": {{"order": "desc"}}}}]
}}""",
        title="[bold cyan]Query[/bold cyan]",
        border_style="cyan"
    )
    console.print(query_panel3)
    
    results_panel3 = Panel(
        f"""[cyan]Properties Found:[/cyan] {result3.total_hits}
[cyan]Results Returned:[/cyan] {min(result3.returned_hits, 5)}
[green]Query Time:[/green] {result3.execution_time_ms}ms""",
        title="[bold]Results Summary[/bold]",
        border_style="green"
    )
    console.print(results_panel3)
    
    total_time = result1.execution_time_ms + result2.execution_time_ms + result3.execution_time_ms
    
    # Final summary
    console.print("\n" + "=" * 70)
    summary_panel = Panel(
        f"""[green]✓ Denormalized index demo complete![/green]

[yellow]Performance Summary:[/yellow]
• Total queries executed: 3
• Total query time: {total_time}ms
• Average query time: {total_time/3:.1f}ms

[cyan]Key Achievement:[/cyan]
All property data, neighborhood information, and Wikipedia articles
retrieved with single queries - no JOINs or multiple lookups needed!""",
        title="[bold green]Demo Complete[/bold green]",
        border_style="green"
    )
    console.print(summary_panel)
    
    # Return combined results
    all_results = []
    if result1.property_results:
        all_results.extend([p.__dict__ for p in result1.property_results])
    if result2.property_results:
        all_results.extend([p.__dict__ for p in result2.property_results])
    if result3.property_results:
        all_results.extend([p.__dict__ for p in result3.property_results])
    
    return MixedEntityResult(
        query_name="Property Relationships via Denormalized Index",
        execution_time_ms=total_time,
        total_hits=result1.total_hits + result2.total_hits + result3.total_hits,
        returned_hits=len(all_results),
        property_results=PropertyConverter.from_elasticsearch_batch([r for r in all_results[:10] if 'listing_id' in r]),
        wikipedia_results=[],
        neighborhood_results=[],  # Limit to 10 for display
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