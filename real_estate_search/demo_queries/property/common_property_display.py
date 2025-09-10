"""
Common property display module for standardized table rendering.

This module provides a single, unified way to display property search results
across all search types. It uses Pydantic for configuration and data validation,
following SOLID principles and clean code practices.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from ...models import PropertyListing
from ..display_formatter import PropertyDisplayFormatter


class PropertyDisplayConfig(BaseModel):
    """
    Configuration for property table display.
    
    Uses boolean flags following Python best practices for clean configuration.
    """
    show_description: bool = Field(default=True, description="Include description column")
    show_score: bool = Field(default=True, description="Include score column")
    show_details: bool = Field(default=True, description="Include details column")
    score_label: str = Field(default="Score", description="Label for score column")
    table_title: str = Field(default="Property Search Results", description="Title for the table")
    max_results: int = Field(default=10, description="Maximum results to display (fixed at 10)")
    
    @field_validator('max_results')
    @classmethod
    def validate_max_results(cls, v):
        """Ensure max_results is always 10."""
        return 10


class PropertyTableDisplay:
    """
    Unified property table display service.
    
    This class handles all property table rendering with standardized columns
    and configurable options through Pydantic models.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the display service.
        
        Args:
            console: Optional Rich console instance
        """
        self.console = console or Console()
        self.formatter = PropertyDisplayFormatter()
    
    def display_properties(
        self,
        properties: List[PropertyListing],
        config: Optional[PropertyDisplayConfig] = None,
        total_hits: Optional[int] = None,
        execution_time_ms: Optional[int] = None
    ) -> None:
        """
        Display properties in a standardized table format.
        
        Args:
            properties: List of properties to display
            config: Display configuration
            total_hits: Total number of hits from search
            execution_time_ms: Query execution time in milliseconds
        """
        if config is None:
            config = PropertyDisplayConfig()
        
        # Ensure we only display up to max_results (10)
        display_properties = properties[:config.max_results]
        
        if not display_properties:
            self._display_no_results()
            return
        
        # Create the table
        table = self._create_table(config)
        
        # Add rows
        for idx, prop in enumerate(display_properties, 1):
            self._add_property_row(table, idx, prop, config)
        
        # Display the table
        self.console.print(table)
        
        # Display statistics if provided
        if total_hits is not None or execution_time_ms is not None:
            self._display_statistics(total_hits, execution_time_ms, len(display_properties))
    
    def _create_table(self, config: PropertyDisplayConfig) -> Table:
        """
        Create the table with configured columns.
        
        Args:
            config: Display configuration
            
        Returns:
            Configured Rich Table
        """
        table = Table(
            title=f"[bold green]{config.table_title}[/bold green]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        # Always include row number and address
        table.add_column("#", style="dim", width=3)
        table.add_column("Address", style="cyan", width=35)
        table.add_column("Price", style="green", justify="right", width=12)
        
        # Optional columns based on configuration
        if config.show_details:
            table.add_column("Details", style="yellow", width=25)
        
        if config.show_score:
            table.add_column(config.score_label, style="magenta", justify="right", width=10)
        
        if config.show_description:
            table.add_column("Description", style="bright_blue", width=40)
        
        return table
    
    def _add_property_row(
        self,
        table: Table,
        idx: int,
        prop: PropertyListing,
        config: PropertyDisplayConfig
    ) -> None:
        """
        Add a property row to the table.
        
        Args:
            table: The Rich Table to add to
            idx: Row number
            prop: Property to display
            config: Display configuration
        """
        row_data = []
        
        # Row number
        row_data.append(str(idx))
        
        # Address
        row_data.append(prop.address.full_address)
        
        # Price
        row_data.append(self.formatter.format_price(prop.price))
        
        # Details (optional)
        if config.show_details:
            details = self._format_property_details(prop)
            row_data.append(details)
        
        # Score (optional)
        if config.show_score:
            # Use hybrid_score if available, otherwise use regular score
            score_value = prop.hybrid_score if prop.hybrid_score is not None else prop.score
            score_str = self._format_score(score_value)
            row_data.append(score_str)
        
        # Description (optional)
        if config.show_description:
            description = self._format_description(prop.description)
            row_data.append(description)
        
        table.add_row(*row_data)
    
    def _format_property_details(self, prop: PropertyListing) -> str:
        """
        Format property details (beds/baths/sqft).
        
        Args:
            prop: Property to format
            
        Returns:
            Formatted details string
        """
        parts = []
        
        if prop.bedrooms:
            parts.append(f"{prop.bedrooms}bd")
        
        if prop.bathrooms:
            parts.append(f"{prop.bathrooms}ba")
        
        if prop.square_feet:
            parts.append(f"{prop.square_feet:,}sqft")
        
        return " • ".join(parts) if parts else "N/A"
    
    def _format_score(self, score: Optional[float]) -> str:
        """
        Format the score value.
        
        Args:
            score: Score value to format
            
        Returns:
            Formatted score string
        """
        if score is None:
            return "N/A"
        
        # For scores between 0 and 1, show as percentage
        if 0 <= score <= 1:
            return f"{score:.2%}"
        # For other scores, show with 2 decimal places
        else:
            return f"{score:.2f}"
    
    def _format_description(self, description: Optional[str], max_length: int = 150) -> str:
        """
        Format property description with truncation.
        
        Args:
            description: Description text
            max_length: Maximum length before truncation
            
        Returns:
            Formatted description
        """
        if not description:
            return "No description available"
        
        if len(description) > max_length:
            return description[:max_length - 3] + "..."
        
        return description
    
    def _display_no_results(self) -> None:
        """Display a message when no results are found."""
        self.console.print(Panel(
            "[red]No properties found matching your search.[/red]",
            border_style="red"
        ))
    
    def _display_statistics(
        self,
        total_hits: Optional[int],
        execution_time_ms: Optional[int],
        displayed_count: int
    ) -> None:
        """
        Display search statistics.
        
        Args:
            total_hits: Total number of hits
            execution_time_ms: Execution time in milliseconds
            displayed_count: Number of results displayed
        """
        stats_parts = []
        
        if execution_time_ms is not None:
            stats_parts.append(f"[green]✓[/green] Query executed in [bold]{execution_time_ms}ms[/bold]")
        
        if total_hits is not None:
            stats_parts.append(f"[green]✓[/green] Total hits: [bold]{total_hits}[/bold]")
        
        stats_parts.append(f"[green]✓[/green] Results shown: [bold]{displayed_count}[/bold]")
        
        stats_text = "\n".join(stats_parts)
        
        self.console.print(Panel(
            stats_text,
            title="[bold]Search Statistics[/bold]",
            border_style="green"
        ))