"""Separate result models for different entity types."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
from rich.console import Console
from rich.table import Table
from rich import box
from io import StringIO
import json
from real_estate_search.models import PropertyListing, WikipediaArticle
from real_estate_search.models.location import LocationIntent


class BaseQueryResult(BaseModel):
    """Base class for all query results."""
    query_name: str = Field(..., description="Name of the demo query")
    query_description: Optional[str] = Field(None, description="Description of what the query searches for")
    execution_time_ms: int = Field(..., description="Query execution time in milliseconds")
    total_hits: int = Field(..., description="Total number of matching documents")
    returned_hits: int = Field(..., description="Number of documents returned")
    query_dsl: Dict[str, Any] = Field(..., description="The actual Elasticsearch query used")
    es_features: Optional[List[str]] = Field(None, description="Elasticsearch features demonstrated")
    indexes_used: Optional[List[str]] = Field(None, description="Indexes queried")
    
    @abstractmethod
    def display(self, verbose: bool = False) -> str:
        """Format results for display."""
        pass
    
    def _display_header(self, console, style_buffer=None):
        """Common header display logic."""
        console.print(f"\n{'='*80}", style="cyan")
        console.print(f"🔍 Demo Query: {self.query_name}", style="bold cyan")
        console.print(f"{'='*80}", style="cyan")
        
        if self.query_description:
            console.print(f"\n📝 SEARCH DESCRIPTION:", style="bold yellow")
            console.print(f"   {self.query_description}", style="yellow")
        
        if self.es_features:
            console.print(f"\n📊 ELASTICSEARCH FEATURES:", style="bold green")
            for feature in self.es_features:
                console.print(f"   • {feature}", style="green")
        
        if self.indexes_used:
            console.print(f"\n📁 INDEXES & DOCUMENTS:", style="bold blue")
            for index_info in self.indexes_used:
                console.print(f"   • {index_info}", style="blue")
        
        console.print(f"\n{'─'*80}", style="dim")
        console.print(f"⏱️  Execution Time: {self.execution_time_ms}ms | 📊 Total Hits: {self.total_hits} | 📄 Returned: {self.returned_hits}", style="cyan")





class WikipediaSearchResult(BaseQueryResult):
    """Result for Wikipedia searches."""
    results: List[WikipediaArticle] = Field(..., description="Wikipedia article results")
    exported_articles: List[Dict[str, Any]] = Field(default_factory=list, description="Exported article information")
    html_report_path: Optional[str] = Field(None, description="Path to HTML report if generated")
    
    def display(self, verbose: bool = False) -> str:
        """Format Wikipedia results for display."""
        import json
        from rich.console import Console
        from rich.table import Table
        from rich import box
        from io import StringIO
        
        string_buffer = StringIO()
        console = Console(file=string_buffer, force_terminal=True, width=150)
        
        # Standard header with query info FIRST
        self._display_header(console)
        
        # Context Display (Demo-specific) - Full-text search overview AFTER header
        if "Full-Text Search" in self.query_name:
            console.print("\n[bold]🔍 Full-Text Search Overview:[/bold]")
            console.print("This demo showcases Wikipedia full-text search after HTML enrichment:")
            console.print()
            console.print("• Searches across complete Wikipedia article content")
            console.print("• Demonstrates various query patterns and operators")
            console.print("• Shows highlighted relevant content from articles")
            console.print("=" * 60)
        
        # Export info if available (after context, before results)
        if self.exported_articles and len(self.exported_articles) > 0:
            console.print(f"\n📥 Exporting Wikipedia articles to real_estate_search/out_html/")
            console.print("-" * 60)
            for article in self.exported_articles:
                console.print(f"✅ Exported: {article['title'][:50]} ({article['file_size_kb']:.1f} KB)")
            console.print(f"\n✅ Successfully exported {len(self.exported_articles)} articles")
        
        # HTML report info if available
        if self.html_report_path:
            console.print(f"\n📄 HTML results saved to: {self.html_report_path}")
            console.print(f"   Open in browser: file://{self.html_report_path}")
            console.print(f"\n📂 HTML report opened in browser: {self.html_report_path}")
        
        # Results Display
        if self.results and len(self.results) > 0:
            console.print(f"\n[bold magenta]📚 TOP WIKIPEDIA ARTICLES:[/bold magenta]")
            
            table = Table(
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
                show_lines=True,
                width=None
            )
            
            table.add_column("ID", style="dim", width=8, no_wrap=True)
            table.add_column("Score", style="magenta", justify="right", width=8)
            table.add_column("Title", style="cyan", width=35)
            table.add_column("Location", style="green", width=25)
            table.add_column("Summary", style="bright_blue", overflow="fold", width=50)
            
            for result in self.results[:5]:  # Limit to 5 for cleaner display
                location = f"{result.city or 'N/A'}, {result.state or 'N/A'}"
                
                summary = result.long_summary or ''
                if len(summary) > 150:
                    summary = summary[:147] + "..."
                
                table.add_row(
                    result.page_id[:6] + "..." if len(result.page_id) > 6 else result.page_id,
                    f"{result.score:.2f}" if result.score else "N/A",
                    result.title,
                    location,
                    summary
                )
            
            console.print(table)
        
        if verbose:
            console.print(f"\n{'-'*40}", style="dim")
            console.print("Query DSL:", style="bold cyan")
            console.print(f"{'-'*40}", style="dim")
            console.print(json.dumps(self.query_dsl, indent=2), style="green")
        
        output = string_buffer.getvalue()
        string_buffer.close()
        return output


class AggregationBucket(BaseModel):
    """Individual aggregation bucket."""
    key: str = Field(..., description="Bucket key")
    doc_count: int = Field(..., description="Document count in bucket")
    sub_aggregations: Optional[Dict[str, Any]] = Field(None, description="Sub-aggregations")


class AggregationSearchResult(BaseQueryResult):
    """Result for aggregation queries."""
    aggregations: Dict[str, Any] = Field(..., description="Aggregation results")
    top_properties: List[PropertyListing] = Field(default_factory=list, description="Sample properties if included")
    
    def display(self, verbose: bool = False) -> str:
        """Format aggregation results for display."""
        import json
        from rich.console import Console
        from rich.table import Table
        from rich.text import Text
        from rich import box
        from io import StringIO
        
        string_buffer = StringIO()
        console = Console(file=string_buffer, force_terminal=True, width=150)
        
        self._display_header(console)
        
        # Display aggregations based on query type
        self._display_aggregations(console)
            
        # Display sample properties if included
        if self.top_properties:
            console.print(f"\n🏠 TOP 5 PROPERTIES IN RANGE:", style="bold magenta")
            
            table = Table(
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta",
                expand=False,
                padding=(0, 1)
            )
            
            table.add_column("#", style="dim", width=3, justify="center")
            table.add_column("Property Details", style="white", width=35)
            table.add_column("Location", style="blue", width=25)
            table.add_column("Price", style="green bold", justify="right", width=12)
            table.add_column("Description", style="yellow", width=45)
            
            for idx, result in enumerate(self.top_properties[:5], 1):
                property_text = Text()
                property_text.append(f"{result.property_type}\n", style="bold")
                property_text.append(f"{result.bedrooms}bd/{result.bathrooms}ba • {result.square_feet:,} sqft\n", style="cyan")
                property_text.append(f"Built {result.year_built if result.year_built else 'N/A'}", style="dim")
                
                # Use Address model's properties directly (it's always an Address object now)
                location_parts = []
                if result.address.street:
                    location_parts.append(result.address.street)
                if result.address.city:
                    location_parts.append(result.address.city)
                if result.address.state:
                    location_parts.append(result.address.state)
                location = '\n'.join(location_parts) if location_parts else 'N/A'
                
                price_text = f"${result.price:,.0f}"
                
                description = result.description
                if len(description) > 100:
                    description = description[:97] + "..."
                
                table.add_row(str(idx), property_text, location, price_text, description)
            
            console.print(table)
        
        if verbose:
            console.print(f"\n{'-'*40}", style="dim")
            console.print("Query DSL:", style="bold cyan")
            console.print(f"{'-'*40}", style="dim")
            console.print(json.dumps(self.query_dsl, indent=2), style="green")
        
        output = string_buffer.getvalue()
        string_buffer.close()
        return output
    
    def _display_aggregations(self, console) -> None:
        """Display aggregations based on the type of aggregation query."""
        from rich.table import Table
        from rich import box
        
        # Check if this is a neighborhood statistics query (Demo 4)
        if 'by_neighborhood' in self.aggregations and 'buckets' in self.aggregations['by_neighborhood']:
            self._display_neighborhood_stats(console)
        # Check if this is a price distribution query (Demo 5)
        elif 'price_histogram' in self.aggregations and 'buckets' in self.aggregations['price_histogram']:
            self._display_price_distribution(console)
    
    def _display_neighborhood_stats(self, console) -> None:
        """Display neighborhood statistics table."""
        from rich.table import Table
        from rich import box
        
        buckets = self.aggregations['by_neighborhood']['buckets']
        if not buckets:
            return
        
        # Create neighborhood stats table
        table = Table(
            title="Neighborhood Property Statistics",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        # Add columns
        table.add_column("Neighborhood", style="cyan", width=22)
        table.add_column("Properties", style="yellow", justify="right", width=10)
        table.add_column("Avg Price", style="green", justify="right", width=10)
        table.add_column("Price Range", style="blue", justify="right", width=10)
        table.add_column("Avg Beds", style="magenta", justify="right", width=8)
        table.add_column("Avg SqFt", style="yellow", justify="right", width=10)
        table.add_column("$/SqFt", style="green", justify="right", width=8)
        
        # Add rows
        for bucket in buckets[:20]:  # Limit to top 20
            neighborhood_id = bucket['key']
            doc_count = bucket['doc_count']
            
            # Extract stats from sub-aggregations
            avg_price = bucket.get('avg_price', {}).get('value', 0)
            min_price = bucket.get('min_price', {}).get('value', 0)
            max_price = bucket.get('max_price', {}).get('value', 0)
            avg_bedrooms = bucket.get('avg_bedrooms', {}).get('value', 0)
            avg_sqft = bucket.get('avg_square_feet', {}).get('value', 0)
            
            # Calculate price per sqft
            price_per_sqft = avg_price / avg_sqft if avg_sqft > 0 else 0
            
            # Format price range
            price_range = f"${min_price/1000:.0f}k-${max_price/1000:.0f}k"
            
            table.add_row(
                neighborhood_id,
                str(doc_count),
                f"${avg_price:,.0f}",
                price_range,
                f"{avg_bedrooms:.1f}",
                f"{avg_sqft:,.0f}",
                f"${price_per_sqft:.2f}"
            )
        
        console.print(table)
    
    def _display_price_distribution(self, console) -> None:
        """Display price distribution histogram."""
        buckets = self.aggregations['price_histogram']['buckets']
        if not buckets:
            return
        
        console.print("\n[bold]Price Distribution Histogram:[/bold]")
        
        # Find max count for scaling
        max_count = max(b['doc_count'] for b in buckets) if buckets else 1
        
        # Display histogram
        for bucket in buckets[:20]:  # Limit to 20 buckets
            key = bucket['key']
            count = bucket['doc_count']
            
            # Calculate bar width
            bar_width = int((count / max_count) * 50) if max_count > 0 else 0
            bar = "█" * bar_width
            
            # Format price label
            price_label = f"${key/1000:.0f}k-${(key+100000)/1000:.0f}k"
            
            # Print histogram row with green bars
            console.print(f"  {price_label:>15} │ [green]{bar}[/green] {count}")
        
        # Display percentiles if available
        if 'price_percentiles' in self.aggregations:
            percentiles = self.aggregations['price_percentiles'].get('values', {})
            if percentiles:
                console.print("\nPrice Percentiles:", style="bold")
                for percentile, value in percentiles.items():
                    console.print(f"  {percentile}th percentile: ${value:,.0f}", style="yellow")
        
        # Display property type stats if available
        if 'by_property_type_stats' in self.aggregations:
            type_buckets = self.aggregations['by_property_type_stats'].get('buckets', [])
            if type_buckets:
                console.print("\nStatistics by Property Type:", style="bold")
                for type_bucket in type_buckets[:5]:
                    prop_type = type_bucket['key'].title() if type_bucket['key'] else "Unknown"
                    count = type_bucket['doc_count']
                    stats = type_bucket.get('price_stats', {})
                    avg_price = stats.get('avg', 0)
                    console.print(f"  {prop_type}: {count} properties, Avg: ${avg_price:,.0f}", style="cyan")


class MixedEntityResult(BaseQueryResult):
    """Result for multi-entity searches."""
    property_results: List[PropertyListing] = Field(default_factory=list, description="Property results")
    wikipedia_results: List[WikipediaArticle] = Field(default_factory=list, description="Wikipedia results")
    neighborhood_results: List[Dict[str, Any]] = Field(default_factory=list, description="Neighborhood results")
    
    def display(self, verbose: bool = False) -> str:
        """Format mixed entity results for display."""
        import json
        from rich.console import Console
        from rich.table import Table
        from rich.text import Text
        from rich import box
        from io import StringIO
        
        string_buffer = StringIO()
        console = Console(file=string_buffer, force_terminal=True, width=150)
        
        # Standard header with query info FIRST
        self._display_header(console)
        
        # Context Display for Demo 10 - Denormalized Index Architecture
        if "Property Relationships" in self.query_name:
            console.print("\n[bold]📊 Denormalized Index Architecture:[/bold]")
            console.print("This demo shows property relationships using a denormalized index:")
            console.print()
            console.print("• Single query retrieves property, neighborhood, and Wikipedia data")
            console.print("• All related data pre-joined at index time for optimal performance")
            console.print("• Demonstrates production-ready pattern for read-heavy applications")
            console.print("• Trades storage space for dramatic query performance gains")
            console.print("=" * 60)
        
        # Display properties
        if self.property_results:
            console.print(f"\n🏠 TOP PROPERTIES:", style="bold magenta")
            
            table = Table(
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta",
                expand=False,
                padding=(0, 1)
            )
            
            table.add_column("#", style="dim", width=3, justify="center")
            table.add_column("Property", style="white", width=35)
            table.add_column("Location", style="blue", width=25)
            table.add_column("Price", style="green bold", justify="right", width=12)
            
            for idx, result in enumerate(self.property_results[:5], 1):
                property_text = f"{result.property_type} - {result.bedrooms}bd/{result.bathrooms}ba"
                
                location_parts = []
                if result.address.city:
                    location_parts.append(result.address.city)
                if result.address.state:
                    location_parts.append(result.address.state)
                location = ', '.join(location_parts) if location_parts else 'N/A'
                
                table.add_row(
                    str(idx),
                    property_text,
                    location,
                    f"${result.price:,.0f}"
                )
            
            console.print(table)
        
        if verbose:
            console.print(f"\n{'-'*40}", style="dim")
            console.print("Query DSL:", style="bold cyan")
            console.print(f"{'-'*40}", style="dim")
            console.print(json.dumps(self.query_dsl, indent=2), style="green")
        
        output = string_buffer.getvalue()
        string_buffer.close()
        return output

class LocationExtractionResult(BaseQueryResult):
    """Result for location understanding queries."""
    results: List[LocationIntent] = Field(..., description="Location extraction results")
    queries: List[str] = Field(..., description="Original queries that were processed")
    
    def display(self, verbose: bool = False) -> str:
        """Format location understanding results for display."""
        string_buffer = StringIO()
        console = Console(file=string_buffer, force_terminal=True, width=150)
        
        # Display header
        self._display_header(console)
        
        # Display location extraction results
        if self.results and len(self.results) > 0:
            console.print(f"\n🗺️  LOCATION EXTRACTION RESULTS:", style="bold magenta")
            
            table = Table(
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta",
                expand=False,
                padding=(0, 1)
            )
            
            # Add columns for location results
            table.add_column("#", style="dim", width=3, justify="center")
            table.add_column("Query", style="white", width=40)
            table.add_column("City", style="blue", width=20)
            table.add_column("State", style="green", width=15)
            table.add_column("Has Location", style="cyan", width=12, justify="center")
            table.add_column("Cleaned Query", style="yellow", width=30)
            
            # Add results
            for idx, (result, query) in enumerate(zip(self.results[:10], self.queries[:10]), 1):  # Show up to 10 location results
                city = result.city or 'N/A'
                state = result.state or 'N/A'
                has_location = "✅" if result.has_location else "❌"
                cleaned_query = result.cleaned_query or 'N/A'
                
                # Truncate long text
                if len(query) > 35:
                    query = query[:32] + "..."
                if len(cleaned_query) > 25:
                    cleaned_query = cleaned_query[:22] + "..."
                
                table.add_row(
                    str(idx),
                    query,
                    city,
                    state, 
                    has_location,
                    cleaned_query
                )
            
            console.print(table)
        
        if verbose:
            console.print(f"\n{'-'*40}", style="dim")
            console.print("Query DSL:", style="bold cyan")
            console.print(f"{'-'*40}", style="dim")
            console.print(json.dumps(self.query_dsl, indent=2), style="green")
        
        output = string_buffer.getvalue()
        string_buffer.close()
        return output
