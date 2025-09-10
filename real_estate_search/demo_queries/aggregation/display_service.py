"""
Display and formatting logic for aggregation results.

This module handles all presentation logic including rich console output,
tables, histograms, and summary panels.
"""

from typing import Dict, Any, List, Optional
import logging

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .constants import HISTOGRAM_BAR_MAX_WIDTH, PRICE_LABEL_WIDTH
from .models import NeighborhoodStats, PriceRangeStats

logger = logging.getLogger(__name__)


class AggregationDisplayService:
    """Service for displaying aggregation results with rich formatting."""
    
    def __init__(self):
        """Initialize the display service with a Rich console."""
        self.console = Console()
    
    def display_neighborhood_stats(
        self, 
        response: Dict[str, Any], 
        results: List[NeighborhoodStats], 
        size: int
    ) -> None:
        """
        Display neighborhood statistics with rich formatting.
        
        Creates formatted tables and panels showing neighborhood property
        statistics and global market metrics.
        
        Args:
            response: Raw Elasticsearch response for global stats
            results: List of NeighborhoodStats objects
            size: Number of neighborhoods analyzed
        """
        # Header panel
        self.console.print(Panel(
            f"[bold cyan]📊 Neighborhood Statistics Analysis[/bold cyan]\n"
            f"[yellow]Analyzing top {size} neighborhoods by property count[/yellow]",
            border_style="cyan"
        ))
        
        if not results:
            self.console.print("[red]No aggregation results found[/red]")
            return
        
        # Create neighborhood stats table
        table = Table(
            title=f"[bold green]Neighborhood Property Statistics[/bold green]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        # Add columns
        table.add_column("Neighborhood", style="cyan", width=20)
        table.add_column("Properties", style="yellow", justify="right")
        table.add_column("Avg Price", style="green", justify="right")
        table.add_column("Price Range", style="blue", justify="right")
        table.add_column("Avg Beds", style="magenta", justify="right")
        table.add_column("Avg SqFt", style="yellow", justify="right")
        table.add_column("$/SqFt", style="green", justify="right")
        
        # Add rows
        for neighborhood in results:
            price_range = f"${neighborhood.min_price:,.0f}-${neighborhood.max_price:,.0f}"
            table.add_row(
                neighborhood.neighborhood_id,
                str(neighborhood.property_count),
                f"${neighborhood.avg_price:,.0f}",
                price_range,
                f"{neighborhood.avg_bedrooms:.1f}",
                f"{neighborhood.avg_square_feet:,.0f}",
                f"${neighborhood.price_per_sqft:.2f}"
            )
        
        self.console.print(table)
        
        # Show global statistics
        self._display_global_stats(response, len(results))
    
    def display_price_distribution(
        self,
        response: Dict[str, Any],
        results: List[PriceRangeStats],
        interval: int,
        min_price: float,
        max_price: float
    ) -> None:
        """
        Display price distribution with rich formatting.
        
        Creates histogram visualization, percentile tables, and property
        type statistics.
        
        Args:
            response: Raw Elasticsearch response
            results: List of PriceRangeStats objects
            interval: Bucket size for histogram
            min_price: Minimum price in range
            max_price: Maximum price in range
        """
        # Header panel
        self.console.print(Panel(
            f"[bold cyan]📊 Price Distribution Analysis[/bold cyan]\n"
            f"[yellow]Range: ${min_price:,.0f} - ${max_price:,.0f}[/yellow]\n"
            f"[yellow]Bucket Size: ${interval:,.0f}[/yellow]",
            border_style="cyan"
        ))
        
        if not results:
            self.console.print("[red]No distribution results found[/red]")
            return
        
        # Draw histogram
        self._draw_histogram(results)
        
        # Show percentiles
        self._display_percentiles(response)
        
        # Show property type statistics
        self._display_property_type_stats(response)
    
    def _draw_histogram(self, results: List[PriceRangeStats]) -> None:
        """
        Draw a text-based histogram of price distribution.
        
        Args:
            results: List of PriceRangeStats objects
        """
        self.console.print("\n[bold]Price Distribution Histogram:[/bold]")
        
        if not results:
            return
        
        max_count = max(r.count for r in results)
        
        for result in results:
            # Calculate bar width proportional to count
            bar_width = int((result.count / max_count) * HISTOGRAM_BAR_MAX_WIDTH) if max_count > 0 else 0
            bar = "█" * bar_width
            
            # Format price label
            price_label = f"${result.range_start/1000:.0f}k-${result.range_end/1000:.0f}k"
            
            # Print histogram row
            self.console.print(
                f"  {price_label:>{PRICE_LABEL_WIDTH}} │ [green]{bar}[/green] {result.count}"
            )
    
    def _display_percentiles(self, response: Dict[str, Any]) -> None:
        """
        Display price percentiles in a formatted table.
        
        Args:
            response: Elasticsearch response with percentile aggregations
        """
        if 'aggregations' not in response or 'price_percentiles' not in response['aggregations']:
            return
        
        percentiles = response['aggregations']['price_percentiles'].get('values', {})
        
        if not percentiles:
            return
        
        # Create percentiles table
        percentile_table = Table(
            title="\n[bold]Price Percentiles[/bold]",
            box=box.SIMPLE,
            show_header=False
        )
        percentile_table.add_column("Percentile", style="yellow")
        percentile_table.add_column("Price", style="green", justify="right")
        
        for percentile, value in percentiles.items():
            percentile_table.add_row(
                f"{percentile}th percentile",
                f"${value:,.0f}" if value else "N/A"
            )
        
        self.console.print(percentile_table)
    
    def _display_property_type_stats(self, response: Dict[str, Any]) -> None:
        """
        Display statistics grouped by property type.
        
        Args:
            response: Elasticsearch response with property type aggregations
        """
        if 'aggregations' not in response or 'by_property_type_stats' not in response['aggregations']:
            return
        
        type_buckets = response['aggregations']['by_property_type_stats'].get('buckets', [])
        
        if not type_buckets:
            return
        
        # Create property type table
        type_table = Table(
            title="\n[bold]Statistics by Property Type[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        type_table.add_column("Type", style="cyan")
        type_table.add_column("Count", style="yellow", justify="right")
        type_table.add_column("Avg Price", style="green", justify="right")
        type_table.add_column("Min Price", style="blue", justify="right")
        type_table.add_column("Max Price", style="red", justify="right")
        
        for type_bucket in type_buckets:
            stats = type_bucket.get('price_stats', {})
            type_table.add_row(
                type_bucket['key'].title() if type_bucket['key'] else "Unknown",
                str(type_bucket['doc_count']),
                f"${stats['avg']:,.0f}" if stats.get('avg') else "N/A",
                f"${stats['min']:,.0f}" if stats.get('min') else "N/A",
                f"${stats['max']:,.0f}" if stats.get('max') else "N/A"
            )
        
        self.console.print(type_table)
    
    def _display_global_stats(self, response: Dict[str, Any], neighborhood_count: int) -> None:
        """
        Display global market statistics panel.
        
        Args:
            response: Elasticsearch response with global aggregations
            neighborhood_count: Number of neighborhoods analyzed
        """
        if 'aggregations' not in response:
            return
        
        aggs = response['aggregations']
        
        # Build stats text
        stats_lines = []
        
        if 'total_properties' in aggs:
            total = aggs['total_properties']['value']
            stats_lines.append(f"[green]✓[/green] Total Properties: [bold]{total:.0f}[/bold]")
        
        if 'overall_avg_price' in aggs:
            avg_price = aggs['overall_avg_price']['value']
            stats_lines.append(f"[green]✓[/green] Overall Average Price: [bold]${avg_price:,.0f}[/bold]")
        
        stats_lines.append(f"[green]✓[/green] Neighborhoods Analyzed: [bold]{neighborhood_count}[/bold]")
        
        if 'took' in response:
            stats_lines.append(f"[green]✓[/green] Query Time: [bold]{response['took']}ms[/bold]")
        
        # Display panel
        if stats_lines:
            stats_panel = Panel(
                "\n".join(stats_lines),
                title="[bold]📈 Overall Market Statistics[/bold]",
                border_style="green"
            )
            self.console.print(stats_panel)