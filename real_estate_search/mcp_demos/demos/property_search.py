"""Property search demos using MCP client."""

import asyncio
from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ..client.client import get_mcp_client
from ..utils.models import (
    PropertySearchRequest,
    PropertySearchResponse,
    Property,
    PropertyType,
    SearchType,
    DemoResult
)


console = Console()


async def demo_basic_property_search(query: str = "modern home with pool") -> DemoResult:
    """Demo 1: Basic property search using natural language.
    
    Core logic for executing a basic property search.
    """
    # Core client logic
    client = get_mcp_client()
    
    try:
        # Create and execute search
        request = PropertySearchRequest(
            query=query,
            size=5,
            search_type=SearchType.HYBRID
        )
        response = await client.search_properties(request)
        
        # Display logic at bottom
        _display_basic_search_results(query, response)
        
        return DemoResult(
            demo_name="Basic Property Search",
            success=True,
            execution_time_ms=response.execution_time_ms,
            total_results=response.total_results,
            returned_results=response.returned_results,
            sample_results=[prop.model_dump() for prop in response.properties[:3]]
        )
        
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        return DemoResult(
            demo_name="Basic Property Search",
            success=False,
            execution_time_ms=0,
            total_results=0,
            returned_results=0,
            sample_results=[],
            error=str(e)
        )


async def demo_property_filter(
    property_type: PropertyType = PropertyType.CONDO,
    min_price: float = 900000,
    max_price: float = 1400000,
    city: str = "San Francisco"
) -> DemoResult:
    """Demo 2: Filtered property search with specific criteria.
    
    Core logic for executing a filtered property search.
    """
    # Core client logic
    client = get_mcp_client()
    
    try:
        # Create and execute search
        # Note: search_properties only accepts query and size, not filters
        # We search for more results to increase chances of finding matches after filtering
        query = f"{property_type.value} in {city} between ${min_price:,.0f} and ${max_price:,.0f}"
        request = PropertySearchRequest(
            query=query,
            size=30,  # Increased to get more results for client-side filtering
            search_type=SearchType.HYBRID
        )
        response = await client.search_properties(request)
        
        # Filter results client-side based on criteria
        filtered_properties = _filter_properties(
            response.properties,
            property_type=property_type,
            min_price=min_price,
            max_price=max_price,
            city=city
        )
        
        # Display logic at bottom
        _display_filtered_search_results(
            property_type, min_price, max_price, city,
            filtered_properties, response.execution_time_ms
        )
        
        return DemoResult(
            demo_name="Filtered Property Search",
            success=True,
            execution_time_ms=response.execution_time_ms,
            total_results=len(filtered_properties),
            returned_results=len(filtered_properties),
            sample_results=[prop.model_dump() for prop in filtered_properties[:3]]
        )
        
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        return DemoResult(
            demo_name="Filtered Property Search",
            success=False,
            execution_time_ms=0,
            total_results=0,
            returned_results=0,
            sample_results=[],
            error=str(e)
        )


async def demo_location_search(city: str = "Oakland", state: str = "CA") -> DemoResult:
    """Demo 3: Location-specific property search.
    
    Core logic for searching properties in a specific location.
    """
    # Core client logic
    client = get_mcp_client()
    
    try:
        # Create and execute search
        query = f"properties in {city}, {state}"
        request = PropertySearchRequest(
            query=query,
            size=10,
            search_type=SearchType.HYBRID
        )
        response = await client.search_properties(request)
        
        # Display logic at bottom
        _display_location_search_results(city, state, response)
        
        return DemoResult(
            demo_name="Location Search",
            success=True,
            execution_time_ms=response.execution_time_ms,
            total_results=response.total_results,
            returned_results=response.returned_results,
            sample_results=[prop.model_dump() for prop in response.properties[:3]]
        )
        
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        return DemoResult(
            demo_name="Location Search",
            success=False,
            execution_time_ms=0,
            total_results=0,
            returned_results=0,
            sample_results=[],
            error=str(e)
        )


# ============================================================================
# Display Functions - Each demo has its own display logic
# ============================================================================

def _display_basic_search_results(query: str, response: PropertySearchResponse):
    """Display results for basic property search."""
    console.print(Panel.fit(
        f"[bold cyan]Demo 1: Basic Property Search[/bold cyan]\n"
        f"Query: '{query}'",
        border_style="cyan"
    ))
    
    if response.properties:
        table = Table(title="Search Results", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Type", style="green")
        table.add_column("Price", justify="right", style="yellow")
        table.add_column("Beds/Baths", justify="center")
        table.add_column("Location", style="blue")
        table.add_column("Score", justify="right", style="red")
        
        for prop in response.properties[:5]:
            table.add_row(
                prop.listing_id,
                prop.property_type,
                f"${prop.price:,.0f}",
                f"{prop.bedrooms}/{prop.bathrooms}",
                f"{prop.address.city}, {prop.address.state}",
                f"{prop.score:.2f}"
            )
        
        console.print(table)
        
        # Show sample property details
        if response.properties:
            sample = response.properties[0]
            console.print("\n[bold]Sample Property Details:[/bold]")
            console.print(Panel(
                f"[cyan]ID:[/cyan] {sample.listing_id}\n"
                f"[cyan]Type:[/cyan] {sample.property_type}\n"
                f"[cyan]Price:[/cyan] ${sample.price:,.0f}\n"
                f"[cyan]Bedrooms:[/cyan] {sample.bedrooms}\n"
                f"[cyan]Bathrooms:[/cyan] {sample.bathrooms}\n"
                f"[cyan]Square Feet:[/cyan] {sample.square_feet or 'N/A'}\n"
                f"[cyan]Description:[/cyan] {sample.description[:100]}...\n"
                f"[cyan]Features:[/cyan] {', '.join(sample.features[:3])}"
                f"{', ...' if len(sample.features) > 3 else ''}",
                title=f"Property: {sample.address.street}",
                border_style="green"
            ))
    
    console.print(f"\n[green]✓[/green] Found {response.total_results} properties in {response.execution_time_ms}ms")


def _display_filtered_search_results(
    property_type: PropertyType,
    min_price: float,
    max_price: float,
    city: str,
    properties: List[Property],
    execution_time_ms: int
):
    """Display results for filtered property search."""
    console.print(Panel.fit(
        f"[bold cyan]Demo 2: Filtered Property Search[/bold cyan]\n"
        f"Type: {property_type.value}\n"
        f"Price: ${min_price:,.0f} - ${max_price:,.0f}\n"
        f"City: {city}",
        border_style="cyan"
    ))
    
    if properties:
        table = Table(
            title=f"{property_type.value}s in {city}",
            show_header=True,
            header_style="bold magenta"
        )
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Price", justify="right", style="yellow")
        table.add_column("Beds", justify="center")
        table.add_column("Baths", justify="center")
        table.add_column("Sq Ft", justify="right")
        table.add_column("Address", style="blue")
        
        for prop in properties[:5]:
            table.add_row(
                prop.listing_id,
                f"${prop.price:,.0f}",
                str(prop.bedrooms),
                str(prop.bathrooms),
                str(prop.square_feet) if prop.square_feet else "N/A",
                prop.address.street
            )
        
        console.print(table)
        
        # Show price statistics
        prices = [p.price for p in properties]
        if prices:
            avg_price = sum(prices) / len(prices)
            min_found = min(prices)
            max_found = max(prices)
            
            console.print("\n[bold]Price Statistics:[/bold]")
            stats_text = Text()
            stats_text.append("Average: ", style="cyan")
            stats_text.append(f"${avg_price:,.0f}\n", style="yellow")
            stats_text.append("Range: ", style="cyan")
            stats_text.append(f"${min_found:,.0f} - ${max_found:,.0f}", style="yellow")
            console.print(stats_text)
    else:
        console.print("[yellow]No properties found matching criteria[/yellow]")
    
    console.print(f"\n[green]✓[/green] Found {len(properties)} condos in {city} within price range in {execution_time_ms}ms")


def _display_location_search_results(city: str, state: str, response: PropertySearchResponse):
    """Display results for location-specific search."""
    console.print(Panel.fit(
        f"[bold cyan]Demo 3: Location Search[/bold cyan]\n"
        f"Location: {city}, {state}",
        border_style="cyan"
    ))
    
    if response.properties:
        table = Table(
            title=f"Properties in {city}, {state}",
            show_header=True,
            header_style="bold magenta"
        )
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Type", style="green")
        table.add_column("Price", justify="right", style="yellow")
        table.add_column("Beds", justify="center")
        table.add_column("Baths", justify="center")
        table.add_column("Address", style="blue")
        
        for prop in response.properties[:5]:
            table.add_row(
                prop.listing_id,
                prop.property_type,
                f"${prop.price:,.0f}",
                str(prop.bedrooms),
                str(prop.bathrooms),
                prop.address.street
            )
        
        console.print(table)
    else:
        console.print(f"[yellow]No properties found in {city}, {state}[/yellow]")
    
    console.print(f"\n[green]✓[/green] Found {response.total_results} properties in {response.execution_time_ms}ms")


# ============================================================================
# Helper Functions
# ============================================================================

def _filter_properties(
    properties: List[Property],
    property_type: PropertyType = None,
    min_price: float = None,
    max_price: float = None,
    city: str = None
) -> List[Property]:
    """Filter properties based on criteria."""
    filtered = []
    for prop in properties:
        # Check property type
        if property_type and prop.property_type.lower() != property_type.value.lower():
            continue
        # Check price range
        if min_price and prop.price < min_price:
            continue
        if max_price and prop.price > max_price:
            continue
        # Check city
        if city and prop.address.city.lower() != city.lower():
            continue
        filtered.append(prop)
    return filtered