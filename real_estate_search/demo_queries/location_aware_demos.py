"""
Location-aware hybrid search demos for Real Estate AI Search.

This module demonstrates location-aware hybrid search capabilities that combine:
1. Natural language location understanding using DSPy
2. Semantic vector search for property features
3. Traditional text search for keyword matching
4. Elasticsearch's native RRF for result fusion
5. Geographic filtering based on extracted location intent

SEARCH PATTERNS DEMONSTRATED:
- City-specific searches with property type filtering
- State and city combinations with lifestyle queries
- Neighborhood-level searches with architectural styles
- Proximity-based searches with distance understanding
- Multi-location entity recognition and filtering
"""

import logging
from typing import Dict, Any, List
from elasticsearch import Elasticsearch
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from .models import DemoQueryResult
from .demo_utils import format_demo_header
from .display_formatter import PropertyDisplayFormatter
from ..hybrid import HybridSearchEngine

logger = logging.getLogger(__name__)


class LocationAwareDisplayFormatter:
    """Rich console formatter for location-aware hybrid search results."""
    
    @staticmethod
    def format_location_info(result: Dict[str, Any]) -> Text:
        """Format location information with rich styling."""
        location_parts = []
        
        # Extract address info
        address = result.get('address', {})
        if address.get('city'):
            location_parts.append(f"🏙️  {address['city']}")
        if address.get('state'):
            location_parts.append(f"🗺️  {address['state']}")
        if result.get('neighborhood', {}).get('name'):
            location_parts.append(f"🏘️  {result['neighborhood']['name']}")
        
        location_text = Text()
        if location_parts:
            location_text.append(" | ".join(location_parts), style="blue")
        else:
            location_text.append("📍 Location details not available", style="dim")
            
        return location_text
    
    @staticmethod
    def format_hybrid_score(result: Dict[str, Any]) -> Text:
        """Format hybrid search score with visual indicator."""
        score = result.get('_hybrid_score', 0)
        
        # Create visual score bar
        score_text = Text()
        score_text.append(f"🎯 {score:.3f}", style="green bold")
        
        # Add score bar visualization
        bar_length = int(score * 20) if score <= 1.0 else 20
        score_text.append(" ")
        score_text.append("█" * bar_length, style="green")
        score_text.append("░" * (20 - bar_length), style="dim")
        
        return score_text
    
    @staticmethod
    def create_location_results_table(results: List[Dict[str, Any]], query: str) -> Table:
        """Create rich table for location-aware search results - showing top 5."""
        table = Table(
            title=f"🏠 Top 5 Properties - Location-Aware Hybrid Search: '{query}'",
            box=box.DOUBLE_EDGE,
            title_style="bold cyan",
            show_header=True,
            header_style="bold magenta",
            expand=True,
            padding=(0, 1)
        )
        
        # Define columns with better widths
        table.add_column("#", style="dim", width=3, justify="center")
        table.add_column("Property Details", style="white", width=45)
        table.add_column("Location", style="blue", width=30)
        table.add_column("Price", style="green bold", justify="right", width=15)
        table.add_column("Description", style="yellow", width=50)
        table.add_column("Score", style="cyan bold", width=12, justify="center")
        
        # Add rows - only top 5
        for idx, result in enumerate(results[:5], 1):
            # Property info with better formatting
            property_type = PropertyDisplayFormatter.format_property_type(result.get('property_type', ''))
            bedrooms = result.get('bedrooms', 0)
            bathrooms = result.get('bathrooms', 0)
            sqft = result.get('square_feet', 0)
            year_built = result.get('year_built', 'N/A')
            
            property_info = Text()
            property_info.append(f"{property_type}\n", style="bold white")
            property_info.append(f"🛏️  {bedrooms} bed | 🚿 {bathrooms} bath\n", style="cyan")
            property_info.append(f"📐 {sqft:,} sqft | 🏗️  Built {year_built}", style="dim")
            
            # Enhanced location info
            address = result.get('address', {})
            location_parts = []
            if address.get('street'):
                location_parts.append(f"📍 {address['street']}")
            if address.get('city'):
                location_parts.append(f"🏙️  {address['city']}")
            if address.get('state'):
                location_parts.append(f"{address['state']}")
            if address.get('zip'):
                location_parts.append(f"📮 {address['zip']}")
            
            neighborhood = result.get('neighborhood', {})
            if neighborhood.get('name'):
                location_parts.append(f"\n🏘️  {neighborhood['name']}")
                
            location_text = Text("\n".join(location_parts), style="blue")
            
            # Price with better formatting
            price = result.get('price', 0)
            price_formatted = Text()
            price_formatted.append("💰 ", style="green")
            price_formatted.append(PropertyDisplayFormatter.format_price(price), style="bold green")
            
            # Property description (truncated if too long)
            description = result.get('description', 'No description available')
            if len(description) > 150:
                description = description[:147] + "..."
            description_text = Text(description, style="italic")
            
            # Hybrid score with visual
            score = result.get('_hybrid_score', 0)
            score_bar_length = int(score * 5) if score <= 1.0 else 5
            score_text = Text()
            score_text.append(f"{score:.3f}\n", style="bold cyan")
            score_text.append("⭐" * score_bar_length, style="yellow")
            score_text.append("☆" * (5 - score_bar_length), style="dim")
            
            table.add_row(
                str(idx),
                property_info,
                location_text,
                price_formatted,
                description_text,
                score_text
            )
        
        return table
    
    @staticmethod
    def create_location_features_panel(example: "LocationAwareSearchExample") -> Panel:
        """Create panel showing location understanding features."""
        content = Text()
        
        content.append("🧠 Location Understanding:\n", style="bold blue")
        for feature in example.location_features:
            content.append(f"  • {feature}\n", style="blue")
        
        content.append("\n🏠 Property Features:\n", style="bold green")  
        for feature in example.property_features:
            content.append(f"  • {feature}\n", style="green")
        
        return Panel(
            content,
            title="Search Intelligence",
            border_style="cyan",
            box=box.ROUNDED
        )
    
    @staticmethod
    def display_location_demo_results(
        result: DemoQueryResult,
        example: "LocationAwareSearchExample",
        console: Console = None
    ) -> None:
        """Display location-aware demo results with rich formatting."""
        if console is None:
            console = Console()
        
        # Header
        console.print(f"\n{'='*80}", style="cyan")
        console.print(f"🌍 LOCATION-AWARE HYBRID SEARCH", style="bold cyan", justify="center")
        console.print(f"{'='*80}", style="cyan")
        
        # Query and description
        console.print(f"\n🔍 Query: [bold white]{example.query}[/bold white]")
        console.print(f"📝 {example.description}\n")
        
        # Performance metrics
        metrics_text = Text()
        metrics_text.append(f"⏱️  {result.execution_time_ms}ms", style="green")
        metrics_text.append("  |  ")
        metrics_text.append(f"📊 {result.total_hits} total", style="blue")
        metrics_text.append("  |  ")
        metrics_text.append(f"📄 {result.returned_hits} returned", style="yellow")
        console.print(Panel(metrics_text, title="Performance", border_style="green"))
        
        # Location understanding features
        console.print(LocationAwareDisplayFormatter.create_location_features_panel(example))
        
        # Results table
        if result.results:
            table = LocationAwareDisplayFormatter.create_location_results_table(
                result.results, example.query
            )
            console.print(table)
        else:
            console.print("📭 No results found", style="yellow")


class LocationAwareSearchExample(BaseModel):
    """Single location-aware search example with metadata."""
    query: str = Field(..., description="Natural language search query with location")
    description: str = Field(..., description="Description of what this demo shows")
    location_features: List[str] = Field(..., description="Location understanding features demonstrated")
    property_features: List[str] = Field(..., description="Property search features demonstrated")


# Example query library with 10 diverse location patterns using actual data locations
LOCATION_SEARCH_EXAMPLES: List[LocationAwareSearchExample] = [
    LocationAwareSearchExample(
        query="Luxury waterfront condo in San Francisco",
        description="City search combining luxury features and waterfront proximity",
        location_features=["City extraction: San Francisco", "Luxury property filtering", "Waterfront proximity understanding"],
        property_features=["Semantic understanding of 'luxury'", "Property type: condo", "Waterfront feature matching"]
    ),
    LocationAwareSearchExample(
        query="Family home near good schools in San Jose California", 
        description="City and state search with lifestyle-oriented queries about schools",
        location_features=["City extraction: San Jose", "State extraction: California", "Proximity understanding: 'near schools'"],
        property_features=["Family-oriented property search", "School district considerations", "Lifestyle feature matching"]
    ),
    LocationAwareSearchExample(
        query="Modern apartment in Oakland",
        description="City-level search with architectural style preferences",
        location_features=["City extraction: Oakland", "Urban area understanding", "Bay Area location"],
        property_features=["Architectural style: modern", "Property type: apartment", "Urban lifestyle features"]
    ),
    LocationAwareSearchExample(
        query="Investment property in Salinas California",
        description="Investment-focused search with city and state targeting",
        location_features=["City extraction: Salinas", "State extraction: California", "Investment market understanding"],
        property_features=["Investment property search", "Market value assessment", "ROI potential features"]
    ),
    LocationAwareSearchExample(
        query="Historic home in San Francisco CA",
        description="City and state search with historic architectural focus",
        location_features=["City extraction: San Francisco", "State extraction: CA", "Historic property understanding"],
        property_features=["Architecture: historic", "Character property features", "Urban neighborhood character"]
    ),
    LocationAwareSearchExample(
        query="Affordable house in Oakland California",
        description="City search with budget-conscious requirements",
        location_features=["City extraction: Oakland", "State extraction: California", "Budget area understanding"],
        property_features=["Property type: house", "Affordable pricing features", "Value-oriented search"]
    ),
    LocationAwareSearchExample(
        query="Condo with amenities in San Jose",
        description="City search with amenity focus",
        location_features=["City extraction: San Jose", "Urban location understanding", "Silicon Valley area"],
        property_features=["Property type: condo", "Amenity matching", "Modern living features"]
    ),
    LocationAwareSearchExample(
        query="Single family home in San Francisco Bay Area",
        description="Region search emphasizing property type",
        location_features=["City extraction: San Francisco", "Region: Bay Area", "Metropolitan area understanding"],
        property_features=["Property type: single-family", "Residential features", "Family home characteristics"]
    ),
    LocationAwareSearchExample(
        query="Townhouse in Oakland under 800k",
        description="City search with property type and price constraints",
        location_features=["City extraction: Oakland", "East Bay location", "Urban market understanding"],
        property_features=["Property type: townhouse", "Price constraint filtering", "Value assessment features"]
    ),
    LocationAwareSearchExample(
        query="Modern condo with parking in San Francisco California",
        description="City and state search with specific amenity requirements",
        location_features=["City extraction: San Francisco", "State extraction: California", "Urban location character"],
        property_features=["Property type: condo", "Amenity: parking", "Modern architecture features"]
    )
]


def demo_location_aware_waterfront_luxury(
    es_client: Elasticsearch,
    size: int = 10
) -> DemoQueryResult:
    """
    Demo: Luxury waterfront properties with city-specific filtering.
    
    Demonstrates location extraction for premium waterfront searches
    combining luxury features with geographic precision.
    """
    example = LOCATION_SEARCH_EXAMPLES[0]
    return _execute_location_demo(es_client, example, size)


def demo_location_aware_family_schools(
    es_client: Elasticsearch, 
    size: int = 10
) -> DemoQueryResult:
    """
    Demo: Family-oriented search with school proximity considerations.
    
    Shows complex location understanding for lifestyle-based queries
    involving city, state, and proximity factors.
    """
    example = LOCATION_SEARCH_EXAMPLES[1]
    return _execute_location_demo(es_client, example, size)


def demo_location_aware_urban_modern(
    es_client: Elasticsearch,
    size: int = 10
) -> DemoQueryResult:
    """
    Demo: Urban neighborhood search with modern architectural preferences.
    
    Demonstrates neighborhood-level location extraction combined
    with architectural style semantic understanding.
    """
    example = LOCATION_SEARCH_EXAMPLES[2]
    return _execute_location_demo(es_client, example, size)


def demo_location_aware_recreation_mountain(
    es_client: Elasticsearch,
    size: int = 10
) -> DemoQueryResult:
    """
    Demo: Recreation-focused property search with mountain access.
    
    Shows location understanding for lifestyle properties
    in specific recreational markets.
    """
    example = LOCATION_SEARCH_EXAMPLES[3]
    return _execute_location_demo(es_client, example, size)


def demo_location_aware_historic_urban(
    es_client: Elasticsearch,
    size: int = 10
) -> DemoQueryResult:
    """
    Demo: Historic property search in urban neighborhoods.
    
    Demonstrates multi-level location extraction (neighborhood, city, state)
    with historic architectural feature understanding.
    """
    example = LOCATION_SEARCH_EXAMPLES[4]
    return _execute_location_demo(es_client, example, size)


def demo_location_aware_beach_proximity(
    es_client: Elasticsearch,
    size: int = 10
) -> DemoQueryResult:
    """
    Demo: Beach property search with proximity requirements.
    
    Shows proximity-based location understanding combined
    with coastal lifestyle feature matching.
    """
    example = LOCATION_SEARCH_EXAMPLES[5]
    return _execute_location_demo(es_client, example, size)


def demo_location_aware_investment_market(
    es_client: Elasticsearch,
    size: int = 10
) -> DemoQueryResult:
    """
    Demo: Investment property search with market-specific targeting.
    
    Demonstrates business-focused location search with
    price constraints and market understanding.
    """
    example = LOCATION_SEARCH_EXAMPLES[6]
    return _execute_location_demo(es_client, example, size)


def demo_location_aware_luxury_urban_views(
    es_client: Elasticsearch,
    size: int = 10
) -> DemoQueryResult:
    """
    Demo: Luxury urban property search emphasizing premium views.
    
    Shows high-end property location targeting with
    luxury feature and view preference understanding.
    """
    example = LOCATION_SEARCH_EXAMPLES[7]
    return _execute_location_demo(es_client, example, size)


def demo_location_aware_suburban_architecture(
    es_client: Elasticsearch,
    size: int = 10
) -> DemoQueryResult:
    """
    Demo: Architectural style search in suburban markets.
    
    Demonstrates area-type understanding (suburban) with
    specific architectural style preferences.
    """
    example = LOCATION_SEARCH_EXAMPLES[8]
    return _execute_location_demo(es_client, example, size)


def demo_location_aware_neighborhood_character(
    es_client: Elasticsearch,
    size: int = 10
) -> DemoQueryResult:
    """
    Demo: Neighborhood character search with architectural details.
    
    Shows fine-grained neighborhood understanding combined
    with specific architectural feature requirements.
    """
    example = LOCATION_SEARCH_EXAMPLES[9]
    return _execute_location_demo(es_client, example, size)


def _execute_location_demo(
    es_client: Elasticsearch,
    example: LocationAwareSearchExample,
    size: int
) -> DemoQueryResult:
    """
    Execute a location-aware demo search.
    
    EFFICIENT SEARCH PATTERN IMPLEMENTATION:
    This function demonstrates the OPTIMAL approach to filtered vector search:
    
    1. Location Extraction (DSPy):
       - Natural language understanding extracts city, state, etc.
       - Creates a cleaned query without location terms
    
    2. Filter Application (CRITICAL for performance):
       - Filters are applied DURING both text and vector search
       - knn.filter parameter ensures vector search is filtered efficiently
       - bool.filter ensures text search is filtered consistently
       - This is the CORRECT pattern - filters reduce search space before scoring
    
    3. Native RRF Fusion:
       - Elasticsearch combines filtered results from both retrievers
       - Maintains the benefits of both search strategies
       - More efficient than manual score combination
    
    ANTI-PATTERN AVOIDED:
    We do NOT use post_filter which would:
    - Compute similarities for ALL vectors first (expensive!)
    - Then filter results (wasteful)
    - Potentially return fewer results than requested
    
    Instead, our knn.filter approach:
    - Reduces the search space BEFORE computing similarities
    - Only computes expensive vector operations on relevant documents
    - Guarantees the requested number of results (if available)
    
    Args:
        es_client: Elasticsearch client
        example: Search example configuration
        size: Number of results to return
        
    Returns:
        DemoQueryResult with location-aware search results
    """
    logger.info(f"Executing location-aware demo: '{example.query}'")
    
    # Initialize hybrid search engine with efficient filtering built-in
    engine = HybridSearchEngine(es_client)
    
    try:
        # Execute location-aware hybrid search
        # This calls search_with_location which:
        # 1. Extracts location using DSPy
        # 2. Builds filters from location intent
        # 3. Applies filters DURING search (not after) for both text and vector
        result = engine.search_with_location(example.query, size)
        
        # Convert to demo format
        demo_results = []
        for search_result in result.results:
            demo_result = search_result.property_data.copy()
            demo_result['_hybrid_score'] = search_result.hybrid_score
            demo_result['_location_aware'] = True
            demo_results.append(demo_result)
        
        # Build comprehensive query DSL representation
        query_dsl = {
            "description": "Location-aware hybrid search with RRF",
            "components": {
                "location_extraction": "DSPy-powered natural language location understanding",
                "text_search": "Multi-field text search with location filtering",
                "vector_search": "1024-dimensional semantic search with location filtering", 
                "rrf_fusion": "Native Elasticsearch reciprocal rank fusion",
                "location_filters": "Geographic constraints from extracted location intent"
            },
            "query_pattern": example.query
        }
        
        # Build feature list
        es_features = [
            "Location-Aware Hybrid Search - DSPy + RRF integration",
            "Natural Language Location Extraction - City, state, neighborhood understanding",
            "Multi-Modal Search Fusion - Text + Vector + Geographic constraints",
            "Elasticsearch Native RRF - Retriever syntax with rank_constant=60",
            f"Query executed in {result.execution_time_ms}ms with location filtering applied"
        ]
        es_features.extend(example.location_features)
        es_features.extend(example.property_features)
        
        return DemoQueryResult(
            query_name=f"Location-Aware Hybrid: '{example.query}'",
            query_description=example.description,
            execution_time_ms=result.execution_time_ms,
            total_hits=result.total_hits,
            returned_hits=len(demo_results),
            results=demo_results,
            query_dsl=query_dsl,
            es_features=es_features,
            indexes_used=[
                "properties index - Real estate listings with embeddings and location fields",
                "Location-aware RRF fusion of text, vector, and geographic search strategies"
            ]
        )
        
    except Exception as e:
        logger.error(f"Location-aware demo failed for query '{example.query}': {e}")
        raise


def demo_location_aware_search_showcase(
    es_client: Elasticsearch,
    show_all_examples: bool = False,
    size: int = 5
) -> List[DemoQueryResult]:
    """
    Showcase multiple location-aware search examples.
    
    Runs a curated selection of location-aware demos to demonstrate
    the full range of location understanding and hybrid search capabilities.
    
    Args:
        es_client: Elasticsearch client
        show_all_examples: If True, runs all 10 examples; if False, runs 5 selected examples
        size: Number of results per demo
        
    Returns:
        List of DemoQueryResult objects
    """
    logger.info(f"Running location-aware search showcase (show_all={show_all_examples})")
    
    # Select examples to run
    if show_all_examples:
        examples = LOCATION_SEARCH_EXAMPLES
    else:
        # Curated selection showing variety - indices 0, 1, 3, 8, 9
        examples = [
            LOCATION_SEARCH_EXAMPLES[0],  # Luxury waterfront in SF
            LOCATION_SEARCH_EXAMPLES[1],  # Family home in San Jose
            LOCATION_SEARCH_EXAMPLES[3],  # Investment property in Salinas
            LOCATION_SEARCH_EXAMPLES[8],  # Condo with amenities in San Jose
            LOCATION_SEARCH_EXAMPLES[9],  # Modern condo in SF
        ]
    
    results = []
    showcase_data = []  # Store data for summary display
    
    # Display showcase header
    console = Console()
    console.print("\n[bold cyan]🌍 Location-Aware Search Showcase[/bold cyan]")
    console.print("=" * 70)
    console.print("[yellow]Processing location-aware searches...[/yellow]")
    
    # Use progress indicator for cleaner output
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Running searches...", total=len(examples))
        
        for i, example in enumerate(examples, 1):
            try:
                progress.update(task, description=f"Processing: {example.query[:50]}...")
                logger.info(f"Executing location-aware demo: '{example.query}'")
                
                # Execute the demo
                result = _execute_location_demo(es_client, example, size)
                results.append(result)
                
                # Save data for summary
                if hasattr(result, 'results') and result.results:
                    top_results = []
                    for prop in result.results[:3]:
                        address = prop.get('address', {})
                        top_results.append({
                            'street': address.get('street', 'Unknown'),
                            'city': address.get('city', 'Unknown'),
                            'price': prop.get('price', 0),
                            'type': prop.get('property_type', 'Unknown')
                        })
                    
                    showcase_data.append({
                        'query': example.query,
                        'description': example.description,
                        'total_hits': result.total_hits,
                        'execution_time_ms': result.execution_time_ms,
                        'top_results': top_results,
                        'location_extracted': getattr(result, 'location_intent', {})
                    })
                else:
                    showcase_data.append({
                        'query': example.query,
                        'description': example.description,
                        'total_hits': 0,
                        'execution_time_ms': 0,
                        'top_results': [],
                        'location_extracted': {}
                    })
                    
                progress.advance(task)
                
            except Exception as e:
                logger.error(f"Example '{example.query}' failed: {e}")
                showcase_data.append({
                    'query': example.query,
                    'description': example.description,
                    'error': str(e)
                })
                progress.advance(task)
                continue
    
    # Display comprehensive summary
    console.print("\n" + "=" * 70)
    console.print("[bold green]📊 Location-Aware Search Results Summary[/bold green]")
    console.print("=" * 70 + "\n")
    
    # Create summary table
    summary_table = Table(title="Search Results Overview", box=box.ROUNDED)
    summary_table.add_column("#", style="cyan", width=3)
    summary_table.add_column("Query", style="yellow", width=35)
    summary_table.add_column("Location", style="blue", width=20)
    summary_table.add_column("Results", style="green", justify="right", width=8)
    summary_table.add_column("Time (ms)", style="magenta", justify="right", width=10)
    
    for i, data in enumerate(showcase_data, 1):
        if 'error' in data:
            summary_table.add_row(
                str(i),
                data['query'][:35],
                "❌ Error",
                "-",
                "-"
            )
        else:
            # Extract location from the query result if available
            location = "Not extracted"
            if data.get('location_extracted'):
                loc = data['location_extracted']
                if isinstance(loc, dict):
                    city = loc.get('city', '')
                    state = loc.get('state', '')
                    location = f"{city}, {state}" if state else city
            
            summary_table.add_row(
                str(i),
                data['query'][:35] + ("..." if len(data['query']) > 35 else ""),
                location,
                str(data['total_hits']),
                f"{data['execution_time_ms']:.0f}"
            )
    
    console.print(summary_table)
    
    # Display top properties for each search
    console.print("\n[bold cyan]🏠 Top Properties by Search:[/bold cyan]\n")
    
    for i, data in enumerate(showcase_data, 1):
        if 'error' not in data and data['top_results']:
            panel_content = f"[yellow]Query:[/yellow] {data['query']}\n"
            panel_content += f"[dim]{data['description']}[/dim]\n\n"
            panel_content += "[bold]Top 3 Properties:[/bold]\n"
            
            for j, prop in enumerate(data['top_results'], 1):
                panel_content += f"{j}. {prop['street']}, {prop['city']} - "
                panel_content += f"[green]${prop['price']:,.0f}[/green] "
                panel_content += f"[dim]({prop['type']})[/dim]\n"
            
            panel = Panel(
                panel_content.strip(),
                title=f"Search #{i}",
                border_style="blue",
                padding=(0, 1)
            )
            console.print(panel)
    
    # Final statistics
    if results:
        total_time = sum(r.execution_time_ms for r in results if hasattr(r, 'execution_time_ms'))
        total_hits = sum(r.total_hits for r in results if hasattr(r, 'total_hits'))
        avg_time = total_time / len(results) if results else 0
        
        stats_panel = Panel(
            f"[bold green]✅ Showcase Complete[/bold green]\n\n"
            f"[cyan]Searches Executed:[/cyan] {len(results)}/{len(examples)}\n"
            f"[yellow]Total Execution Time:[/yellow] {total_time:.0f}ms\n"
            f"[magenta]Average Query Time:[/magenta] {avg_time:.0f}ms\n"
            f"[green]Total Properties Found:[/green] {total_hits:,}\n"
            f"[blue]Average Results per Search:[/blue] {total_hits/len(results):.0f}",
            title="[bold]Performance Statistics[/bold]",
            border_style="green",
            expand=False
        )
        console.print("\n")
        console.print(stats_panel)
    
    logger.info(f"Completed showcase with {len(results)} successful demos")
    return results