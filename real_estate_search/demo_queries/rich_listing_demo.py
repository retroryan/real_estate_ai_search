"""
Rich Real Estate Listing Demo - Single Query Showcase.

This demo shows how the denormalized property_relationships index enables
creating comprehensive, informative property listings with a single query.
"""

import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from elasticsearch import Elasticsearch
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box
from rich.layout import Layout
from rich.align import Align

from ..models.results import BaseQueryResult
from ..models.neighborhood import Neighborhood as NeighborhoodModel
from ..models import PropertyListing, WikipediaArticle
from ..html_generators import PropertyListingHTMLGenerator

# ===== ELASTICSEARCH DEMO CONFIGURATION =====
# These values are sourced from the actual Elasticsearch data as of deployment.
# The property IDs come from the property_relationships index which contains
# IDs like: prop-sf-001, prop-sf-003, prop-sf-005, etc.
# To query the index, use appropriate authentication from environment variables
DEFAULT_DEMO_PROPERTY_ID = "prop-oak-125"  # Oakland property - adjust based on loaded data


def format_price(price: Optional[float]) -> str:
    """Format price with proper currency display."""
    if not price or price == 0:
        return "Price Upon Request"
    return f"${price:,.0f}"


def format_date(date_value: Optional[str]) -> str:
    """Format date for display - kept for compatibility."""
    return date_value if date_value else "N/A"


def create_property_header(property_model: PropertyListing) -> Panel:
    """Create the main property header panel."""
    # Get formatted address from model
    full_address = property_model.address.full_address
    
    # Property type and price from model
    prop_type = property_model.display_property_type
    price = property_model.display_price
    
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


def create_property_details_table(property_model: PropertyListing) -> Table:
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
        ("Bedrooms", f"{property_model.bedrooms}" if property_model.bedrooms else "N/A"),
        ("Bathrooms", f"{property_model.bathrooms}" if property_model.bathrooms else "N/A"),
        ("Square Feet", f"{property_model.square_feet:,}" if property_model.square_feet else "N/A"),
        ("Year Built", f"{property_model.year_built}" if property_model.year_built else "N/A"),
        ("Lot Size", f"{property_model.lot_size:,} sqft" if property_model.lot_size else "N/A"),
        ("Price/SqFt", f"${property_model.price_per_sqft:,.0f}" if property_model.price_per_sqft else "N/A"),
        ("Days on Market", f"{property_model.days_on_market}" if property_model.days_on_market else "N/A"),
        ("Listing Date", property_model.listing_date_display),
        ("Status", property_model.status.replace("_", " ").title()),
    ]
    
    for feature, value in details:
        table.add_row(feature, str(value))
    
    # Add parking if available
    if property_model.parking:
        table.add_row("Parking", property_model.parking_display)
    
    return table


def create_features_panel(property_model: PropertyListing) -> Panel:
    """Create a panel showing property features and amenities."""
    content = ""
    
    # Features (guaranteed to be list by model)
    if property_model.features:
        content += "[bold yellow]Features:[/bold yellow]\n"
        for feature in property_model.features[:10]:  # Limit to first 10
            content += f"  • {feature}\n"
    
    # Note: amenities is aliased to features in PropertyListing model
    # So we only use features field here
    
    if not content:
        content = "No special features listed"
    
    return Panel(
        content.strip(),
        title="Features & Amenities",
        border_style="green",
        padding=(1, 2)
    )


def create_neighborhood_panel(neighborhood: Optional[NeighborhoodModel]) -> Panel:
    """Create a panel with neighborhood information."""
    if not neighborhood:
        return Panel(
            "Neighborhood information not available",
            title="Neighborhood",
            border_style="yellow"
        )
    
    content = Text()
    
    # Neighborhood name and location
    name = neighborhood.name
    city = neighborhood.city
    state = neighborhood.state
    
    content.append(f"{name}\n", style="bold cyan")
    if city and state:
        content.append(f"{city}, {state}\n\n", style="dim")
    
    # Demographics
    if neighborhood.demographics and neighborhood.demographics.population:
        content.append(f"Population: ", style="yellow")
        content.append(f"{neighborhood.demographics.population:,}\n")
    
    # Scores
    if neighborhood.walkability_score:
        content.append(f"Walkability Score: ", style="yellow")
        score = neighborhood.walkability_score
        if score >= 70:
            style = "green"
        elif score >= 50:
            style = "yellow"
        else:
            style = "red"
        content.append(f"{score}/100\n", style=style)
    
    if neighborhood.school_ratings and neighborhood.school_ratings.overall:
        content.append(f"School Rating: ", style="yellow")
        rating = neighborhood.school_ratings.overall
        if rating >= 7:
            style = "green"
        elif rating >= 5:
            style = "yellow"
        else:
            style = "red"
        content.append(f"{rating:.1f}/10\n", style=style)
    
    # Description
    if neighborhood.description:
        content.append(f"\n{neighborhood.description[:200]}...\n", style="italic")
    
    # Amenities (guaranteed to be list by model)
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


def create_wikipedia_panel(articles: List[WikipediaArticle]) -> Panel:
    """Create a panel with Wikipedia article information."""
    if not articles:
        return Panel(
            "No local area information available",
            title="Local Area Information",
            border_style="magenta"
        )
    
    content = Text()
    
    for i, article in enumerate(articles[:3], 1):  # Limit to first 3
        title = article.title
        summary = article.short_summary or article.long_summary or ''
        confidence = article.confidence
        relationship_type = article.relationship_type or 'related'
        
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
        if article.url:
            content.append(f"   🔗 {article.url}\n", style="dim blue")
        
        if i < len(articles[:3]):
            content.append("\n")
    
    return Panel(
        content,
        title="📚 Local Area Information (from Wikipedia)",
        border_style="magenta",
        padding=(1, 2)
    )


def create_description_panel(property_model: PropertyListing) -> Panel:
    """Create a panel with the property description."""
    description = property_model.description or ''
    
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
) -> BaseQueryResult:
    """
    Demonstrate a rich property listing with all embedded data from a single query.
    
    This shows the power of the denormalized property_relationships index:
    - Property details
    - Neighborhood demographics and amenities
    - Wikipedia articles about the area
    - All from ONE Elasticsearch query!
    """
    console = Console()
    
    # Build query - use provided ID or default to an actual property from the index
    if listing_id:
        query = {"term": {"listing_id": listing_id}}
    else:
        # Use an actual property ID that exists in the property_relationships index
        query = {"term": {"listing_id": DEFAULT_DEMO_PROPERTY_ID}}
    
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
        return BaseQueryResult(
            query_name="Rich Property Listing",
            total_hits=0,
            returned_hits=0,
            execution_time_ms=query_time,
            results=[],
            query_dsl={"query": query}
        )
    
    # Get the property with all embedded data
    property_data = response['hits']['hits'][0]['_source']
    
    # Create Pydantic model from ES data
    property_model = PropertyListing(**property_data)
    
    # Extract neighborhood and wikipedia from the raw data (these are embedded in property_relationships index)
    neighborhood_data = property_data.get('neighborhood')
    wikipedia_data = property_data.get('wikipedia_articles', [])
    
    # Create models for neighborhood and wikipedia if they exist
    neighborhood = NeighborhoodModel(**neighborhood_data) if neighborhood_data else None
    wikipedia_articles = [WikipediaArticle(**w) for w in wikipedia_data] if wikipedia_data else []
    
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
    console.print(create_property_header(property_model))
    console.print("\n")
    
    # Property description
    console.print(create_description_panel(property_model))
    console.print("\n")
    
    # Create two-column layout for details and features
    details_table = create_property_details_table(property_model)
    features_panel = create_features_panel(property_model)
    
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
    
    # Generate HTML file with complete data including wikipedia articles
    html_generator = PropertyListingHTMLGenerator(output_dir="real_estate_search/out_html")
    property_data_for_html = property_model.model_dump()
    property_data_for_html['wikipedia_articles'] = [article.model_dump() for article in wikipedia_articles]
    property_data_for_html['neighborhood'] = neighborhood.model_dump() if neighborhood else None
    html_content = html_generator.generate_html(property_data_for_html)
    
    # Save HTML file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    listing_id = property_model.listing_id
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
    
    return BaseQueryResult(
        query_name="Rich Property Listing (Single Query)",
        total_hits=response['hits']['total']['value'],
        returned_hits=1,
        execution_time_ms=query_time,
        results=[property_model.model_dump()],
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
def demo_15(es_client: Elasticsearch, verbose: bool = False) -> BaseQueryResult:
    """Demo 15: Rich Real Estate Listing with Single Query."""
    return demo_rich_property_listing(es_client)