"""Location-based discovery demos using MCP client."""

import asyncio
from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.columns import Columns

from ..client.client import get_mcp_client
from ..utils.models import (
    PropertySearchRequest,
    PropertyType,
    SearchType,
    DemoResult
)


console = Console()


async def demo_location_based_discovery(
    city: str = "San Francisco",
    state: str = "CA",
    property_type: PropertyType = PropertyType.CONDO
) -> DemoResult:
    """Demo 7: Location-Based Discovery.
    
    Discover properties and Wikipedia information for a specific city,
    providing a comprehensive view of what's available in an area.
    
    Args:
        city: City to explore
        state: State code
        property_type: Type of properties to find
        
    Returns:
        Demo execution result
    """
    console.print(Panel.fit(
        f"[bold cyan]Demo 7: Location-Based Discovery[/bold cyan]\n"
        f"Exploring: {city}, {state}\n"
        f"Property Type: {property_type.value}",
        border_style="cyan"
    ))
    
    client = get_mcp_client()
    
    try:
        console.print(f"\n[yellow]🔍 Discovering {city}, {state}...[/yellow]\n")
        
        # Create property search request
        property_request = PropertySearchRequest(
            query=f"{property_type.value} in {city}",
            property_type=property_type,
            city=city,
            state=state,
            size=5,
            search_type=SearchType.HYBRID
        )
        
        # Search for properties and Wikipedia info in parallel
        property_task = asyncio.create_task(client.search_properties(property_request))
        wiki_task = asyncio.create_task(client.search_wikipedia_by_location(
            city=city,
            state=state,
            size=5
        ))
        
        property_response, wiki_response = await asyncio.gather(
            property_task,
            wiki_task
        )
        
        # Create location overview
        overview = Text()
        overview.append(f"📍 {city}, {state} Overview\n\n", style="bold yellow")
        
        # Property market summary
        if property_response.properties:
            prices = [p.price for p in property_response.properties]
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            
            overview.append("🏠 Property Market:\n", style="bold cyan")
            overview.append(f"   • {property_response.total_results} {property_type.value}s available\n")
            overview.append(f"   • Price range: ${min_price:,.0f} - ${max_price:,.0f}\n")
            overview.append(f"   • Average price: ${avg_price:,.0f}\n\n")
        
        # Wikipedia context summary
        if wiki_response.get("articles"):
            overview.append("📚 Local Context:\n", style="bold cyan")
            topics = set()
            for article in wiki_response["articles"][:5]:
                if article.get("key_topics"):
                    topics.update(article["key_topics"][:3])
            
            if topics:
                overview.append(f"   • Key topics: {', '.join(list(topics)[:6])}\n")
            overview.append(f"   • {wiki_response['total_results']} Wikipedia articles about the area\n")
        
        console.print(Panel(overview, border_style="yellow"))
        
        # Display properties
        if property_response.properties:
            console.print(f"\n[bold green]🏠 Available {property_type.value}s:[/bold green]\n")
            
            property_table = Table(show_header=True, header_style="bold magenta")
            property_table.add_column("Price", justify="right", style="yellow")
            property_table.add_column("Beds", justify="center")
            property_table.add_column("Baths", justify="center")
            property_table.add_column("Sq Ft", justify="right")
            property_table.add_column("Address", style="cyan")
            property_table.add_column("Features", style="green")
            
            for prop in property_response.properties[:5]:
                features = ", ".join(prop.features[:2]) if prop.features else "N/A"
                property_table.add_row(
                    f"${prop.price:,.0f}",
                    str(prop.bedrooms),
                    str(prop.bathrooms),
                    str(prop.square_feet) if prop.square_feet else "N/A",
                    prop.address.street,
                    features
                )
            
            console.print(property_table)
        
        # Display Wikipedia highlights
        if wiki_response.get("articles"):
            console.print(f"\n[bold blue]📍 Notable Places & Information:[/bold blue]\n")
            
            for idx, article in enumerate(wiki_response["articles"][:3], 1):
                wiki_panel = Panel(
                    f"{article.get('short_summary', 'No summary available')[:200]}...\n\n"
                    f"[dim]Topics: {', '.join(article.get('key_topics', [])[:5])}[/dim]",
                    title=f"[{idx}] {article['title']}",
                    border_style="blue"
                )
                console.print(wiki_panel)
        
        # Discovery summary
        total_discoveries = property_response.total_results + wiki_response.get("total_results", 0)
        total_time = property_response.execution_time_ms + wiki_response.get("execution_time_ms", 0)
        
        console.print(Panel(
            f"[green]✓[/green] Location discovery completed\n\n"
            f"📊 Discovery Summary:\n"
            f"   • Properties found: {property_response.total_results}\n"
            f"   • Wikipedia articles: {wiki_response.get('total_results', 0)}\n"
            f"   • Total discoveries: {total_discoveries}\n"
            f"   • Search time: {total_time}ms\n\n"
            f"💡 Tip: This location has {'high' if property_response.total_results > 10 else 'moderate' if property_response.total_results > 5 else 'limited'} "
            f"property availability and {'rich' if wiki_response.get('total_results', 0) > 10 else 'good' if wiki_response.get('total_results', 0) > 5 else 'basic'} "
            f"contextual information.",
            title="Discovery Complete",
            border_style="green"
        ))
        
        return DemoResult(
            demo_name="Location-Based Discovery",
            success=True,
            execution_time_ms=total_time,
            total_results=total_discoveries,
            returned_results=len(property_response.properties) + len(wiki_response.get("articles", [])),
            sample_results=[
                {
                    "location": {"city": city, "state": state},
                    "properties": [p.model_dump() for p in property_response.properties[:2]],
                    "wikipedia": wiki_response.get("articles", [])[:2]
                }
            ]
        )
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        return DemoResult(
            demo_name="Location-Based Discovery",
            success=False,
            execution_time_ms=0,
            total_results=0,
            returned_results=0,
            sample_results=[],
            error=str(e)
        )