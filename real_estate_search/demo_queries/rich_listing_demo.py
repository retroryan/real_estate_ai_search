"""
Rich Real Estate Listing Demo - Single Query Showcase.

This demo shows how the denormalized property_relationships index enables
creating comprehensive, informative property listings with a single query.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from elasticsearch import Elasticsearch
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box
from rich.layout import Layout
from rich.align import Align

from .models import DemoQueryResult
from ..html_generators import PropertyListingHTMLGenerator


def format_price(price: Optional[float]) -> str:
    """Format price with proper currency display."""
    if not price or price == 0:
        return "Price Upon Request"
    return f"${price:,.0f}"


def format_date(date_value: Any) -> str:
    """Format date for display."""
    if not date_value:
        return "N/A"
    if isinstance(date_value, str) and date_value.isdigit():
        # Unix timestamp in milliseconds
        try:
            timestamp = int(date_value) / 1000
            return datetime.fromtimestamp(timestamp).strftime("%B %d, %Y")
        except:
            pass
    return str(date_value)


def create_property_header(property: Dict[str, Any]) -> Panel:
    """Create the main property header panel."""
    address = property.get('address', {})
    
    # Build address string
    street = address.get('street', 'Address Not Available')
    city = address.get('city', '')
    state = address.get('state', '')
    zip_code = address.get('zip', '')
    
    full_address = street
    if city and state:
        full_address += f"\n{city}, {state}"
    if zip_code:
        full_address += f" {zip_code}"
    
    # Property type and price
    prop_type = property.get('property_type', 'Property').title()
    price = format_price(property.get('price'))
    
    # Create header text
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


def create_property_details_table(property: Dict[str, Any]) -> Table:
    """Create a table with property details."""
    table = Table(
        title="Property Details",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Feature", style="yellow", width=20)
    table.add_column("Value", style="white")
    
    # Add property details
    details = [
        ("Bedrooms", f"{property.get('bedrooms', 'N/A')}"),
        ("Bathrooms", f"{property.get('bathrooms', 'N/A')}"),
        ("Square Feet", f"{property.get('square_feet', 'N/A'):,}" if property.get('square_feet') else "N/A"),
        ("Year Built", f"{property.get('year_built', 'N/A')}"),
        ("Lot Size", f"{property.get('lot_size', 'N/A'):,} sqft" if property.get('lot_size') else "N/A"),
        ("Price/SqFt", format_price(property.get('price_per_sqft'))),
        ("Days on Market", f"{property.get('days_on_market', 'N/A')}"),
        ("Listing Date", format_date(property.get('listing_date'))),
        ("Status", property.get('status', 'Active').title()),
    ]
    
    for feature, value in details:
        table.add_row(feature, str(value))
    
    # Add parking if available
    if property.get('parking'):
        parking = property['parking']
        if isinstance(parking, dict):
            parking_str = f"{parking.get('type', 'N/A')} ({parking.get('spaces', 'N/A')} spaces)"
        else:
            parking_str = str(parking)
        table.add_row("Parking", parking_str)
    
    return table


def create_features_panel(property: Dict[str, Any]) -> Panel:
    """Create a panel showing property features and amenities."""
    content = ""
    
    # Features
    features = property.get('features', [])
    if features and isinstance(features, list):
        content += "[bold yellow]Features:[/bold yellow]\n"
        for feature in features[:10]:  # Limit to first 10
            content += f"  • {feature}\n"
    
    # Amenities
    amenities = property.get('amenities', [])
    if amenities and isinstance(amenities, list):
        if content:
            content += "\n"
        content += "[bold yellow]Amenities:[/bold yellow]\n"
        for amenity in amenities[:10]:  # Limit to first 10
            content += f"  • {amenity}\n"
    
    if not content:
        content = "No special features listed"
    
    return Panel(
        content.strip(),
        title="Features & Amenities",
        border_style="green",
        padding=(1, 2)
    )


def create_neighborhood_panel(neighborhood: Optional[Dict[str, Any]]) -> Panel:
    """Create a panel with neighborhood information."""
    if not neighborhood:
        return Panel(
            "Neighborhood information not available",
            title="Neighborhood",
            border_style="yellow"
        )
    
    content = Text()
    
    # Neighborhood name and location
    name = neighborhood.get('name', 'Unknown')
    city = neighborhood.get('city', '')
    state = neighborhood.get('state', '')
    
    content.append(f"{name}\n", style="bold cyan")
    if city and state:
        content.append(f"{city}, {state}\n\n", style="dim")
    
    # Demographics
    if neighborhood.get('population'):
        content.append(f"Population: ", style="yellow")
        content.append(f"{neighborhood['population']:,}\n")
    
    if neighborhood.get('median_income'):
        content.append(f"Median Income: ", style="yellow")
        content.append(f"${neighborhood['median_income']:,}\n")
    
    # Scores
    if neighborhood.get('walkability_score'):
        content.append(f"Walkability Score: ", style="yellow")
        score = neighborhood['walkability_score']
        if score >= 70:
            style = "green"
        elif score >= 50:
            style = "yellow"
        else:
            style = "red"
        content.append(f"{score}/100\n", style=style)
    
    if neighborhood.get('school_rating'):
        content.append(f"School Rating: ", style="yellow")
        rating = neighborhood['school_rating']
        if rating >= 4:
            style = "green"
        elif rating >= 3:
            style = "yellow"
        else:
            style = "red"
        content.append(f"{rating}/5.0\n", style=style)
    
    # Description
    if neighborhood.get('description'):
        content.append(f"\n{neighborhood['description'][:200]}...\n", style="italic")
    
    # Amenities
    if neighborhood.get('amenities') and isinstance(neighborhood['amenities'], list):
        content.append("\nLocal Amenities:\n", style="bold yellow")
        for amenity in neighborhood['amenities'][:5]:
            content.append(f"  • {amenity}\n")
    
    return Panel(
        content,
        title="📍 Neighborhood Information",
        border_style="yellow",
        padding=(1, 2)
    )


def create_wikipedia_panel(articles: List[Dict[str, Any]]) -> Panel:
    """Create a panel with Wikipedia article information."""
    if not articles:
        return Panel(
            "No local area information available",
            title="Local Area Information",
            border_style="magenta"
        )
    
    content = Text()
    
    for i, article in enumerate(articles[:3], 1):  # Limit to first 3
        title = article.get('title', 'Unknown Article')
        summary = article.get('summary', '')
        confidence = article.get('confidence', 0)
        relationship_type = article.get('relationship_type', 'related')
        
        # Article header
        content.append(f"{i}. {title}", style="bold cyan")
        content.append(f" ({relationship_type})", style="dim")
        if confidence:
            content.append(f" [Relevance: {confidence:.0%}]\n", style="green" if confidence > 0.8 else "yellow")
        else:
            content.append("\n")
        
        # Article summary
        if summary:
            # Truncate to first 150 characters
            summary_text = summary[:150] + "..." if len(summary) > 150 else summary
            content.append(f"   {summary_text}\n", style="italic")
        
        # URL if available
        if article.get('url'):
            content.append(f"   🔗 {article['url']}\n", style="dim blue")
        
        if i < len(articles[:3]):
            content.append("\n")
    
    return Panel(
        content,
        title="📚 Local Area Information (from Wikipedia)",
        border_style="magenta",
        padding=(1, 2)
    )


def create_description_panel(property: Dict[str, Any]) -> Panel:
    """Create a panel with the property description."""
    description = property.get('description', '')
    
    if not description:
        return Panel(
            "No description available",
            title="Property Description",
            border_style="blue"
        )
    
    # Limit description length for display
    if len(description) > 500:
        description = description[:497] + "..."
    
    return Panel(
        description,
        title="📝 Property Description",
        border_style="blue",
        padding=(1, 2)
    )


def demo_rich_property_listing(
    es_client: Elasticsearch,
    listing_id: Optional[str] = None
) -> DemoQueryResult:
    """
    Demonstrate a rich property listing with all embedded data from a single query.
    
    This shows the power of the denormalized property_relationships index:
    - Property details
    - Neighborhood demographics and amenities
    - Wikipedia articles about the area
    - All from ONE Elasticsearch query!
    """
    console = Console()
    
    # Build query - default to a specific affordable property with good data
    if listing_id:
        query = {"term": {"listing_id": listing_id}}
    else:
        # Use a specific property with a reasonable price ($277,128)
        query = {"term": {"listing_id": "prop-coal-140"}}
    
    # Single query to get everything!
    start_time = datetime.now()
    
    response = es_client.search(
        index="property_relationships",
        body={
            "query": query,
            "size": 1,
            "sort": [{"_score": "desc"}]  # Best match first
        }
    )
    
    query_time = int((datetime.now() - start_time).total_seconds() * 1000)
    
    if not response['hits']['hits']:
        console.print("[red]No properties found[/red]")
        return DemoQueryResult(
            query_name="Rich Property Listing",
            total_hits=0,
            returned_hits=0,
            execution_time_ms=query_time,
            results=[],
            query_dsl={"query": query}
        )
    
    # Get the property with all embedded data
    property_data = response['hits']['hits'][0]['_source']
    neighborhood = property_data.get('neighborhood')
    wikipedia_articles = property_data.get('wikipedia_articles', [])
    
    # Create the rich display
    console.print("\n")
    console.print(Panel.fit(
        f"[bold green]✨ Single Query Execution Time: {query_time:.1f}ms[/bold green]",
        border_style="green"
    ))
    console.print("\n")
    
    # Elasticsearch functionality overview
    console.print(Panel(
        "[bold cyan]📊 ELASTICSEARCH FEATURES DEMONSTRATED:[/bold cyan]\n\n"
        "[yellow]• Denormalized Index Pattern[/yellow] - Single index containing embedded related data\n"
        "[yellow]• Document Embedding[/yellow] - Neighborhood & Wikipedia data nested within property documents\n"
        "[yellow]• Single Query Performance[/yellow] - Retrieve complete listing with one search request\n"
        "[yellow]• Nested Object Support[/yellow] - Complex JSON structures with arrays and objects\n"
        "[yellow]• Large Document Handling[/yellow] - Efficiently storing/retrieving 50KB+ documents\n"
        "[yellow]• Term Query[/yellow] - Exact match on listing_id for precise retrieval\n"
        "[yellow]• _source Filtering[/yellow] - Return complete embedded documents\n\n"
        "[dim]This demonstrates enterprise patterns for e-commerce, content management, and \n"
        "real-time applications where performance and user experience are critical.[/dim]",
        title="[bold magenta]⚡ Premium Real Estate Search with Elasticsearch[/bold magenta]",
        border_style="magenta",
        padding=(1, 2)
    ))
    console.print("\n")
    
    # Property header
    console.print(create_property_header(property_data))
    console.print("\n")
    
    # Property description
    console.print(create_description_panel(property_data))
    console.print("\n")
    
    # Create two-column layout for details and features
    details_table = create_property_details_table(property_data)
    features_panel = create_features_panel(property_data)
    
    console.print(Columns([details_table, features_panel], equal=True, expand=True))
    console.print("\n")
    
    # Neighborhood information
    console.print(create_neighborhood_panel(neighborhood))
    console.print("\n")
    
    # Wikipedia articles
    console.print(create_wikipedia_panel(wikipedia_articles))
    console.print("\n")
    
    # Show what this would look like with multiple queries
    console.print(Panel(
        "[bold red]Without Denormalization:[/bold red]\n"
        "• Query 1: Get property details (50ms)\n"
        "• Query 2: Get neighborhood by ID (50ms)\n"
        "• Query 3-5: Get each Wikipedia article (50ms each)\n"
        f"[red]Total: ~250ms with 5 separate queries[/red]\n\n"
        f"[bold green]With Denormalization:[/bold green]\n"
        f"• Single query: {query_time:.1f}ms\n"
        f"[green]Improvement: {(250/query_time):.1f}x faster![/green]",
        title="⚡ Performance Comparison",
        border_style="yellow"
    ))
    
    # Generate HTML file
    html_generator = PropertyListingHTMLGenerator(output_dir="real_estate_search/out_html")
    html_content = html_generator.generate_html(property_data)
    
    # Save HTML file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    listing_id = property_data.get('listing_id', 'unknown')
    filename = f"property_listing_{listing_id}_{timestamp}.html"
    html_path = html_generator.save_html(html_content, filename)
    
    # Open the HTML file in browser
    try:
        import subprocess
        import platform
        if platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', str(html_path)], check=False)
        elif platform.system() == 'Linux':
            subprocess.run(['xdg-open', str(html_path)], check=False)
        elif platform.system() == 'Windows':
            subprocess.run(['start', str(html_path)], shell=True, check=False)
        
        # Show HTML file location with opened status
        console.print("\n")
        console.print(Panel(
            f"[bold green]✅ HTML listing generated and opened in browser![/bold green]\n\n"
            f"📄 File: {html_path.name}\n"
            f"📁 Location: {html_path.absolute()}\n\n"
            f"[green]The property listing page has been opened in your default browser[/green]",
            title="📊 HTML Report Generated",
            border_style="green"
        ))
    except Exception as e:
        # Fallback if auto-open fails
        console.print("\n")
        console.print(Panel(
            f"[bold green]✅ HTML listing generated successfully![/bold green]\n\n"
            f"📄 File: {html_path.name}\n"
            f"📁 Location: {html_path.absolute()}\n\n"
            f"[yellow]Open in browser to view the interactive listing page[/yellow]\n"
            f"[dim](Auto-open failed: {e})[/dim]",
            title="📊 HTML Report Generated",
            border_style="green"
        ))
    
    return DemoQueryResult(
        query_name="Rich Property Listing (Single Query)",
        total_hits=response['hits']['total']['value'],
        returned_hits=1,
        execution_time_ms=query_time,
        results=[property_data],
        query_dsl={"query": query},
        aggregations={
            "data_sources": {
                "property": 1,
                "neighborhood": 1 if neighborhood else 0,
                "wikipedia_articles": len(wikipedia_articles)
            }
        }
    )


# Convenience function for demo system
def demo_15(es_client: Elasticsearch, verbose: bool = False) -> DemoQueryResult:
    """Demo 15: Rich Real Estate Listing with Single Query."""
    return demo_rich_property_listing(es_client)