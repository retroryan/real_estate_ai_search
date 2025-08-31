"""Property search demos using MCP client."""

import asyncio
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ..client.client import get_mcp_client
from ..utils.models import (
    PropertySearchRequest,
    PropertyType,
    SearchType,
    DemoResult
)


console = Console()


async def demo_basic_property_search(query: str = "modern home with pool") -> DemoResult:
    """Demo 1: Basic property search using natural language.
    
    This demo shows how to perform a simple semantic search for properties
    using the MCP server's property search tool.
    
    Args:
        query: Natural language search query
        
    Returns:
        Demo execution result
    """
    console.print(Panel.fit(
        f"[bold cyan]Demo 1: Basic Property Search[/bold cyan]\n"
        f"Query: '{query}'",
        border_style="cyan"
    ))
    
    client = get_mcp_client()
    
    try:
        # Create search request
        request = PropertySearchRequest(
            query=query,
            size=5,
            search_type=SearchType.HYBRID
        )
        
        # Execute search
        response = await client.search_properties(request)
        
        # Display results
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
                    f"{prop.score:.2f}" if prop.score else "N/A"
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
                    f"[cyan]Amenities:[/cyan] {', '.join(sample.amenities[:3])}"
                    f"{', ...' if len(sample.amenities) > 3 else ''}",
                    title=f"Property: {sample.address.street}",
                    border_style="green"
                ))
        
        console.print(f"\n[green]✓[/green] Found {response.total} properties in {response.search_time_ms}ms")
        
        return DemoResult(
            demo_name="Basic Property Search",
            success=True,
            execution_time_ms=response.search_time_ms,
            total_results=response.total,
            returned_results=response.returned,
            sample_results=[prop.model_dump() for prop in response.properties[:3]]
        )
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
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
    min_price: float = 800000,
    max_price: float = 1500000,
    city: str = "San Francisco"
) -> DemoResult:
    """Demo 2: Filtered property search with specific criteria.
    
    This demo shows how to search for properties with specific filters
    like property type, price range, and location.
    
    Args:
        property_type: Type of property to search for
        min_price: Minimum price filter
        max_price: Maximum price filter
        city: City to search in
        
    Returns:
        Demo execution result
    """
    console.print(Panel.fit(
        f"[bold cyan]Demo 2: Filtered Property Search[/bold cyan]\n"
        f"Type: {property_type.value}\n"
        f"Price: ${min_price:,.0f} - ${max_price:,.0f}\n"
        f"City: {city}",
        border_style="cyan"
    ))
    
    client = get_mcp_client()
    
    try:
        # Create filtered search request
        request = PropertySearchRequest(
            query="affordable home with amenities",
            property_type=property_type,
            min_price=min_price,
            max_price=max_price,
            city=city,
            size=10,
            search_type=SearchType.HYBRID
        )
        
        # Execute search
        response = await client.search_properties(request)
        
        # Display results
        if response.properties:
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
            
            for prop in response.properties[:5]:
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
            prices = [p.price for p in response.properties]
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
                console.print(Panel(stats_text, border_style="green"))
        
        console.print(
            f"\n[green]✓[/green] Found {response.total} {property_type.value.lower()}s "
            f"in {city} within price range in {response.search_time_ms}ms"
        )
        
        return DemoResult(
            demo_name="Filtered Property Search",
            success=True,
            execution_time_ms=response.search_time_ms,
            total_results=response.total,
            returned_results=response.returned,
            sample_results=[prop.model_dump() for prop in response.properties[:3]]
        )
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        return DemoResult(
            demo_name="Filtered Property Search",
            success=False,
            execution_time_ms=0,
            total_results=0,
            returned_results=0,
            sample_results=[],
            error=str(e)
        )


def run_demo(demo_number: int) -> None:
    """Run a specific demo by number.
    
    Args:
        demo_number: The demo number to run (1 or 2)
    """
    if demo_number == 1:
        result = asyncio.run(demo_basic_property_search())
    elif demo_number == 2:
        result = asyncio.run(demo_property_filter())
    else:
        console.print(f"[red]Error: Demo {demo_number} not found[/red]")
        return
    
    # Print summary
    console.print("\n" + "="*60)
    if result.success:
        console.print(f"[green]Demo completed successfully![/green]")
    else:
        console.print(f"[red]Demo failed: {result.error}[/red]")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        try:
            demo_num = int(sys.argv[1])
            run_demo(demo_num)
        except ValueError:
            console.print("[red]Please provide a valid demo number (1 or 2)[/red]")
    else:
        # Run all demos
        console.print("[bold yellow]Running all property search demos...[/bold yellow]\n")
        asyncio.run(demo_basic_property_search())
        console.print("\n" + "="*60 + "\n")
        asyncio.run(demo_property_filter())