"""Natural language semantic search demo for MCP client."""

import asyncio
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from real_estate_search.mcp_demos.client.client_factory import create_client_from_config

console = Console()


async def demo_natural_language_semantic_search(
    query: str = "cozy family home near good schools and parks"
):
    """Demo the natural language semantic search tool.
    
    Args:
        query: Natural language query to test
    """
    console.print(Panel.fit(
        f"[bold green]Demo: Natural Language Semantic Search[/bold green]\n"
        f"[blue]Query: '{query}'[/blue]",
        border_style="green"
    ))

    # Create MCP client
    config_path = Path("real_estate_search/mcp_demos/config.yaml")
    client = create_client_from_config(config_path=config_path)

    try:
        # Call the natural language search tool
        response = await client.call_tool(
            "search_properties",
            {
                "query": query,
                "size": 8,
                "include_location_extraction": True
            }
        )

        if not response.success:
            console.print(f"[red]✗ Error: {response.error}[/red]")
            return

        data = response.data
        console.print(f"[green]✓ Found {data['returned_hits']} properties in {data['execution_time_ms']}ms[/green]")

        # Display search features
        if 'search_features' in data:
            console.print("\n[bold blue]Search Features Used:[/bold blue]")
            for feature in data['search_features']:
                console.print(f"  • {feature}")

        # Display results table
        if data['results']:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="dim")
            table.add_column("Type", style="cyan")
            table.add_column("Price", justify="right", style="green")
            table.add_column("Beds/Baths", justify="center")
            table.add_column("Location", style="blue")
            table.add_column("Score", justify="right", style="yellow")

            for result in data['results'][:5]:  # Show top 5
                price = f"${result.get('price', 0):,.0f}" if result.get('price') else "N/A"
                beds = result.get('bedrooms', '?')
                baths = result.get('bathrooms', '?')
                city = result.get('address', {}).get('city', 'Unknown') if isinstance(result.get('address'), dict) else 'Unknown'
                state = result.get('address', {}).get('state', '') if isinstance(result.get('address'), dict) else ''
                location = f"{city}, {state}".strip(', ')
                score = f"{result.get('_score', 0):.3f}" if result.get('_score') is not None else "N/A"
                
                table.add_row(
                    result.get('listing_id', 'N/A'),
                    result.get('property_type', 'Unknown'),
                    price,
                    f"{beds}/{baths}",
                    location,
                    score
                )

            console.print("\n[bold]Search Results[/bold]")
            console.print(table)

            # Show sample property details
            first_result = data['results'][0]
            if 'description' in first_result:
                console.print(Panel(
                    f"[bold]Sample Property:[/bold] {first_result.get('listing_id', 'Unknown')}\n"
                    f"[dim]{first_result.get('description', 'No description')[:200]}...[/dim]",
                    title="Property Description",
                    border_style="blue"
                ))

    except Exception as e:
        console.print(f"[red]✗ Unexpected error: {str(e)}[/red]")


async def demo_natural_language_examples():
    """Demo multiple natural language search examples."""
    console.print(Panel.fit(
        "[bold green]Demo: Natural Language Search Examples[/bold green]\n"
        "[blue]Running 5 diverse example queries to show AI capabilities[/blue]",
        border_style="green"
    ))

    # Create MCP client
    config_path = Path("real_estate_search/mcp_demos/config.yaml")
    client = create_client_from_config(config_path=config_path)

    try:
        # Call the examples search
        response = await client.call_tool(
            "search_properties",
            {
                "query": "modern home with pool",  # Example query
                "size": 3,
                "include_location_extraction": True
            }
        )

        if not response.success:
            console.print(f"[red]✗ Error: {response.error}[/red]")
            return

        data = response.data
        console.print(f"[green]✓ Processed {data['returned_hits']} example queries in {data['execution_time_ms']}ms[/green]")

        # Display search features
        if 'search_features' in data:
            console.print("\n[bold blue]Capabilities Demonstrated:[/bold blue]")
            for feature in data['search_features']:
                console.print(f"  • {feature}")

        # Display example results
        if data['results']:
            console.print("\n[bold]Example Query Results[/bold]")
            
            for i, example in enumerate(data['results'], 1):
                query = example.get('query', 'Unknown query')
                top_match = example.get('top_match', {})
                score = example.get('score', 0)
                query_time = example.get('query_time_ms', 0)
                
                # Create a panel for each example
                price = f"${top_match.get('price', 0):,.0f}" if top_match.get('price') else "N/A"
                property_type = top_match.get('property_type', 'Unknown')
                address = top_match.get('address', {})
                location = f"{address.get('city', 'Unknown')}, {address.get('state', '')}" if isinstance(address, dict) else "Unknown"
                
                panel_content = (
                    f"[bold blue]Query {i}:[/bold blue] {query}\n"
                    f"[dim]Found in {query_time:.1f}ms[/dim]\n\n"
                    f"[bold]Top Match:[/bold] {top_match.get('listing_id', 'N/A')}\n"
                    f"Type: {property_type} | Price: {price} | Location: {location}\n"
                    f"Similarity Score: {score:.3f}"
                )
                
                console.print(Panel(
                    panel_content,
                    title=f"Example {i}",
                    border_style="cyan"
                ))

    except Exception as e:
        console.print(f"[red]✗ Unexpected error: {str(e)}[/red]")


async def demo_semantic_vs_keyword_comparison(
    query: str = "stunning views from modern kitchen"
):
    """Demo semantic vs keyword search comparison."""
    console.print(Panel.fit(
        f"[bold green]Demo: Semantic vs Keyword Search Comparison[/bold green]\n"
        f"[blue]Query: '{query}'[/blue]",
        border_style="green"
    ))

    # Create MCP client
    config_path = Path("real_estate_search/mcp_demos/config.yaml")
    client = create_client_from_config(config_path=config_path)

    try:
        # Call the comparison search
        response = await client.call_tool(
            "search_properties",
            {
                "query": query,
                "size": 5,
                "include_location_extraction": True
            }
        )

        if not response.success:
            console.print(f"[red]✗ Error: {response.error}[/red]")
            return

        data = response.data
        console.print(f"[green]✓ Comparison completed in {data['execution_time_ms']}ms[/green]")

        semantic = data.get('semantic', {})
        keyword = data.get('keyword', {})
        comparison = data.get('comparison', {})

        # Create comparison table
        comp_table = Table(show_header=True, header_style="bold magenta")
        comp_table.add_column("Metric", style="cyan")
        comp_table.add_column("Semantic (AI)", style="blue")
        comp_table.add_column("Keyword (Traditional)", style="yellow")

        comp_table.add_row(
            "Search Type", 
            semantic.get('search_type', 'N/A'),
            keyword.get('search_type', 'N/A')
        )
        comp_table.add_row(
            "Total Hits", 
            str(semantic.get('total_hits', 0)),
            str(keyword.get('total_hits', 0))
        )
        comp_table.add_row(
            "Execution Time",
            f"{semantic.get('execution_time_ms', 0):.1f}ms",
            f"{keyword.get('execution_time_ms', 0):.1f}ms"
        )
        comp_table.add_row(
            "Top Score",
            f"{semantic.get('top_score', 0):.3f}",
            f"{keyword.get('top_score', 0):.3f}"
        )

        console.print("\n[bold]Search Method Comparison[/bold]")
        console.print(comp_table)

        # Show overlap analysis
        console.print(f"\n[bold blue]Result Overlap Analysis:[/bold blue]")
        console.print(f"  • Results in both searches: {comparison.get('overlap_count', 0)}")
        console.print(f"  • Unique to semantic: {comparison.get('unique_to_semantic', 0)}")
        console.print(f"  • Unique to keyword: {comparison.get('unique_to_keyword', 0)}")

        # Show recommendations
        if comparison.get('recommendation'):
            console.print(f"\n[bold green]Recommendation:[/bold green]")
            console.print(f"  {comparison['recommendation']}")

    except Exception as e:
        console.print(f"[red]✗ Unexpected error: {str(e)}[/red]")


# Main demo runner
async def run_all_natural_language_demos():
    """Run all natural language search demos."""
    console.print("\n🚀 [bold magenta]Natural Language Semantic Search Demos[/bold magenta] 🚀\n")
    
    # Demo 1: Basic semantic search
    await demo_natural_language_semantic_search("cozy family home near good schools and parks")
    
    console.print("\n" + "="*80 + "\n")
    
    # Demo 2: Multiple examples
    await demo_natural_language_examples()
    
    console.print("\n" + "="*80 + "\n")
    
    # Demo 3: Semantic vs keyword comparison
    await demo_semantic_vs_keyword_comparison("stunning views from modern kitchen")
    
    console.print(f"\n[bold green]🎉 All natural language search demos completed![/bold green]")


if __name__ == "__main__":
    asyncio.run(run_all_natural_language_demos())