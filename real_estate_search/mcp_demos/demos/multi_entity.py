"""Multi-entity search demos using MCP client."""

import asyncio
from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from ..client.client import get_mcp_client
from ..utils.models import (
    PropertySearchRequest,
    WikipediaSearchRequest,
    SearchType,
    DemoResult
)


console = Console()


async def demo_multi_entity_search(
    query: str = "Victorian architecture San Francisco"
) -> DemoResult:
    """Demo 5: Multi-Entity Search.
    
    Search across both properties and Wikipedia articles simultaneously,
    demonstrating parallel search capabilities across different entity types.
    
    Args:
        query: Search query to use for both properties and Wikipedia
        
    Returns:
        Demo execution result
    """
    console.print(Panel.fit(
        f"[bold cyan]Demo 5: Multi-Entity Search[/bold cyan]\n"
        f"Query: '{query}'\n"
        f"Searching: Properties + Wikipedia",
        border_style="cyan"
    ))
    
    client = get_mcp_client()
    
    try:
        # Create search requests
        property_request = PropertySearchRequest(
            query=query,
            size=3,
            search_type=SearchType.HYBRID
        )
        
        wikipedia_request = WikipediaSearchRequest(
            query=query,
            search_in="full",
            size=3,
            search_type=SearchType.HYBRID
        )
        
        # Execute searches in parallel
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Searching multiple indices...", total=None)
            
            property_task = asyncio.create_task(client.search_properties(property_request))
            wikipedia_task = asyncio.create_task(client.search_wikipedia(wikipedia_request))
            
            property_response, wikipedia_response = await asyncio.gather(
                property_task,
                wikipedia_task
            )
            
            progress.update(task, completed=True)
        
        # Display results side by side
        console.print("\n[bold yellow]🔍 Multi-Entity Search Results[/bold yellow]\n")
        
        # Properties panel
        property_text = Text()
        property_text.append("🏠 Properties\n\n", style="bold cyan")
        
        if property_response.properties:
            for idx, prop in enumerate(property_response.properties[:3], 1):
                property_text.append(f"{idx}. ", style="yellow")
                property_text.append(f"{prop.property_type} - ${prop.price:,.0f}\n", style="green")
                property_text.append(f"   {prop.address.street}, {prop.address.city}\n", style="dim")
                property_text.append(f"   {prop.bedrooms} bed, {prop.bathrooms} bath", style="dim")
                if prop.square_feet:
                    property_text.append(f", {prop.square_feet} sq ft", style="dim")
                property_text.append("\n\n")
        else:
            property_text.append("No properties found", style="dim red")
        
        property_panel = Panel(
            property_text,
            title=f"Found {property_response.total} properties",
            border_style="green"
        )
        
        # Wikipedia panel
        wiki_text = Text()
        wiki_text.append("📚 Wikipedia Articles\n\n", style="bold cyan")
        
        if wikipedia_response.articles:
            for idx, article in enumerate(wikipedia_response.articles[:3], 1):
                wiki_text.append(f"{idx}. ", style="yellow")
                wiki_text.append(f"{article.title}\n", style="green")
                if article.summary:
                    wiki_text.append(f"   {article.summary[:100]}...\n", style="dim")
                if article.categories:
                    cats = ", ".join(article.categories[:3])
                    wiki_text.append(f"   Categories: {cats}\n", style="blue dim")
                wiki_text.append("\n")
        else:
            wiki_text.append("No articles found", style="dim red")
        
        wiki_panel = Panel(
            wiki_text,
            title=f"Found {wikipedia_response.total} articles",
            border_style="blue"
        )
        
        # Display panels side by side
        console.print(Columns([property_panel, wiki_panel], equal=True, expand=True))
        
        # Summary statistics
        total_time = property_response.search_time_ms + wikipedia_response.search_time_ms
        total_results = property_response.total + wikipedia_response.total
        
        console.print(Panel(
            f"[green]✓[/green] Search completed\n"
            f"Total results: {total_results}\n"
            f"Properties: {property_response.total} in {property_response.search_time_ms}ms\n"
            f"Wikipedia: {wikipedia_response.total} in {wikipedia_response.search_time_ms}ms\n"
            f"Total time: {total_time}ms",
            title="Search Summary",
            border_style="yellow"
        ))
        
        return DemoResult(
            demo_name="Multi-Entity Search",
            success=True,
            execution_time_ms=total_time,
            total_results=total_results,
            returned_results=len(property_response.properties) + len(wikipedia_response.articles),
            sample_results=[
                {"type": "property", "data": prop.model_dump()} 
                for prop in property_response.properties[:2]
            ] + [
                {"type": "wikipedia", "data": article.model_dump()} 
                for article in wikipedia_response.articles[:2]
            ]
        )
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        return DemoResult(
            demo_name="Multi-Entity Search",
            success=False,
            execution_time_ms=0,
            total_results=0,
            returned_results=0,
            sample_results=[],
            error=str(e)
        )