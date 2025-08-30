"""Search comparison demos using MCP client."""

import asyncio
from typing import Dict, Any, List, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text

from ..client.client import get_mcp_client
from ..utils.models import (
    PropertySearchRequest,
    SearchType,
    DemoResult
)


console = Console()


async def demo_semantic_vs_text_comparison(
    query: str = "cozy cottage with fireplace near parks"
) -> DemoResult:
    """Demo 6: Semantic vs Text Search Comparison.
    
    Compare semantic (embedding-based) search with traditional text search
    to demonstrate the differences in search approaches.
    
    Args:
        query: Natural language query to test
        
    Returns:
        Demo execution result
    """
    console.print(Panel.fit(
        f"[bold cyan]Demo 6: Semantic vs Text Search Comparison[/bold cyan]\n"
        f"Query: '{query}'",
        border_style="cyan"
    ))
    
    client = get_mcp_client()
    
    try:
        # Create requests for different search types
        semantic_request = PropertySearchRequest(
            query=query,
            size=5,
            search_type=SearchType.SEMANTIC
        )
        
        text_request = PropertySearchRequest(
            query=query,
            size=5,
            search_type=SearchType.TEXT
        )
        
        hybrid_request = PropertySearchRequest(
            query=query,
            size=5,
            search_type=SearchType.HYBRID
        )
        
        console.print("[yellow]Running searches with different algorithms...[/yellow]\n")
        
        # Execute all three search types
        semantic_task = asyncio.create_task(client.search_properties(semantic_request))
        text_task = asyncio.create_task(client.search_properties(text_request))
        hybrid_task = asyncio.create_task(client.search_properties(hybrid_request))
        
        semantic_response, text_response, hybrid_response = await asyncio.gather(
            semantic_task,
            text_task,
            hybrid_task
        )
        
        # Create comparison table
        comparison_table = Table(
            title="Search Algorithm Comparison",
            show_header=True,
            header_style="bold magenta"
        )
        comparison_table.add_column("Metric", style="cyan")
        comparison_table.add_column("Semantic", justify="center", style="green")
        comparison_table.add_column("Text/Keyword", justify="center", style="blue")
        comparison_table.add_column("Hybrid", justify="center", style="yellow")
        
        comparison_table.add_row(
            "Total Results",
            str(semantic_response.total),
            str(text_response.total),
            str(hybrid_response.total)
        )
        comparison_table.add_row(
            "Search Time (ms)",
            str(semantic_response.search_time_ms),
            str(text_response.search_time_ms),
            str(hybrid_response.search_time_ms)
        )
        comparison_table.add_row(
            "Top Score",
            f"{semantic_response.properties[0].score:.3f}" if (semantic_response.properties and semantic_response.properties[0].score is not None) else "N/A",
            f"{text_response.properties[0].score:.3f}" if (text_response.properties and text_response.properties[0].score is not None) else "N/A",
            f"{hybrid_response.properties[0].score:.3f}" if (hybrid_response.properties and hybrid_response.properties[0].score is not None) else "N/A"
        )
        
        console.print(comparison_table)
        
        # Show top results from each method
        console.print("\n[bold yellow]Top Results by Search Type:[/bold yellow]\n")
        
        # Semantic results
        semantic_text = Text()
        semantic_text.append("🧠 Semantic Search\n", style="bold green")
        semantic_text.append("(Understands meaning & context)\n\n", style="dim")
        
        for idx, prop in enumerate(semantic_response.properties[:3], 1):
            semantic_text.append(f"{idx}. {prop.property_type} - ${prop.price:,.0f}\n", style="green")
            semantic_text.append(f"   {prop.description[:50]}...\n", style="dim")
            semantic_text.append(f"   Score: {prop.score:.3f}\n\n" if prop.score is not None else "   Score: N/A\n\n", style="yellow dim")
        
        # Text results
        text_text = Text()
        text_text.append("📝 Text/Keyword Search\n", style="bold blue")
        text_text.append("(Matches exact words)\n\n", style="dim")
        
        for idx, prop in enumerate(text_response.properties[:3], 1):
            text_text.append(f"{idx}. {prop.property_type} - ${prop.price:,.0f}\n", style="blue")
            text_text.append(f"   {prop.description[:50]}...\n", style="dim")
            text_text.append(f"   Score: {prop.score:.3f}\n\n" if prop.score is not None else "   Score: N/A\n\n", style="yellow dim")
        
        # Hybrid results
        hybrid_text = Text()
        hybrid_text.append("🔄 Hybrid Search\n", style="bold yellow")
        hybrid_text.append("(Best of both approaches)\n\n", style="dim")
        
        for idx, prop in enumerate(hybrid_response.properties[:3], 1):
            hybrid_text.append(f"{idx}. {prop.property_type} - ${prop.price:,.0f}\n", style="yellow")
            hybrid_text.append(f"   {prop.description[:50]}...\n", style="dim")
            hybrid_text.append(f"   Score: {prop.score:.3f}\n\n" if prop.score is not None else "   Score: N/A\n\n", style="yellow dim")
        
        # Display results in columns
        console.print(Columns([
            Panel(semantic_text, border_style="green"),
            Panel(text_text, border_style="blue"),
            Panel(hybrid_text, border_style="yellow")
        ], equal=True, expand=True))
        
        # Analysis summary
        console.print(Panel(
            "[bold]Key Differences:[/bold]\n\n"
            "• [green]Semantic[/green]: Finds conceptually similar properties even without exact word matches\n"
            "• [blue]Text[/blue]: Precisely matches keywords but may miss relevant results with different wording\n"
            "• [yellow]Hybrid[/yellow]: Combines both approaches for balanced results\n\n"
            f"[bold]Recommendation:[/bold] Use [yellow]Hybrid[/yellow] for best overall results",
            title="Analysis",
            border_style="magenta"
        ))
        
        total_time = semantic_response.search_time_ms + text_response.search_time_ms + hybrid_response.search_time_ms
        
        return DemoResult(
            demo_name="Semantic vs Text Search Comparison",
            success=True,
            execution_time_ms=total_time,
            total_results=semantic_response.total + text_response.total + hybrid_response.total,
            returned_results=len(semantic_response.properties) + len(text_response.properties) + len(hybrid_response.properties),
            sample_results=[
                {"type": "semantic", "results": [p.model_dump() for p in semantic_response.properties[:2]]},
                {"type": "text", "results": [p.model_dump() for p in text_response.properties[:2]]},
                {"type": "hybrid", "results": [p.model_dump() for p in hybrid_response.properties[:2]]}
            ]
        )
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        return DemoResult(
            demo_name="Semantic vs Text Search Comparison",
            success=False,
            execution_time_ms=0,
            total_results=0,
            returned_results=0,
            sample_results=[],
            error=str(e)
        )