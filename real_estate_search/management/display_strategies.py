"""
Display strategies for demo output formatting.

Implements the Strategy pattern for clean separation of display logic from business logic.
Each strategy encapsulates how demo results are formatted and presented to the user.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box
from rich.columns import Columns

from ..models.results import BaseQueryResult
from ..models import PropertyListing, WikipediaArticle
from ..models.results.location_aware import LocationAwareSearchResult
from ..models.results.location import LocationUnderstandingResult
from ..models.results.wikipedia import WikipediaSearchResult


class DisplayStrategy(ABC):
    """
    Abstract base class for display strategies.
    
    Defines the interface that all display strategies must implement.
    """
    
    def __init__(self):
        """Initialize the display strategy."""
        self.console = Console()
    
    @abstractmethod
    def display_header(self, demo_name: str, demo_number: int, description: Optional[str] = None) -> None:
        """
        Display the demo header.
        
        Args:
            demo_name: Name of the demo
            demo_number: Demo number
            description: Optional demo description
        """
        pass
    
    @abstractmethod
    def display_result(self, result: BaseQueryResult, verbose: bool = False) -> None:
        """
        Display the demo result.
        
        Args:
            result: Query result to display
            verbose: Whether to show verbose output
        """
        pass
    
    @abstractmethod
    def display_error(self, error: Exception) -> None:
        """
        Display an error message.
        
        Args:
            error: Exception that occurred
        """
        pass


class RichConsoleDisplay(DisplayStrategy):
    """
    Rich console display with panels and formatting.
    
    Uses the rich library for enhanced terminal output with colors,
    boxes, and formatted text.
    """
    
    def display_header(self, demo_name: str, demo_number: int, description: Optional[str] = None) -> None:
        """Display a rich formatted header."""
        header_text = Text()
        header_text.append(f"Demo {demo_number}: ", style="bold cyan")
        header_text.append(demo_name, style="bold yellow")
        
        self.console.print("\n")
        self.console.print(Panel(
            header_text,
            title="[bold magenta]🚀 Running Demo[/bold magenta]",
            border_style="bright_blue",
            box=box.DOUBLE,
            padding=(1, 2)
        ))
        
        if description:
            self.console.print(Panel(
                description,
                title="[bold green]📝 Description[/bold green]",
                border_style="green",
                box=box.ROUNDED,
                padding=(1, 2)
            ))
    
    def display_result(self, result: BaseQueryResult, verbose: bool = False) -> None:
        """Display the result using the result's own display method."""
        # Let the result display itself
        output = result.display(verbose=verbose)
        self.console.print(output)
    
    def display_error(self, error: Exception) -> None:
        """Display an error with rich formatting."""
        error_text = Text()
        error_text.append("✗ Error executing demo: ", style="bold red")
        error_text.append(str(error), style="red")
        
        self.console.print(Panel(
            error_text,
            border_style="red",
            box=box.ROUNDED
        ))


class PlainTextDisplay(DisplayStrategy):
    """
    Plain text display without formatting.
    
    Simple text output for environments that don't support rich formatting.
    """
    
    def display_header(self, demo_name: str, demo_number: int, description: Optional[str] = None) -> None:
        """Display a plain text header."""
        print(f"\nRunning Demo {demo_number}: {demo_name}")
        print("=" * 60)
        
        if description:
            print(description)
            print("=" * 60)
    
    def display_result(self, result: BaseQueryResult, verbose: bool = False) -> None:
        """Display the result as plain text."""
        output = result.display(verbose=verbose)
        print(output)
    
    def display_error(self, error: Exception) -> None:
        """Display an error as plain text."""
        print(f"✗ Error executing demo: {error}")


class PropertyTableDisplay(DisplayStrategy):
    """
    Property-specific table display.
    
    Specialized display for property search results with rich tables.
    Used by demos 1-3 that have their own PropertyDemoRunner.
    """
    
    def display_header(self, demo_name: str, demo_number: int, description: Optional[str] = None) -> None:
        """Property demos handle their own headers."""
        # PropertyDemoRunner handles the header display
        pass
    
    def display_result(self, result: BaseQueryResult, verbose: bool = False) -> None:
        """Property demos handle their own result display."""
        # PropertyDemoRunner handles the result display
        pass
    
    def display_error(self, error: Exception) -> None:
        """Display an error with rich formatting."""
        error_text = Text()
        error_text.append("✗ Error: ", style="bold red")
        error_text.append(str(error), style="red")
        
        self.console.print(Panel(
            error_text,
            border_style="red",
            box=box.ROUNDED
        ))


class LocationAwareDisplay(RichConsoleDisplay):
    """
    Location-aware search display.
    
    Enhanced display for location-based searches that shows extracted
    location information and property results.
    """
    
    def display_result(self, result: BaseQueryResult, verbose: bool = False) -> None:
        """Display location-aware search results with special formatting."""
        # LocationAwareDisplay is only used for location-aware demos
        # which always have location_intent field
        if result.location_intent:
            location_panel = self._create_location_panel(result.location_intent)
            self.console.print(location_panel)
        
        # Use parent class for standard display
        super().display_result(result, verbose)
    
    def _create_location_panel(self, location_intent: Dict[str, Any]) -> Panel:
        """Create a panel showing extracted location information."""
        location_text = Text()
        location_text.append("📍 Location Extracted:\n", style="bold cyan")
        
        city = location_intent.get('city', 'N/A')
        state = location_intent.get('state', 'N/A')
        confidence = location_intent.get('confidence', 0)
        
        location_text.append(f"  City: ", style="yellow")
        location_text.append(f"{city}\n")
        location_text.append(f"  State: ", style="yellow")
        location_text.append(f"{state}\n")
        location_text.append(f"  Confidence: ", style="yellow")
        
        # Color code confidence
        if confidence >= 0.9:
            conf_style = "green"
        elif confidence >= 0.7:
            conf_style = "yellow"
        else:
            conf_style = "red"
        
        location_text.append(f"{confidence:.0%}", style=conf_style)
        
        return Panel(
            location_text,
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2)
        )


class WikipediaDisplay(RichConsoleDisplay):
    """
    Wikipedia search display.
    
    Specialized display for Wikipedia article search results.
    """
    
    def display_result(self, result: BaseQueryResult, verbose: bool = False) -> None:
        """Display Wikipedia search results with article formatting."""
        # WikipediaDisplay is only used for Wikipedia demos
        # which always have results field with WikipediaArticle objects
        if result.results:
            # Create a rich table for articles
            table = self._create_articles_table(result.results[:5])
            self.console.print(table)
            
            # Show remaining count if there are more
            if len(result.results) > 5:
                remaining = len(result.results) - 5
                self.console.print(f"\n[dim]... and {remaining} more articles[/dim]")
        
        # Always show base display as well for stats
        super().display_result(result, verbose)
    
    def _create_articles_table(self, articles: List[WikipediaArticle]) -> Table:
        """Create a rich table for Wikipedia articles."""
        table = Table(
            title="📚 Wikipedia Articles Found",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("#", style="yellow", width=3)
        table.add_column("Title", style="bright_cyan")
        table.add_column("Summary", style="white")
        
        for i, article in enumerate(articles, 1):
            summary = article.short_summary or article.long_summary or ""
            if len(summary) > 100:
                summary = summary[:97] + "..."
            
            table.add_row(
                str(i),
                article.title,
                summary
            )
        
        return table


class AggregationDisplay(RichConsoleDisplay):
    """
    Aggregation results display.
    
    Enhanced display for aggregation queries with statistics and charts.
    """
    
    def display_result(self, result: BaseQueryResult, verbose: bool = False) -> None:
        """Display aggregation results with enhanced formatting."""
        if result.aggregations:
            # Create panels for different aggregation types
            for agg_name, agg_data in result.aggregations.items():
                panel = self._create_aggregation_panel(agg_name, agg_data)
                self.console.print(panel)
        
        # Use parent class for standard display
        super().display_result(result, verbose)
    
    def _create_aggregation_panel(self, name: str, data: Any) -> Panel:
        """Create a panel for aggregation data."""
        content = Text()
        
        # Aggregation data is always a dict in Elasticsearch responses
        # Handle bucket aggregations
        if 'buckets' in data:
            content.append(f"📊 {name.replace('_', ' ').title()}\n\n", style="bold yellow")
            for bucket in data['buckets'][:10]:
                key = bucket.get('key', 'Unknown')
                count = bucket.get('doc_count', 0)
                content.append(f"  {key}: ", style="cyan")
                content.append(f"{count:,}\n")
        # Handle stats aggregations
        elif any(k in data for k in ['min', 'max', 'avg']):
            content.append(f"📈 {name.replace('_', ' ').title()} Statistics\n\n", style="bold yellow")
            if 'min' in data:
                content.append(f"  Min: ${data['min']:,.0f}\n")
            if 'max' in data:
                content.append(f"  Max: ${data['max']:,.0f}\n")
            if 'avg' in data:
                content.append(f"  Avg: ${data['avg']:,.0f}\n")
        else:
            # Generic dict display
            content.append(f"{name.replace('_', ' ').title()}\n", style="bold yellow")
            for key, value in data.items():
                content.append(f"  {key}: {value}\n")
        
        return Panel(
            content,
            border_style="yellow",
            box=box.ROUNDED,
            padding=(1, 2)
        )


class LocationUnderstandingDisplay(RichConsoleDisplay):
    """
    Location understanding display.
    
    Display for location extraction and understanding demos.
    """
    
    def display_result(self, result: BaseQueryResult, verbose: bool = False) -> None:
        """Display location understanding results."""
        # LocationUnderstandingDisplay is only used for Demo 11
        # Just use the result's own display method
        output = result.display(verbose=verbose)
        self.console.print(output)


class NaturalLanguageDisplay(RichConsoleDisplay):
    """
    Natural language query display.
    
    Display for demos that handle multiple natural language queries.
    """
    
    def display_header(self, demo_name: str, demo_number: int, description: Optional[str] = None) -> None:
        """Display header for natural language demos."""
        super().display_header(demo_name, demo_number, description)
        
        # Add explanation about natural language processing
        self.console.print(Panel(
            "🤖 This demo processes natural language queries and extracts semantic meaning\n"
            "to find relevant properties using advanced NLP techniques.",
            title="[bold blue]Natural Language Processing[/bold blue]",
            border_style="blue",
            box=box.ROUNDED,
            padding=(1, 2)
        ))
    
    def display_result(self, result: BaseQueryResult, verbose: bool = False) -> None:
        """Display results from natural language queries."""
        # All query results have a display method from BaseQueryResult
        output = result.display(verbose=verbose)
        self.console.print(output)


# Factory function to get the appropriate display strategy
def get_display_strategy(strategy_type: str) -> DisplayStrategy:
    """
    Factory function to get the appropriate display strategy.
    
    Args:
        strategy_type: Type of display strategy to create
        
    Returns:
        Instance of the requested display strategy
        
    Raises:
        ValueError: If strategy type is unknown
    """
    strategies = {
        'rich': RichConsoleDisplay,
        'plain': PlainTextDisplay,
        'property': PropertyTableDisplay,
        'location': LocationAwareDisplay,
        'location_understanding': LocationUnderstandingDisplay,
        'wikipedia': WikipediaDisplay,
        'aggregation': AggregationDisplay,
        'natural_language': NaturalLanguageDisplay
    }
    
    strategy_class = strategies.get(strategy_type)
    if not strategy_class:
        raise ValueError(f"Unknown display strategy: {strategy_type}")
    
    return strategy_class()