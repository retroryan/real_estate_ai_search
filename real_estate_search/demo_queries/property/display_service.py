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

from .models import PropertySearchResult
from ..result_models import AggregationSearchResult
from ...models import PropertyListing
from ..display_formatter import PropertyDisplayFormatter
from .common_property_display import PropertyTableDisplay, PropertyDisplayConfig

logger = logging.getLogger(__name__)


class PropertyDisplayService:
    """
    Service for displaying property search results.
    
    Handles all formatting and console output for property searches
    using Rich library for enhanced terminal display.
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console if console is not None else Console()
        self.table_display = PropertyTableDisplay(self.console)
    
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