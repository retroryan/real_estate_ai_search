"""
Display and formatting service for property search results.

This module handles all Rich console output, table formatting,
and result visualization. No business logic or query construction.
"""

from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
import logging

from ...models.results import PropertySearchResult, AggregationSearchResult
from ...models import PropertyListing
from ..display_formatter import PropertyDisplayFormatter

logger = logging.getLogger(__name__)


class PropertyDisplayService:
    """
    Service for displaying property search results.
    
    Handles all formatting and console output for property searches
    using Rich library for enhanced terminal display.
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console if console is not None else Console()
    
    def display_search_criteria(
        self,
        title: str,
        criteria: Dict[str, Any]
    ) -> None:
        """
        Display search criteria in a formatted panel.
        
        Args:
            title: Title for the search
            criteria: Dictionary of search criteria to display
        """
        criteria_text = Text()
        
        for key, value in criteria.items():
            if key == "property_type":
                criteria_text.append("🏠 Property Type: ", style="yellow")
                criteria_text.append(f"{PropertyDisplayFormatter.format_property_type(value)}\n", style="cyan")
            elif key == "price_range":
                criteria_text.append("💰 Price Range: ", style="yellow")
                criteria_text.append(f"${value['min']:,.0f} - ${value['max']:,.0f}\n", style="green")
            elif key == "bedrooms":
                criteria_text.append("🛏️  Bedrooms: ", style="yellow")
                criteria_text.append(f"{value}+\n", style="cyan")
            elif key == "bathrooms":
                criteria_text.append("🚿 Bathrooms: ", style="yellow")
                criteria_text.append(f"{value}+\n", style="cyan")
            elif key == "location":
                criteria_text.append("📍 Center Location: ", style="yellow")
                criteria_text.append(f"({value['lat']:.4f}, {value['lon']:.4f})\n", style="cyan")
            elif key == "radius":
                criteria_text.append("📏 Search Radius: ", style="yellow")
                criteria_text.append(f"{value} km\n", style="cyan")
            elif key == "query":
                criteria_text.append("🔍 Query: ", style="yellow")
                criteria_text.append(f"'{value}'\n", style="cyan")
        
        self.console.print(Panel(
            criteria_text,
            title=f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan"
        ))
    
    def display_basic_search_results(
        self,
        result: PropertySearchResult
    ) -> None:
        """
        Display basic search results with highlighting.
        
        Args:
            result: PropertySearchResult to display
        """
        # Header
        self.console.print(Panel.fit(
            f"[bold cyan]🔍 {result.query_name}[/bold cyan]",
            border_style="cyan"
        ))
        
        if result.total_hits == 0:
            self.console.print(Panel(
                "[red]No properties found matching your search.[/red]",
                border_style="red"
            ))
            return
        
        # Results table
        table = Table(
            title=f"[bold green]Found {result.total_hits} Properties[/bold green]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Address", style="cyan", width=30)
        table.add_column("Price", style="green", justify="right")
        table.add_column("Details", style="yellow")
        table.add_column("Score", style="magenta", justify="right")
        
        for i, prop in enumerate(result.results[:10], 1):
            address = prop.address.full_address
            price = prop.display_price
            details = prop.summary
            score = f"{prop.score:.2f}" if prop.score else "N/A"
            
            table.add_row(str(i), address, price, details, score)
        
        self.console.print(table)
        
        # Statistics
        self.console.print(Panel(
            f"[green]✓[/green] Query executed in [bold]{result.execution_time_ms}ms[/bold]\n"
            f"[green]✓[/green] Total hits: [bold]{result.total_hits}[/bold]\n"
            f"[green]✓[/green] Results shown: [bold]{len(result.results)}[/bold]",
            title="[bold]Search Statistics[/bold]",
            border_style="green"
        ))
    
    def display_filtered_search_results(
        self,
        result: PropertySearchResult
    ) -> None:
        """
        Display filtered search results in a table.
        
        Args:
            result: PropertySearchResult to display
        """
        if result.total_hits > 0:
            # Create property cards layout
            table = Table(
                title=f"[bold green]Found {result.total_hits} Matching Properties[/bold green]",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
                width=120
            )
            table.add_column("#", style="dim", width=3)
            table.add_column("Address", style="cyan", width=35)
            table.add_column("Price", style="green", justify="right", width=12)
            table.add_column("Beds/Baths", style="yellow", justify="center", width=10)
            table.add_column("Sq Ft", style="blue", justify="right", width=10)
            table.add_column("Type", style="magenta", width=15)
            
            for i, prop in enumerate(result.results[:15], 1):
                address = prop.address.full_address
                price = f"${prop.price:,.0f}"
                beds_baths = f"{prop.bedrooms}/{prop.bathrooms}"
                sq_ft = f"{prop.square_feet:,}" if prop.square_feet else "N/A"
                prop_type = PropertyDisplayFormatter.format_property_type(prop.property_type)
                
                table.add_row(
                    str(i),
                    address,
                    price,
                    beds_baths,
                    sq_ft,
                    prop_type
                )
            
            self.console.print(table)
            
            # Summary stats
            self.console.print(Panel(
                f"[green]✓[/green] Filters applied successfully\n"
                f"[green]✓[/green] Query time: [bold]{result.execution_time_ms}ms[/bold]\n"
                f"[green]✓[/green] Total matches: [bold]{result.total_hits}[/bold]\n"
                f"[green]✓[/green] Showing: [bold]{len(result.results)}[/bold] properties",
                title="[bold]Filter Results[/bold]",
                border_style="green"
            ))
        else:
            self.console.print(Panel(
                "[red]No properties found matching your filters.[/red]\n"
                "[yellow]Try adjusting your criteria for more results.[/yellow]",
                border_style="red"
            ))
    
    def display_geo_search_results(
        self,
        result: PropertySearchResult,
        radius_km: float
    ) -> None:
        """
        Display geo-distance search results with distance information.
        
        Args:
            result: PropertySearchResult to display
            radius_km: Search radius for display
        """
        if result.total_hits > 0:
            # Create distance-sorted table
            table = Table(
                title=f"[bold green]Found {result.total_hits} Properties Within {radius_km}km[/bold green]",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan"
            )
            table.add_column("#", style="dim", width=3)
            table.add_column("Distance", style="magenta", justify="right", width=10)
            table.add_column("Address", style="cyan", width=35)
            table.add_column("Price", style="green", justify="right")
            table.add_column("Details", style="yellow")
            
            for i, prop in enumerate(result.results[:15], 1):
                address = prop.address.full_address
                price = f"${prop.price:,.0f}"
                details = f"{prop.bedrooms} bed, {prop.bathrooms} bath"
                # Note: Distance would need to be added to PropertyResult model
                distance_str = "N/A"
                
                table.add_row(
                    str(i),
                    distance_str,
                    address,
                    price,
                    details
                )
            
            self.console.print(table)
            
            # Show map visualization hint
            self.console.print(Panel(
                f"[green]✓[/green] Found [bold]{result.total_hits}[/bold] properties within [bold]{radius_km}km[/bold]\n"
                f"[green]✓[/green] Query time: [bold]{result.execution_time_ms}ms[/bold]\n"
                f"[green]✓[/green] Results sorted by distance from center\n"
                f"[dim]💡 Tip: Properties are sorted from nearest to farthest[/dim]",
                title="[bold]📍 Location Search Results[/bold]",
                border_style="green"
            ))
        else:
            self.console.print(Panel(
                f"[red]No properties found within {radius_km}km of the specified location.[/red]\n"
                "[yellow]Try increasing the search radius or adjusting the price limit.[/yellow]",
                border_style="red"
            ))
    
    def display_aggregation_results(
        self,
        result: AggregationSearchResult
    ) -> None:
        """
        Display price range search with aggregation statistics.
        
        Args:
            result: AggregationSearchResult to display
        """
        # Show aggregation results in a nice format
        if result.aggregations and 'price_stats' in result.aggregations:
            stats = result.aggregations['price_stats']
            
            # Create statistics panel
            stats_table = Table(box=box.SIMPLE, show_header=False)
            stats_table.add_column("Metric", style="yellow")
            stats_table.add_column("Value", style="green", justify="right")
            
            stats_table.add_row("Properties Found", str(stats.get('count', 0)))
            stats_table.add_row("Minimum Price", f"${stats.get('min', 0):,.0f}")
            stats_table.add_row("Maximum Price", f"${stats.get('max', 0):,.0f}")
            stats_table.add_row("Average Price", f"${stats.get('avg', 0):,.0f}")
            
            self.console.print(Panel(
                stats_table,
                title="[bold]📈 Price Statistics[/bold]",
                border_style="blue"
            ))
        
        # Property type distribution
        if result.aggregations and 'property_types' in result.aggregations:
            type_buckets = result.aggregations['property_types'].get('buckets', [])
            if type_buckets:
                type_table = Table(box=box.SIMPLE, show_header=False)
                type_table.add_column("Type", style="cyan")
                type_table.add_column("Count", style="magenta", justify="right")
                
                for bucket in type_buckets[:5]:
                    prop_type = PropertyDisplayFormatter.format_property_type(bucket['key'])
                    type_table.add_row(prop_type, str(bucket['doc_count']))
                
                self.console.print(Panel(
                    type_table,
                    title="[bold]🏠 Property Types[/bold]",
                    border_style="magenta"
                ))
        
        # Price histogram
        if result.aggregations and 'price_histogram' in result.aggregations:
            hist_buckets = result.aggregations['price_histogram'].get('buckets', [])
            if hist_buckets:
                self.console.print(Panel(
                    "[bold]📊 Price Distribution (in $100k buckets)[/bold]",
                    border_style="yellow"
                ))
                
                max_count = max(b['doc_count'] for b in hist_buckets) if hist_buckets else 1
                for bucket in hist_buckets[:10]:
                    price_range = f"${bucket['key']/1000:.0f}k"
                    count = bucket['doc_count']
                    bar_width = int((count / max_count) * 40)
                    bar = "█" * bar_width
                    self.console.print(f"  {price_range:>10} │ {bar} {count}")
        
        # Show final summary
        self.console.print(Panel(
            f"[green]✓[/green] Analysis complete in [bold]{result.execution_time_ms}ms[/bold]\n"
            f"[green]✓[/green] Properties analyzed: [bold]{result.total_hits}[/bold]\n"
            f"[green]✓[/green] Statistical aggregations calculated",
            title="[bold]✅ Search Complete[/bold]",
            border_style="green"
        ))
    
    def display_error(
        self,
        message: str,
        exec_time: Optional[int] = None
    ) -> None:
        """
        Display an error message.
        
        Args:
            message: Error message to display
            exec_time: Optional execution time in ms
        """
        error_text = f"[red]{message}[/red]"
        if exec_time:
            error_text += f"\n[yellow]Execution time: {exec_time}ms[/yellow]"
        
        self.console.print(Panel(
            error_text,
            title="[bold red]Error[/bold red]",
            border_style="red"
        ))