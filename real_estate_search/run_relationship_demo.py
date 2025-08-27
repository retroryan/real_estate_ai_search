#!/usr/bin/env python3
"""
Run demo showing relationships between properties, neighborhoods, and Wikipedia data.

This script demonstrates how the real_estate_search module works with data
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

from real_estate_search.config import AppConfig
from real_estate_search.demo_queries import (
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


def main():
    """Run the relationship demos."""
    console.print("\n[bold cyan]Real Estate Search - Property, Neighborhood & Wikipedia Demo[/bold cyan]")
    console.print("=" * 70)
    
    # Load configuration
    config_path = Path("real_estate_search/config.yaml")
    if not config_path.exists():
        config_path = Path("config.yaml")
    
    config = AppConfig.from_yaml(config_path)
    
    # Create Elasticsearch client
    es_client = Elasticsearch(
        hosts=[f"{config.elasticsearch.host}:{config.elasticsearch.port}"],
        basic_auth=(config.elasticsearch.username, config.elasticsearch.password) if config.elasticsearch.username else None
    )
    
    # Check connection
    if not es_client.ping():
        console.print("[red]Cannot connect to Elasticsearch[/red]")
        return
    
    console.print("[green]✓ Connected to Elasticsearch[/green]")
    
    # Demo 1: Property with full context
    console.print("\n" + "="*70)
    console.print("[bold]Demo 1: Property with Full Neighborhood and Wikipedia Context[/bold]")
    console.print("="*70)
    
    result = demo_property_with_full_context(es_client)
    if result.results:
        display_property_with_context(result.results)
        console.print(f"\n[dim]Query took {result.execution_time_ms}ms[/dim]")
    else:
        console.print("[red]No data found[/red]")
    
    # Demo 2: Neighborhood with properties and Wikipedia
    console.print("\n" + "="*70)
    console.print("[bold]Demo 2: Neighborhood with All Properties and Wikipedia Articles[/bold]")
    console.print("="*70)
    
    result = demo_neighborhood_properties_and_wiki(es_client, "Pacific Heights")
    if result.results:
        display_neighborhood_with_properties(result.results)
        console.print(f"\n[dim]Found {result.returned_hits} total items[/dim]")
    else:
        console.print("[red]No data found for Pacific Heights[/red]")
    
    # Demo 3: Location Wikipedia context
    console.print("\n" + "="*70)
    console.print("[bold]Demo 3: Location-based Wikipedia Context for Properties[/bold]")
    console.print("="*70)
    
    result = demo_location_wikipedia_context(es_client, "San Francisco", "CA")
    if result.results:
        display_location_context(result.results, "San Francisco", "CA")
        console.print(f"\n[dim]Found {len([r for r in result.results if r.get('_entity_type') == 'property'])} properties and {len([r for r in result.results if r.get('_entity_type') == 'wikipedia'])} Wikipedia articles[/dim]")
    else:
        console.print("[red]No data found for San Francisco, CA[/red]")
    
    console.print("\n[green]Demo complete![/green]")


if __name__ == "__main__":
    main()