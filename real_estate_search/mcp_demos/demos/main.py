"""Main entry point for MCP demos."""

import asyncio
import sys
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .property_search import demo_basic_property_search, demo_property_filter


console = Console()


# Demo registry
DEMOS = {
    1: {
        "name": "Basic Property Search",
        "description": "Search properties using natural language queries",
        "function": demo_basic_property_search
    },
    2: {
        "name": "Property Filter Search",
        "description": "Search with specific filters (type, price, location)",
        "function": demo_property_filter
    }
}


def list_demos():
    """List all available MCP demos."""
    console.print(Panel.fit(
        "[bold cyan]MCP Real Estate Search Demos[/bold cyan]",
        border_style="cyan"
    ))
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="cyan", no_wrap=True, width=3)
    table.add_column("Demo Name", style="green")
    table.add_column("Description", style="yellow")
    
    for num, demo in DEMOS.items():
        table.add_row(
            str(num),
            demo["name"],
            demo["description"]
        )
    
    console.print(table)
    console.print("\n[dim]Use './mcp_demos.sh <number>' to run a specific demo[/dim]")


async def run_demo(demo_number: int, verbose: bool = False):
    """Run a specific demo.
    
    Args:
        demo_number: The demo number to run
        verbose: Whether to show verbose output
    """
    if demo_number not in DEMOS:
        console.print(f"[red]Error: Demo {demo_number} not found[/red]")
        console.print(f"Valid demo numbers are: {list(DEMOS.keys())}")
        return
    
    demo = DEMOS[demo_number]
    
    console.print("\n" + "="*60)
    console.print(f"[bold yellow]Running: {demo['name']}[/bold yellow]")
    console.print("="*60 + "\n")
    
    try:
        result = await demo["function"]()
        
        if verbose and result.sample_results:
            console.print("\n[bold]Verbose Output - Sample Results:[/bold]")
            import json
            console.print(json.dumps(result.sample_results, indent=2))
            
    except Exception as e:
        console.print(f"[red]Demo failed with error: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())


def main():
    """Main entry point for MCP demos."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Real Estate Search Demos")
    parser.add_argument("demo", type=int, nargs="?", help="Demo number to run")
    parser.add_argument("--list", "-l", action="store_true", help="List all demos")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.list:
        list_demos()
    elif args.demo:
        asyncio.run(run_demo(args.demo, args.verbose))
    else:
        # Default: list demos
        list_demos()


if __name__ == "__main__":
    main()