"""
Display service for rich listing presentations.

This module handles all display and presentation logic for rich listings,
including console output with Rich library and HTML generation.
"""

from typing import Optional, List
from pathlib import Path
from datetime import datetime
import logging
import subprocess
import platform

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box
from rich.align import Align

from .models import (
    RichListingModel,
    RichListingSearchResult,
    RichListingDisplayConfig,
    NeighborhoodModel
)
from real_estate_search.models import PropertyListing, WikipediaArticle
from real_estate_search.html_generators import PropertyListingHTMLGenerator


logger = logging.getLogger(__name__)


class RichListingDisplayService:
    """
    Handles display and presentation of rich listing data.
    
    This service manages all visual output including Rich console
    formatting and HTML generation.
    """
    
    def __init__(self, config: Optional[RichListingDisplayConfig] = None):
        """
        Initialize the display service.
        
        Args:
            config: Display configuration settings
        """
        self.config = config or RichListingDisplayConfig()
        self.console = Console(width=self.config.console_width) if self.config.use_rich_console else None
        self.html_generator = PropertyListingHTMLGenerator(
            output_dir=self.config.html_output_dir
        ) if self.config.generate_html else None
    
    def display_rich_listing(self, listing: RichListingModel) -> None:
        """
        Display a complete rich listing in the console.
        
        Args:
            listing: The rich listing to display
        """
        if not self.console:
            return
        
        self.console.print("\n")
        
        # Display property header
        self.console.print(self.create_property_header(listing.property_data))
        self.console.print("\n")
        
        # Display property description
        if self.config.show_description:
            self.console.print(self.create_description_panel(listing.property_data))
            self.console.print("\n")
        
        # Create two-column layout for details and features
        if self.config.show_details_table or self.config.show_features:
            columns = []
            if self.config.show_details_table:
                columns.append(self.create_property_details_table(listing.property_data))
            if self.config.show_features:
                columns.append(self.create_features_panel(listing.property_data))
            
            if columns:
                self.console.print(Columns(columns, equal=True, expand=True))
                self.console.print("\n")
        
        # Display neighborhood information
        if self.config.show_neighborhood and listing.neighborhood:
            self.console.print(self.create_neighborhood_panel(listing.neighborhood))
            self.console.print("\n")
        
        # Display Wikipedia articles
        if self.config.show_wikipedia and listing.wikipedia_articles:
            self.console.print(self.create_wikipedia_panel(listing.wikipedia_articles))
            self.console.print("\n")
    
    def create_property_header(self, property: PropertyListing) -> Panel:
        """Create the main property header panel."""
        full_address = property.address.full_address
        prop_type = property.display_property_type
        price = self.format_price(property.price)
        
        header = Text()
        header.append(full_address, style="bold cyan")
        header.append(f"\n\n{prop_type}", style="yellow")
        header.append(f" | ", style="dim")
        header.append(price, style="bold green")
        
        return Panel(
            Align.center(header),
            title="[bold blue]🏠 Property Listing[/bold blue]",
            border_style="blue",
            padding=(1, 2)
        )
    
    def create_property_details_table(self, property: PropertyListing) -> Table:
        """Create a table with property details."""
        table = Table(
            title="Property Details",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("Feature", style="yellow", width=20)
        table.add_column("Value", style="white")
        
        details = [
            ("Bedrooms", f"{property.bedrooms}" if property.bedrooms else "N/A"),
            ("Bathrooms", f"{property.bathrooms}" if property.bathrooms else "N/A"),
            ("Square Feet", f"{property.square_feet:,}" if property.square_feet else "N/A"),
            ("Year Built", f"{property.year_built}" if property.year_built else "N/A"),
            ("Lot Size", f"{property.lot_size:,} sqft" if property.lot_size else "N/A"),
            ("Price/SqFt", f"${property.price_per_sqft:,.0f}" if property.price_per_sqft else "N/A"),
            ("Days on Market", f"{property.days_on_market}" if property.days_on_market else "N/A"),
            ("Listing Date", property.listing_date_display),
            ("Status", property.status.replace("_", " ").title()),
        ]
        
        for feature, value in details:
            table.add_row(feature, str(value))
        
        if property.parking:
            table.add_row("Parking", property.parking_display)
        
        return table
    
    def create_features_panel(self, property: PropertyListing) -> Panel:
        """Create a panel showing property features and amenities."""
        content = ""
        
        if property.features:
            content += "[bold yellow]Features:[/bold yellow]\n"
            for feature in property.features[:self.config.max_features]:
                content += f"  • {feature}\n"
        
        if not content:
            content = "No special features listed"
        
        return Panel(
            content.strip(),
            title="Features & Amenities",
            border_style="green",
            padding=(1, 2)
        )
    
    def create_neighborhood_panel(self, neighborhood: NeighborhoodModel) -> Panel:
        """Create a panel with neighborhood information."""
        content = Text()
        
        content.append(f"{neighborhood.name}\n", style="bold cyan")
        if neighborhood.full_location:
            content.append(f"{neighborhood.full_location}\n\n", style="dim")
        
        if neighborhood.population:
            content.append(f"Population: ", style="yellow")
            content.append(f"{neighborhood.population:,}\n")
        
        if neighborhood.walkability_score:
            content.append(f"Walkability Score: ", style="yellow")
            score = neighborhood.walkability_score
            style = "green" if score >= 70 else "yellow" if score >= 50 else "red"
            content.append(f"{score}/100 ({neighborhood.walkability_category})\n", style=style)
        
        if neighborhood.school_rating:
            content.append(f"School Rating: ", style="yellow")
            content.append(neighborhood.school_rating_display + "\n")
        
        if neighborhood.description:
            max_length = 200
            desc = neighborhood.description[:max_length]
            if len(neighborhood.description) > max_length:
                desc += "..."
            content.append(f"\n{desc}\n", style="italic")
        
        if neighborhood.amenities:
            content.append("\nLocal Amenities:\n", style="bold yellow")
            for amenity in neighborhood.amenities[:5]:
                content.append(f"  • {amenity}\n")
        
        return Panel(
            content,
            title="📍 Neighborhood Information",
            border_style="yellow",
            padding=(1, 2)
        )
    
    def create_wikipedia_panel(self, articles: List[WikipediaArticle]) -> Panel:
        """Create a panel with Wikipedia article information."""
        content = Text()
        
        for i, article in enumerate(articles[:self.config.max_wikipedia_articles], 1):
            content.append(f"{i}. {article.title}", style="bold cyan")
            
            if article.relationship_type:
                content.append(f" ({article.relationship_type})", style="dim")
            
            if article.confidence:
                style = "green" if article.confidence > 0.8 else "yellow"
                content.append(f" [Relevance: {article.confidence:.0%}]\n", style=style)
            else:
                content.append("\n")
            
            if article.short_summary or article.long_summary:
                summary = article.short_summary or article.long_summary or ''
                max_len = self.config.wikipedia_summary_length
                summary_text = summary[:max_len]
                if len(summary) > max_len:
                    summary_text += "..."
                content.append(f"   {summary_text}\n", style="italic")
            
            if article.url:
                content.append(f"   🔗 {article.url}\n", style="dim blue")
            
            if i < len(articles[:self.config.max_wikipedia_articles]):
                content.append("\n")
        
        return Panel(
            content,
            title="📚 Local Area Information (from Wikipedia)",
            border_style="magenta",
            padding=(1, 2)
        )
    
    def create_description_panel(self, property: PropertyListing) -> Panel:
        """Create a panel with the property description."""
        description = property.description or ''
        
        if not description:
            description = "No description available"
        elif len(description) > self.config.description_length:
            description = description[:self.config.description_length - 3] + "..."
        
        return Panel(
            description,
            title="📝 Property Description",
            border_style="blue",
            padding=(1, 2)
        )
    
    def format_price(self, price: Optional[float]) -> str:
        """Format price with proper currency display."""
        if not price or price == 0:
            return "Price Upon Request"
        return f"${price:,.0f}"
    
    def generate_and_open_html(self, listing: RichListingModel) -> Optional[Path]:
        """
        Generate HTML for the listing and optionally open in browser.
        
        Args:
            listing: The rich listing to generate HTML for
            
        Returns:
            Path to generated HTML file or None if not generated
        """
        if not self.config.generate_html or not self.html_generator:
            return None
        
        try:
            # Prepare data for HTML generation
            property_data = listing.property_data.model_dump()
            property_data['neighborhood'] = listing.neighborhood.model_dump() if listing.neighborhood else None
            property_data['wikipedia_articles'] = [
                article.model_dump() for article in listing.wikipedia_articles
            ]
            
            # Generate HTML
            html_content = self.html_generator.generate_html(property_data)
            
            # Save HTML file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            listing_id = listing.property_data.listing_id
            filename = f"property_listing_{listing_id}_{timestamp}.html"
            html_path = self.html_generator.save_html(html_content, filename)
            
            # Open in browser if configured
            if self.config.open_in_browser:
                self._open_in_browser(html_path)
            
            return html_path
            
        except Exception as e:
            logger.error(f"Error generating HTML: {e}")
            return None
    
    def _open_in_browser(self, file_path: Path) -> bool:
        """
        Open HTML file in the default browser.
        
        Args:
            file_path: Path to HTML file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            system = platform.system()
            if system == 'Darwin':  # macOS
                subprocess.run(['open', str(file_path)], check=False)
            elif system == 'Linux':
                subprocess.run(['xdg-open', str(file_path)], check=False)
            elif system == 'Windows':
                subprocess.run(['start', str(file_path)], shell=True, check=False)
            return True
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
            return False
    
    def display_search_summary(self, result: RichListingSearchResult) -> None:
        """
        Display a summary of search results.
        
        Args:
            result: Search result to summarize
        """
        if not self.console:
            return
        
        self.console.print(Panel.fit(
            f"[bold green]✨ Search Complete[/bold green]\n"
            f"Total Results: {result.total_hits}\n"
            f"Returned: {result.returned_hits}\n"
            f"Execution Time: {result.execution_time_ms}ms",
            border_style="green"
        ))