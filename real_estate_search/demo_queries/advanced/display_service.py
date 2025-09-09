"""
Display service for advanced search results.

This module handles all display and formatting logic for
semantic, multi-entity, and Wikipedia search results.
"""

from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
import logging

from ..result_models import (
    PropertySearchResult, WikipediaSearchResult, MixedEntityResult,
    WikipediaArticle
)
from ...models.property import PropertyListing
from .search_executor import (
    SemanticSearchResponse, MultiEntityResponse, WikipediaResponse
)

logger = logging.getLogger(__name__)


class AdvancedDisplayService:
    """Service for displaying advanced search results."""
    
    def __init__(self):
        """Initialize the display service."""
        self.console = Console()
    
    def display_semantic_results(
        self,
        response: SemanticSearchResponse,
        reference: Optional[PropertyListing] = None,
        query_name: str = "Semantic Similarity Search"
    ) -> None:
        """
        Display semantic search results.
        
        Args:
            response: Semantic search response
            reference: Reference property used for similarity
            query_name: Name of the query for display
        """
        # Show reference property if available
        if reference:
            addr = reference.address
            street = addr.street or 'Unknown street'
            city = addr.city or 'Unknown city'
            price_fmt = f"${reference.price:,.0f}" if reference.price else "Unknown price"
            
            ref_text = Text()
            ref_text.append("🏠 Reference Property\n", style="bold yellow")
            ref_text.append(f"Address: {street}, {city}\n", style="cyan")
            ref_text.append(f"Type: {reference.display_property_type}\n", style="magenta")
            ref_text.append(f"Price: {price_fmt}\n", style="green")
            ref_text.append(f"Size: {reference.bedrooms}bd/{reference.bathrooms}ba | {reference.square_feet:,} sqft\n", style="blue")
            ref_text.append(f"\n📝 Description:\n", style="bold yellow")
            desc_preview = reference.description[:300] + "..." if len(reference.description) > 300 else reference.description
            ref_text.append(desc_preview, style="bright_blue")
            
            self.console.print(Panel(
                ref_text,
                title="[bold cyan]🤖 AI Semantic Similarity Search[/bold cyan]",
                subtitle=f"Finding similar properties using embeddings",
                border_style="cyan"
            ))
        
        if response.results:
            # Create similarity results table
            table = Table(
                title=f"[bold green]Found {len(response.results)} Similar Properties[/bold green]",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
                show_lines=True
            )
            table.add_column("#", style="dim", width=4)
            table.add_column("Score", style="magenta", justify="right", width=8)
            table.add_column("Property Details", style="cyan", width=50)
            table.add_column("Description", style="bright_blue", width=60)
            
            for i, result in enumerate(response.results, 1):
                # Format address
                addr = result.address
                address_str = f"{addr.street or 'N/A'}, {addr.city or 'N/A'}"
                
                # Format price
                price_str = f"${result.price:,.0f}" if result.price else "N/A"
                
                # Format size
                size_str = f"{result.bedrooms}bd/{result.bathrooms}ba | {result.square_feet:,}sqft"
                
                # Format property details
                property_details = Text()
                property_details.append(f"📍 {address_str}\n", style="cyan")
                property_details.append(f"💰 {price_str} ", style="green")
                property_details.append(f"• {result.property_type.title()}\n", style="yellow")
                property_details.append(f"🏠 {size_str}", style="blue")
                
                # Format description
                description = result.description
                desc_text = Text(description[:200] + "..." if len(description) > 200 else description, style="bright_blue")
                
                # Add to table
                table.add_row(
                    str(i),
                    f"{result.score:.2f}" if result.score else "N/A",
                    property_details,
                    desc_text
                )
            
            self.console.print(table)
            
            # Show AI insights
            self.console.print(Panel(
                f"[green]✓[/green] Found [bold]{len(response.results)}[/bold] semantically similar properties\n"
                f"[green]✓[/green] Using [bold]1024-dimensional[/bold] voyage-3 embeddings\n"
                f"[green]✓[/green] Query time: [bold]{response.execution_time_ms}ms[/bold]\n"
                f"[dim]💡 Higher similarity scores indicate more similar properties[/dim]",
                title="[bold]🤖 AI Search Results[/bold]",
                border_style="green"
            ))
    
    def display_multi_entity_results(
        self,
        response: MultiEntityResponse,
        query_text: str = ""
    ) -> None:
        """
        Display multi-entity search results.
        
        Args:
            response: Multi-entity search response
            query_text: Original query text
        """
        # Show search header
        self.console.print(Panel(
            f"[bold cyan]🌐 Multi-Entity Search[/bold cyan]\n"
            f"[yellow]Query: '{query_text}'[/yellow]\n"
            f"[dim]Searching across properties, neighborhoods, and Wikipedia[/dim]",
            border_style="cyan"
        ))
        
        # Display properties
        if response.property_results:
            prop_table = Table(
                title="[bold]🏠 Properties[/bold]",
                box=box.SIMPLE,
                show_header=True,
                header_style="cyan"
            )
            prop_table.add_column("Score", style="magenta", justify="right", width=8)
            prop_table.add_column("Address", style="cyan")
            prop_table.add_column("Price", style="green", justify="right")
            prop_table.add_column("Type", style="yellow")
            
            for result in response.property_results[:5]:
                addr = result.address
                address_str = f"{addr.street}, {addr.city}"
                price_str = f"${result.price:,.0f}" if result.price else "N/A"
                
                prop_table.add_row(
                    f"{result.score:.2f}" if result.score else "N/A",
                    address_str,
                    price_str,
                    result.property_type.title()
                )
            
            self.console.print(prop_table)
        
        # Display neighborhoods (if any)
        if response.neighborhood_results:
            neigh_table = Table(
                title="\n[bold]📍 Neighborhoods[/bold]",
                box=box.SIMPLE,
                show_header=True,
                header_style="cyan"
            )
            neigh_table.add_column("Score", style="magenta", justify="right", width=8)
            neigh_table.add_column("Name", style="cyan")
            neigh_table.add_column("City", style="green")
            
            for result in response.neighborhood_results[:5]:
                neigh_table.add_row(
                    f"{result.get('_score', 0):.2f}",
                    result.get('name', 'N/A'),
                    result.get('city', 'N/A')
                )
            
            self.console.print(neigh_table)
        
        # Display Wikipedia articles
        if response.wikipedia_results:
            wiki_table = Table(
                title="\n[bold]📚 Wikipedia Articles[/bold]",
                box=box.SIMPLE,
                show_header=True,
                header_style="cyan"
            )
            wiki_table.add_column("Score", style="magenta", justify="right", width=8)
            wiki_table.add_column("Title", style="cyan")
            wiki_table.add_column("Categories", style="yellow")
            
            for result in response.wikipedia_results[:5]:
                # Note: categories might not be in WikipediaArticle model
                cat_str = "N/A"  # Default if no categories
                
                wiki_table.add_row(
                    f"{result.score:.2f}" if result.score else "N/A",
                    result.title,
                    cat_str
                )
            
            self.console.print(wiki_table)
        
        # Show summary statistics
        if response.aggregations and 'by_index' in response.aggregations:
            stats_text = Text()
            for bucket in response.aggregations['by_index']['buckets']:
                index_name = bucket['key']
                count = bucket['doc_count']
                if 'properties' in index_name:
                    stats_text.append(f"🏠 Properties: {count}  ", style="cyan")
                elif 'neighborhoods' in index_name:
                    stats_text.append(f"📍 Neighborhoods: {count}  ", style="yellow")
                elif 'wikipedia' in index_name:
                    stats_text.append(f"📚 Wikipedia: {count}  ", style="magenta")
            
            self.console.print(Panel(
                stats_text,
                title="[bold]Search Results Summary[/bold]",
                border_style="green"
            ))
    
    def display_wikipedia_results(
        self,
        response: WikipediaResponse,
        city: str = "",
        state: str = "",
        topics: Optional[List[str]] = None
    ) -> None:
        """
        Display Wikipedia search results.
        
        Args:
            response: Wikipedia search response
            city: City filter used
            state: State filter used
            topics: Topics filter used
        """
        # Show search header
        self.console.print(Panel(
            f"[bold cyan]📚 Wikipedia Article Search[/bold cyan]\n"
            f"[yellow]Location: {city}, {state}[/yellow]\n"
            f"[dim]Topics: {', '.join(topics) if topics else 'All topics'}[/dim]",
            border_style="cyan"
        ))
        
        if response.results:
            # Create results table
            table = Table(
                title=f"[bold green]Found {len(response.results)} Wikipedia Articles[/bold green]",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
                show_lines=True,
                width=None
            )
            table.add_column("ID", style="dim", width=6, no_wrap=True)
            table.add_column("Score", style="magenta", justify="right", width=6, no_wrap=True)
            table.add_column("Article", style="cyan", overflow="fold")
            table.add_column("Summary", style="bright_blue", overflow="fold")
            
            for i, result in enumerate(response.results, 1):
                # Format article info
                article_info = Text()
                article_info.append(f"📖 {result.title}\n", style="bold white")
                article_info.append(f"📍 {result.city or 'N/A'}, {result.state or 'N/A'}\n", style="green")
                
                # Format summary
                summary_text = Text(
                    result.summary[:250] + "..." if len(result.summary) > 250 else result.summary,
                    style="bright_blue"
                )
                
                # Add to table
                table.add_row(
                    str(result.page_id),
                    f"{result.score:.2f}" if result.score else "N/A",
                    article_info,
                    summary_text
                )
            
            self.console.print(table)
            
            # Show search insights
            self.console.print(Panel(
                f"[green]✓[/green] Found [bold]{len(response.results)}[/bold] Wikipedia articles\n"
                f"[green]✓[/green] Location: [bold]{city}, {state}[/bold]\n"
                f"[green]✓[/green] Query time: [bold]{response.execution_time_ms}ms[/bold]",
                title="[bold]📚 Search Results[/bold]",
                border_style="green"
            ))
        else:
            self.console.print(Panel(
                f"[yellow]No Wikipedia articles found for {city}, {state}[/yellow]",
                border_style="yellow"
            ))
    
    def display_neighborhood_associations(
        self,
        articles: List[Dict[str, Any]],
        city: str = "",
        state: str = ""
    ) -> None:
        """
        Display Wikipedia articles with neighborhood associations.
        
        Args:
            articles: List of articles with neighborhood data
            city: City filter
            state: State filter
        """
        self.console.print("\n[bold cyan]🏘️ Articles with Neighborhood Associations[/bold cyan]")
        
        if articles:
            neigh_table = Table(
                title=f"[bold green]Found {len(articles)} Articles with Neighborhoods[/bold green]",
                box=box.SIMPLE,
                show_header=True,
                header_style="bold cyan",
                show_lines=False
            )
            neigh_table.add_column("Title", style="cyan")
            neigh_table.add_column("Location", style="green", no_wrap=True)
            neigh_table.add_column("Neighborhoods", style="yellow")
            
            for article in articles:
                location = f"{article.get('city', 'N/A')}, {article.get('state', 'N/A')}"
                neighborhoods = article.get('neighborhood_names', [])
                neigh_display = ', '.join(neighborhoods[:3])
                if len(neighborhoods) > 3:
                    neigh_display += f" (+{len(neighborhoods) - 3} more)"
                
                neigh_table.add_row(
                    article.get('title', 'N/A'),
                    location,
                    neigh_display or 'N/A'
                )
            
            self.console.print(neigh_table)
        else:
            self.console.print(f"[yellow]No articles with neighborhood associations found in {city}, {state}[/yellow]")
    
    def display_error(self, message: str) -> None:
        """
        Display an error message.
        
        Args:
            message: Error message to display
        """
        self.console.print(Panel(
            f"[red]❌ Error: {message}[/red]",
            border_style="red"
        ))