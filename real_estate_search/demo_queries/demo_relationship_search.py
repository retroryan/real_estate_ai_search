#!/usr/bin/env python3
"""
Demo showing relationships between properties, neighborhoods, and Wikipedia data.

This demonstrates how the real_estate_search module works with data
indexed by the data_pipeline, showing the full context available for each property.
"""

import logging
from pathlib import Path
from typing import Dict, Any

from elasticsearch import Elasticsearch
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from .models import DemoQueryResult
from .property_neighborhood_wiki import (
    demo_property_with_full_context,
    demo_neighborhood_properties_and_wiki,
    demo_location_wikipedia_context
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rich console for formatted output
console = Console()


def display_property_with_context(results: list) -> None:
    """Display property with its neighborhood and Wikipedia context."""
    property_data = None
    neighborhood_data = None
    wikipedia_articles = []
    
    # Separate results by type
    for result in results:
        entity_type = result.get('_entity_type', '')
        if entity_type == 'property':
            property_data = result
        elif entity_type == 'neighborhood':
            neighborhood_data = result
        elif 'wikipedia' in entity_type:
            wikipedia_articles.append(result)
    
    # Display property
    if property_data:
        console.print("\n[bold cyan]📍 Property Details[/bold cyan]")
        table = Table(box=box.ROUNDED, show_header=False)
        table.add_column("Field", style="yellow")
        table.add_column("Value", style="white")
        
        table.add_row("Address", f"{property_data.get('address', {}).get('street', 'N/A')}")
        table.add_row("City", f"{property_data.get('address', {}).get('city', 'N/A')}, {property_data.get('address', {}).get('state', 'N/A')}")
        table.add_row("Price", f"${property_data.get('price', 0):,.0f}")
        table.add_row("Type", property_data.get('property_type', 'N/A'))
        table.add_row("Bedrooms", str(property_data.get('bedrooms', 'N/A')))
        table.add_row("Bathrooms", str(property_data.get('bathrooms', 'N/A')))
        table.add_row("Square Feet", f"{property_data.get('square_feet', 0):,}")
        
        console.print(table)
    
    # Display neighborhood
    if neighborhood_data:
        console.print("\n[bold green]🏘️ Neighborhood Information[/bold green]")
        table = Table(box=box.ROUNDED, show_header=False)
        table.add_column("Field", style="yellow")
        table.add_column("Value", style="white")
        
        table.add_row("Name", neighborhood_data.get('name', 'N/A'))
        table.add_row("City", f"{neighborhood_data.get('city', 'N/A')}, {neighborhood_data.get('state', 'N/A')}")
        
        description = neighborhood_data.get('description', '')
        if description:
            table.add_row("Description", description[:200] + "...")
        
        amenities = neighborhood_data.get('amenities', [])
        if amenities:
            table.add_row("Amenities", ", ".join(amenities[:5]))
        
        demographics = neighborhood_data.get('demographics', {})
        if demographics:
            pop = demographics.get('population', 'N/A')
            table.add_row("Population", str(pop))
        
        console.print(table)
    
    # Display Wikipedia articles
    if wikipedia_articles:
        console.print("\n[bold blue]📚 Wikipedia Context[/bold blue]")
        table = Table(box=box.ROUNDED)
        table.add_column("Title", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Confidence", style="green")
        
        for article in wikipedia_articles:
            relationship = article.get('_relationship', 'related')
            confidence = article.get('_confidence', 0.0)
            table.add_row(
                article.get('title', 'N/A'),
                relationship,
                f"{confidence:.0%}" if confidence else "N/A"
            )
        
        console.print(table)


def display_neighborhood_with_properties(results: list) -> None:
    """Display neighborhood with all its properties and Wikipedia articles."""
    neighborhood_data = None
    properties = []
    wikipedia_articles = []
    
    # Separate results by type
    for result in results:
        entity_type = result.get('_entity_type', '')
        if entity_type == 'neighborhood':
            neighborhood_data = result
        elif entity_type == 'property':
            properties.append(result)
        elif entity_type == 'wikipedia':
            wikipedia_articles.append(result)
    
    # Display neighborhood header
    if neighborhood_data:
        console.print(f"\n[bold cyan]🏘️ {neighborhood_data.get('name', 'Unknown Neighborhood')}[/bold cyan]")
        console.print(f"[dim]{neighborhood_data.get('city', '')}, {neighborhood_data.get('state', '')}[/dim]")
        
        description = neighborhood_data.get('description', '')
        if description:
            console.print(f"\n{description[:300]}...")
    
    # Display properties
    if properties:
        console.print("\n[bold green]🏠 Properties in this Neighborhood[/bold green]")
        table = Table(box=box.ROUNDED)
        table.add_column("Address", style="white")
        table.add_column("Price", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("Beds/Baths", style="cyan")
        
        for prop in properties[:5]:
            table.add_row(
                prop.get('address', {}).get('street', 'N/A')[:30],
                f"${prop.get('price', 0):,.0f}",
                prop.get('property_type', 'N/A'),
                f"{prop.get('bedrooms', 0)}/{prop.get('bathrooms', 0)}"
            )
        
        console.print(table)
    
    # Display Wikipedia articles
    if wikipedia_articles:
        console.print("\n[bold blue]📚 Related Wikipedia Articles[/bold blue]")
        table = Table(box=box.ROUNDED)
        table.add_column("Title", style="cyan")
        table.add_column("Relationship", style="yellow")
        table.add_column("Confidence", style="green")
        
        for article in wikipedia_articles:
            table.add_row(
                article.get('title', 'N/A'),
                article.get('_relationship', 'related'),
                f"{article.get('_confidence', 0):.0%}"
            )
        
        console.print(table)


def display_location_context(results: list, city: str, state: str) -> None:
    """Display properties and Wikipedia articles for a location."""
    properties = []
    wikipedia_articles = []
    
    # Separate results by type
    for result in results:
        entity_type = result.get('_entity_type', '')
        if entity_type == 'property':
            properties.append(result)
        elif entity_type == 'wikipedia':
            wikipedia_articles.append(result)
    
    console.print(f"\n[bold cyan]📍 Location Context: {city}, {state}[/bold cyan]")
    
    # Display properties
    if properties:
        console.print("\n[bold green]🏠 Properties[/bold green]")
        table = Table(box=box.ROUNDED)
        table.add_column("Address", style="white")
        table.add_column("Price", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("Neighborhood", style="cyan")
        
        for prop in properties:
            table.add_row(
                prop.get('address', {}).get('street', 'N/A')[:30],
                f"${prop.get('price', 0):,.0f}",
                prop.get('property_type', 'N/A'),
                prop.get('neighborhood_id', 'N/A')[:15]
            )
        
        console.print(table)
    
    # Display Wikipedia articles
    if wikipedia_articles:
        console.print("\n[bold blue]📚 Wikipedia Articles about this Location[/bold blue]")
        table = Table(box=box.ROUNDED)
        table.add_column("Title", style="cyan")
        table.add_column("Summary", style="white")
        
        for article in wikipedia_articles[:5]:
            summary = article.get('summary', '')[:100] + "..." if article.get('summary') else 'N/A'
            table.add_row(
                article.get('title', 'N/A'),
                summary
            )
        
        console.print(table)


def demo_relationship_search(es_client: Elasticsearch) -> DemoQueryResult:
    """Run comprehensive demo showing property-neighborhood-Wikipedia relationships.
    
    Args:
        es_client: Elasticsearch client
        
    Returns:
        DemoQueryResult with combined search results
    """
    console.print("\n[bold cyan]Demo 9: Property, Neighborhood & Wikipedia Relationships[/bold cyan]")
    console.print("=" * 70)
    
    console.print("\n[dim]This demo demonstrates how the search system connects three data types:[/dim]")
    console.print("[dim]• Properties: Real estate listings with details and amenities[/dim]")
    console.print("[dim]• Neighborhoods: Contextual information about areas[/dim]")
    console.print("[dim]• Wikipedia: Encyclopedia articles providing rich location context[/dim]")
    console.print("\n[dim]The system uses relationship mappings to link these entities together,[/dim]")
    console.print("[dim]enriching property searches with comprehensive location intelligence.[/dim]")
    
    all_results = []
    
    # Demo Part 1: Property with full context
    console.print("\n[bold]Part 1: Property with Full Neighborhood and Wikipedia Context[/bold]")
    console.print("-" * 50)
    console.print("\n[dim italic]Query Process:[/dim italic]")
    console.print("[dim]1. Randomly selects a property from the index[/dim]")
    console.print("[dim]2. Fetches the neighborhood using the property's neighborhood_id[/dim]")
    console.print("[dim]3. Searches Wikipedia for articles about the property's city[/dim]")
    console.print("[dim]4. Ranks Wikipedia articles by relevance and relationship type[/dim]")
    console.print("[dim]5. Returns enriched property data with full location context[/dim]")
    
    result1 = demo_property_with_full_context(es_client)
    if result1.results:
        display_property_with_context(result1.results)
        console.print(f"\n[dim]Query execution time: {result1.execution_time_ms}ms[/dim]")
        console.print(f"[dim]Result shows: Property details + Neighborhood info + Related Wikipedia articles[/dim]")
        all_results.extend(result1.results)
    else:
        console.print("[yellow]No data found for property context demo[/yellow]")
    
    # Demo Part 2: Neighborhood with properties and Wikipedia
    console.print("\n[bold]Part 2: Neighborhood with All Properties and Wikipedia Articles[/bold]")
    console.print("-" * 50)
    console.print("\n[dim italic]Query Process:[/dim italic]")
    console.print("[dim]1. Searches for neighborhood by name: 'Pacific Heights'[/dim]")
    console.print("[dim]2. Retrieves all properties with matching neighborhood_id[/dim]")
    console.print("[dim]3. Finds Wikipedia articles mentioning the neighborhood[/dim]")
    console.print("[dim]4. Categorizes articles by type (primary, neighborhood, park, reference)[/dim]")
    console.print("[dim]5. Combines results showing the neighborhood ecosystem[/dim]")
    
    result2 = demo_neighborhood_properties_and_wiki(es_client, "Pacific Heights")
    if result2.results:
        display_neighborhood_with_properties(result2.results)
        console.print(f"\n[dim]Total items found: {result2.returned_hits}[/dim]")
        console.print(f"[dim]Result shows: Neighborhood overview + Sample properties + Related Wikipedia content[/dim]")
        all_results.extend(result2.results)
    else:
        console.print("[yellow]No data found for Pacific Heights[/yellow]")
    
    # Demo Part 3: Location Wikipedia context
    console.print("\n[bold]Part 3: Location-based Wikipedia Context for Properties[/bold]")
    console.print("-" * 50)
    console.print("\n[dim italic]Query Process:[/dim italic]")
    console.print("[dim]1. Multi-search across properties and Wikipedia indices[/dim]")
    console.print("[dim]2. Filters properties by city and state: San Francisco, CA[/dim]")
    console.print("[dim]3. Searches Wikipedia for articles about the location[/dim]")
    console.print("[dim]4. Uses text analysis to find location-specific content[/dim]")
    console.print("[dim]5. Merges results to show properties with city-wide context[/dim]")
    
    result3 = demo_location_wikipedia_context(es_client, "San Francisco", "CA")
    if result3.results:
        display_location_context(result3.results, "San Francisco", "CA")
        prop_count = len([r for r in result3.results if r.get('_entity_type') == 'property'])
        wiki_count = len([r for r in result3.results if r.get('_entity_type') == 'wikipedia'])
        console.print(f"\n[dim]Query results: {prop_count} properties and {wiki_count} Wikipedia articles[/dim]")
        console.print(f"[dim]Result shows: City-level property listings + Wikipedia articles about the location[/dim]")
        all_results.extend(result3.results)
    else:
        console.print("[yellow]No data found for San Francisco, CA[/yellow]")
    
    console.print("\n[green]✓ Demo 9 complete - Rich entity relationships demonstrated![/green]")
    console.print("\n[bold yellow]Key Insights:[/bold yellow]")
    console.print("[yellow]• Properties are enriched with neighborhood and Wikipedia data[/yellow]")
    console.print("[yellow]• Relationships are mapped using IDs and location matching[/yellow]")
    console.print("[yellow]• Wikipedia articles provide historical and cultural context[/yellow]")
    console.print("[yellow]• Multi-index searches enable comprehensive location intelligence[/yellow]")
    
    # Return combined results
    return DemoQueryResult(
        query_name="Demo 9: Property-Neighborhood-Wikipedia Relationships",
        query_description="Demonstrates comprehensive entity relationships by showing properties with neighborhood context and Wikipedia articles, illustrating how the system connects different data types",
        results=all_results[:20],  # Limit to 20 results for management display
        total_hits=len(all_results),
        returned_hits=min(20, len(all_results)),
        execution_time_ms=result1.execution_time_ms + result2.execution_time_ms + result3.execution_time_ms if result1.results else 0,
        query_dsl={"demo": "relationship_search", "parts": ["property_context", "neighborhood", "location"]},
        es_features=[
            "Entity Relationship Mapping - Connecting properties to neighborhoods to Wikipedia",
            "Foreign Key Lookups - Following neighborhood_id references",
            "Multi-Step Queries - Building context through sequential searches",
            "Cross-Index Joins - Combining data from 3 different indices",
            "Wikipedia Correlations - Confidence-scored article relationships",
            "Rich Metadata - Including relationship types and confidence scores"
        ],
        indexes_used=[
            "properties index - Primary real estate listings",
            "neighborhoods index - Area demographics and descriptions",
            "wikipedia index - Encyclopedia articles with location data",
            "Demonstrates full knowledge graph traversal"
        ]
    )


def main():
    """Standalone entry point for running the demo with rich visualization."""
    from ..config import AppConfig
    from ..infrastructure.elasticsearch_client import ElasticsearchClientFactory
    
    console.print("\n[bold cyan]Real Estate Search - Property, Neighborhood & Wikipedia Demo[/bold cyan]")
    console.print("=" * 70)
    
    # Load configuration
    config_path = Path("real_estate_search/config.yaml")
    if not config_path.exists():
        config_path = Path("config.yaml")
    
    try:
        config = AppConfig.from_yaml(config_path)
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        return
    
    # Create Elasticsearch client using factory
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
    
    # Run the demo
    demo_relationship_search(es_client)


if __name__ == "__main__":
    main()