"""Wikipedia search demos using MCP client."""

import asyncio
from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns

from ..client.client import get_mcp_client
from ..utils.models import (
    WikipediaSearchRequest,
    SearchType,
    DemoResult
)


console = Console()


async def demo_wikipedia_location_context(
    city: str = "San Francisco",
    state: str = "CA"
) -> DemoResult:
    """Demo 4: Wikipedia Location Context.
    
    Find Wikipedia articles about a specific location to understand
    neighborhood context, landmarks, and local attractions.
    
    Args:
        city: City to search for
        state: State code
        
    Returns:
        Demo execution result
    """
    console.print(Panel.fit(
        f"[bold cyan]Demo 4: Wikipedia Location Context[/bold cyan]\n"
        f"Location: {city}, {state}",
        border_style="cyan"
    ))
    
    client = get_mcp_client()
    
    try:
        # Use location-specific search
        result = await client.search_wikipedia_by_location(
            city=city,
            state=state,
            size=5
        )
        
        if result.get("articles"):
            # Display location context
            console.print(f"\n[bold]📍 Location Context for {city}, {state}:[/bold]\n")
            
            for idx, article in enumerate(result["articles"][:5], 1):
                # Create a panel for each article
                content = Text()
                content.append(f"📄 {article['title']}\n", style="bold yellow")
                
                if article.get("short_summary"):
                    content.append(f"{article['short_summary'][:200]}...\n", style="dim")
                
                if article.get("key_topics"):
                    topics = ", ".join(article["key_topics"][:5])
                    content.append(f"\n🏷️  Topics: ", style="cyan")
                    content.append(topics, style="blue")
                
                if article.get("location_match", {}).get("coordinates"):
                    coords = article["location_match"]["coordinates"]
                    content.append(f"\n📍 Coordinates: ", style="cyan")
                    content.append(f"({coords['lat']:.4f}, {coords['lon']:.4f})", style="green")
                
                console.print(Panel(
                    content,
                    title=f"[{idx}] Relevance: {article.get('score', 0):.2f}",
                    border_style="blue"
                ))
        
        console.print(
            f"\n[green]✓[/green] Found {result['total_results']} articles "
            f"about {city} in {result['execution_time_ms']}ms"
        )
        
        return DemoResult(
            demo_name="Wikipedia Location Context",
            success=True,
            execution_time_ms=result["execution_time_ms"],
            total_results=result["total_results"],
            returned_results=result["returned_results"],
            sample_results=result.get("articles", [])[:3]
        )
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        return DemoResult(
            demo_name="Wikipedia Location Context",
            success=False,
            execution_time_ms=0,
            total_results=0,
            returned_results=0,
            sample_results=[],
            error=str(e)
        )


async def demo_wikipedia_search(
    query: str = "Golden Gate Bridge history architecture",
    search_in: str = "full"
) -> DemoResult:
    """Demo 3: Wikipedia Article Search.
    
    Search Wikipedia articles with natural language queries,
    demonstrating different search modes (full, summaries, chunks).
    
    Args:
        query: Search query
        search_in: What to search (full, summaries, chunks)
        
    Returns:
        Demo execution result
    """
    console.print(Panel.fit(
        f"[bold cyan]Demo 3: Wikipedia Article Search[/bold cyan]\n"
        f"Query: '{query}'\n"
        f"Search in: {search_in}",
        border_style="cyan"
    ))
    
    client = get_mcp_client()
    
    try:
        request = WikipediaSearchRequest(
            query=query,
            search_in=search_in,
            size=5,
            search_type=SearchType.HYBRID
        )
        
        response = await client.search_wikipedia(request)
        
        if response.articles:
            table = Table(
                title="Wikipedia Search Results",
                show_header=True,
                header_style="bold magenta"
            )
            table.add_column("Title", style="cyan")
            table.add_column("Long Summary", style="green", max_width=50)
            table.add_column("Categories", style="yellow")
            table.add_column("Score", justify="right", style="red")
            
            for article in response.articles[:5]:
                categories = ", ".join(article.categories[:2]) if article.categories else "N/A"
                # Try long_summary first, then short_summary
                display_summary = getattr(article, 'long_summary', None) or getattr(article, 'short_summary', None)
                summary = display_summary[:100] + "..." if display_summary else "N/A"
                
                table.add_row(
                    article.title,
                    summary,
                    categories,
                    f"{article.score:.2f}" if article.score else "N/A"
                )
            
            console.print(table)
        
        console.print(
            f"\n[green]✓[/green] Found {response.total} articles "
            f"in {response.search_time_ms}ms"
        )
        
        return DemoResult(
            demo_name="Wikipedia Article Search",
            success=True,
            execution_time_ms=response.search_time_ms,
            total_results=response.total,
            returned_results=response.returned,
            sample_results=[article.model_dump() for article in response.articles[:3]]
        )
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        return DemoResult(
            demo_name="Wikipedia Article Search",
            success=False,
            execution_time_ms=0,
            total_results=0,
            returned_results=0,
            sample_results=[],
            error=str(e)
        )