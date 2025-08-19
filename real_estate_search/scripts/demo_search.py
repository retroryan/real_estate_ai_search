#!/usr/bin/env python3
"""
Demo script to showcase various search capabilities of the Property Search System.
This script demonstrates different search types with clear, formatted output.
"""

import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box

from real_estate_search.config.settings import Settings
from real_estate_search.search.search_engine import PropertySearchEngine
from real_estate_search.search.models import SearchRequest, SearchFilters, GeoSearchParams, GeoPoint
from real_estate_search.search.enums import QueryType, GeoDistanceUnit
from real_estate_search.indexer.enums import PropertyType, PropertyStatus, SortOrder


console = Console()


class SearchDemo:
    """Demonstrate various search capabilities."""
    
    def __init__(self):
        """Initialize the demo."""
        self.settings = Settings.load()
        self.search_engine = PropertySearchEngine(self.settings)
        
    def print_section_header(self, title: str, description: str = ""):
        """Print a formatted section header."""
        console.print("\n" + "="*80)
        console.print(f"[bold cyan]{title}[/bold cyan]")
        if description:
            console.print(f"[dim]{description}[/dim]")
        console.print("="*80 + "\n")
    
    def print_query_info(self, query_type: str, params: Dict[str, Any]):
        """Print query parameters in a formatted way."""
        console.print("[bold]Query Type:[/bold]", query_type)
        console.print("[bold]Parameters:[/bold]")
        for key, value in params.items():
            if value is not None:
                console.print(f"  • {key}: {value}")
        console.print()
    
    def print_results(self, response, show_details: bool = True):
        """Print search results in a formatted table."""
        if response.total == 0:
            console.print("[yellow]No results found[/yellow]")
            return
        
        # Summary
        console.print(f"[green]Found {response.total} properties[/green] (showing {len(response.hits)})")
        console.print(f"Query took: {response.took_ms}ms\n")
        
        # Results table
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("ID", style="cyan", width=12)
        table.add_column("Address", style="white")
        table.add_column("City", style="white")
        table.add_column("Type", style="yellow")
        table.add_column("Price", justify="right", style="green")
        table.add_column("Beds", justify="center")
        table.add_column("Baths", justify="center")
        table.add_column("Sq Ft", justify="right")
        
        if any(hit.distance for hit in response.hits):
            table.add_column("Distance", justify="right", style="blue")
        
        if any(hit.score for hit in response.hits):
            table.add_column("Score", justify="right", style="dim")
        
        for hit in response.hits:
            prop = hit.property
            row = [
                prop.listing_id,
                prop.address.street[:30],
                prop.address.city,
                prop.property_type.value if hasattr(prop.property_type, 'value') else str(prop.property_type),
                f"${prop.price:,.0f}",
                str(prop.bedrooms),
                f"{prop.bathrooms:.1f}",
                f"{prop.square_feet:,}" if prop.square_feet else "N/A"
            ]
            
            if any(h.distance for h in response.hits):
                if hit.distance:
                    row.append(f"{hit.distance:.2f} km")
                else:
                    row.append("")
            
            if any(h.score for h in response.hits):
                if hit.score:
                    row.append(f"{hit.score:.2f}")
                else:
                    row.append("")
            
            table.add_row(*row)
        
        console.print(table)
        
        # Show highlights if available
        if show_details and any(hit.highlights for hit in response.hits):
            console.print("\n[bold]Search Highlights:[/bold]")
            for i, hit in enumerate(response.hits[:3]):
                if hit.highlights:
                    console.print(f"\n[cyan]{hit.property.listing_id}:[/cyan]")
                    for field, highlights in hit.highlights.items():
                        console.print(f"  • {field}: {' ... '.join(highlights)}")
    
    def print_aggregations(self, response):
        """Print aggregation results."""
        if not response.aggregations:
            return
        
        console.print("\n[bold]Aggregations:[/bold]\n")
        
        for agg_name, agg_data in response.aggregations.items():
            if hasattr(agg_data, 'type'):
                if agg_data.type == "terms":
                    console.print(f"[cyan]{agg_name}:[/cyan]")
                    for bucket in agg_data.buckets[:5]:
                        if hasattr(bucket, 'key') and hasattr(bucket, 'doc_count'):
                            console.print(f"  • {bucket.key}: {bucket.doc_count} properties")
                        elif isinstance(bucket, dict):
                            console.print(f"  • {bucket.get('key', 'N/A')}: {bucket.get('doc_count', 0)} properties")
                elif agg_data.type == "range":
                    console.print(f"[cyan]{agg_name}:[/cyan]")
                    for bucket in agg_data.buckets:
                        if hasattr(bucket, 'from_value'):
                            if bucket.from_value is not None and bucket.to_value is not None:
                                console.print(f"  • ${bucket.from_value/1000:.0f}k-${bucket.to_value/1000:.0f}k: {bucket.doc_count} properties")
                        elif isinstance(bucket, dict):
                            from_val = bucket.get('from')
                            to_val = bucket.get('to')
                            key = bucket.get('key', '')
                            count = bucket.get('doc_count', 0)
                            if from_val is not None and to_val is not None:
                                console.print(f"  • {key}: {count} properties")
                            elif to_val is not None:
                                console.print(f"  • Under ${to_val/1000:.0f}k: {count} properties")
                            elif from_val is not None:
                                console.print(f"  • Over ${from_val/1000:.0f}k: {count} properties")
                elif agg_data.type == "stats":
                    console.print(f"[cyan]{agg_name}:[/cyan]")
                    if hasattr(agg_data, 'avg'):
                        console.print(f"  • Average: ${agg_data.avg:,.0f}")
                        console.print(f"  • Min: ${agg_data.min:,.0f}")
                        console.print(f"  • Max: ${agg_data.max:,.0f}")
        console.print()
    
    def demo_text_search(self):
        """Demonstrate text search across multiple fields."""
        self.print_section_header(
            "TEXT SEARCH",
            "Search across all text fields (description, features, amenities, etc.)"
        )
        
        # Example 1: Search for mountain views
        self.print_query_info(
            "Full-text search",
            {"query": "mountain views", "size": 5}
        )
        
        request = SearchRequest(
            query_type=QueryType.TEXT,
            query_text="mountain views",
            size=5,
            include_highlights=True
        )
        
        response = self.search_engine.search(request)
        self.print_results(response)
    
    def demo_filter_search(self):
        """Demonstrate filtered search with multiple criteria."""
        self.print_section_header(
            "FILTERED SEARCH",
            "Search using specific property criteria (price, bedrooms, type, etc.)"
        )
        
        # Example: Find 3+ bedroom homes under $1M
        self.print_query_info(
            "Filter-based search",
            {
                "min_bedrooms": 3,
                "max_price": "$1,000,000",
                "property_types": ["single_family", "townhouse"],
                "cities": ["Park City"],
                "sort": "price ascending"
            }
        )
        
        filters = SearchFilters(
            min_bedrooms=3,
            max_price=1000000,
            property_types=[PropertyType.SINGLE_FAMILY, PropertyType.TOWNHOUSE],
            cities=["Park City"]
        )
        
        request = SearchRequest(
            query_type=QueryType.FILTER,
            filters=filters,
            size=5,
            sort_by=SortOrder.PRICE_ASC
        )
        
        response = self.search_engine.search(request)
        self.print_results(response)
    
    def demo_combined_search(self):
        """Demonstrate combining text search with filters."""
        self.print_section_header(
            "COMBINED TEXT + FILTER SEARCH",
            "Combine full-text search with property filters"
        )
        
        self.print_query_info(
            "Text search with filters",
            {
                "query": "modern kitchen",
                "min_price": "$500,000",
                "max_price": "$1,500,000",
                "min_bedrooms": 2,
                "property_status": "active"
            }
        )
        
        filters = SearchFilters(
            min_price=500000,
            max_price=1500000,
            min_bedrooms=2,
            property_status=PropertyStatus.ACTIVE
        )
        
        request = SearchRequest(
            query_type=QueryType.TEXT,
            query_text="modern kitchen",
            filters=filters,
            size=5,
            include_highlights=True
        )
        
        response = self.search_engine.search(request)
        self.print_results(response)
    
    def demo_geo_search(self):
        """Demonstrate geographic radius search."""
        self.print_section_header(
            "GEOGRAPHIC SEARCH",
            "Find properties within a radius of a location"
        )
        
        # Search near downtown Park City
        self.print_query_info(
            "Geo-radius search",
            {
                "center": "Park City, UT (40.6461, -111.4980)",
                "radius": "5 km",
                "max_price": "$2,000,000",
                "sort": "distance"
            }
        )
        
        filters = SearchFilters(max_price=2000000)
        
        response = self.search_engine.geo_search(
            center_lat=40.6461,
            center_lon=-111.4980,
            radius=5,
            unit="km",
            filters=filters,
            size=5
        )
        
        self.print_results(response)
    
    def demo_aggregation_search(self):
        """Demonstrate search with aggregations."""
        self.print_section_header(
            "AGGREGATION SEARCH",
            "Get statistical insights about the property market"
        )
        
        self.print_query_info(
            "Search with aggregations",
            {
                "query": "all properties",
                "aggregations": "price ranges, property types, cities, statistics"
            }
        )
        
        request = SearchRequest(
            query_type=QueryType.FILTER,
            filters=SearchFilters(),  # No filters - get all
            size=1,  # Minimal size for aggregation-only query
            include_aggregations=True
        )
        
        response = self.search_engine.search(request)
        
        console.print(f"[green]Total properties in index: {response.total}[/green]")
        self.print_aggregations(response)
    
    def demo_price_range_search(self):
        """Demonstrate searching different price ranges."""
        self.print_section_header(
            "PRICE RANGE ANALYSIS",
            "Compare properties across different price brackets"
        )
        
        price_ranges = [
            ("Budget", 0, 500000),
            ("Mid-range", 500000, 1000000),
            ("Luxury", 1000000, 2000000),
            ("Ultra-luxury", 2000000, 10000000)
        ]
        
        table = Table(
            title="Properties by Price Range",
            show_header=True,
            header_style="bold magenta",
            box=box.ROUNDED
        )
        table.add_column("Range", style="cyan")
        table.add_column("Price Bracket", style="white")
        table.add_column("Count", justify="center", style="green")
        table.add_column("Avg Beds", justify="center")
        table.add_column("Avg Baths", justify="center")
        table.add_column("Avg Sq Ft", justify="right")
        table.add_column("Cities", style="dim")
        
        for label, min_price, max_price in price_ranges:
            filters = SearchFilters(
                min_price=min_price,
                max_price=max_price
            )
            
            request = SearchRequest(
                query_type=QueryType.FILTER,
                filters=filters,
                size=100,  # Get more to calculate averages
                include_aggregations=False
            )
            
            response = self.search_engine.search(request)
            
            if response.total > 0:
                # Calculate averages
                total_beds = sum(hit.property.bedrooms for hit in response.hits)
                total_baths = sum(hit.property.bathrooms for hit in response.hits)
                total_sqft = sum(hit.property.square_feet for hit in response.hits if hit.property.square_feet)
                sqft_count = sum(1 for hit in response.hits if hit.property.square_feet)
                
                cities = set(hit.property.address.city for hit in response.hits)
                
                avg_beds = total_beds / len(response.hits) if response.hits else 0
                avg_baths = total_baths / len(response.hits) if response.hits else 0
                avg_sqft = total_sqft / sqft_count if sqft_count > 0 else 0
                
                table.add_row(
                    label,
                    f"${min_price/1000:.0f}k-${max_price/1000:.0f}k",
                    str(response.total),
                    f"{avg_beds:.1f}",
                    f"{avg_baths:.1f}",
                    f"{avg_sqft:,.0f}" if avg_sqft > 0 else "N/A",
                    ", ".join(list(cities)[:2])
                )
            else:
                table.add_row(
                    label,
                    f"${min_price/1000:.0f}k-${max_price/1000:.0f}k",
                    "0",
                    "-",
                    "-",
                    "-",
                    "-"
                )
        
        console.print(table)
    
    def demo_property_type_comparison(self):
        """Compare different property types."""
        self.print_section_header(
            "PROPERTY TYPE COMPARISON",
            "Analyze different property types in the market"
        )
        
        property_types = [
            PropertyType.SINGLE_FAMILY,
            PropertyType.CONDO,
            PropertyType.TOWNHOUSE,
            PropertyType.MULTI_FAMILY
        ]
        
        table = Table(
            title="Property Type Analysis",
            show_header=True,
            header_style="bold magenta",
            box=box.ROUNDED
        )
        table.add_column("Type", style="cyan")
        table.add_column("Count", justify="center", style="green")
        table.add_column("Avg Price", justify="right", style="yellow")
        table.add_column("Price Range", justify="center")
        table.add_column("Avg Size", justify="right")
        table.add_column("Top City", style="dim")
        
        for prop_type in property_types:
            filters = SearchFilters(
                property_types=[prop_type]
            )
            
            request = SearchRequest(
                query_type=QueryType.FILTER,
                filters=filters,
                size=100,
                include_aggregations=False
            )
            
            response = self.search_engine.search(request)
            
            if response.total > 0:
                prices = [hit.property.price for hit in response.hits]
                avg_price = sum(prices) / len(prices)
                min_price = min(prices)
                max_price = max(prices)
                
                sizes = [hit.property.square_feet for hit in response.hits if hit.property.square_feet]
                avg_size = sum(sizes) / len(sizes) if sizes else 0
                
                # Find most common city
                city_counts = {}
                for hit in response.hits:
                    city = hit.property.address.city
                    city_counts[city] = city_counts.get(city, 0) + 1
                top_city = max(city_counts, key=city_counts.get) if city_counts else "N/A"
                
                table.add_row(
                    prop_type.value,
                    str(response.total),
                    f"${avg_price:,.0f}",
                    f"${min_price/1000:.0f}k-${max_price/1000:.0f}k",
                    f"{avg_size:,.0f} sq ft" if avg_size > 0 else "N/A",
                    top_city
                )
            else:
                table.add_row(
                    prop_type.value,
                    "0",
                    "-",
                    "-",
                    "-",
                    "-"
                )
        
        console.print(table)
    
    def demo_similar_properties(self):
        """Find properties similar to a given property."""
        self.print_section_header(
            "SIMILAR PROPERTIES SEARCH",
            "Find properties similar to a reference property"
        )
        
        # First, find a luxury property to use as reference
        console.print("[dim]Finding a reference property...[/dim]\n")
        
        filters = SearchFilters(
            min_price=1000000,
            property_types=[PropertyType.SINGLE_FAMILY]
        )
        
        request = SearchRequest(
            query_type=QueryType.FILTER,
            filters=filters,
            size=1
        )
        
        response = self.search_engine.search(request)
        
        if response.hits:
            reference = response.hits[0]
            console.print(f"[bold]Reference Property:[/bold]")
            console.print(f"  • ID: {reference.property.listing_id}")
            console.print(f"  • Address: {reference.property.address.street}, {reference.property.address.city}")
            console.print(f"  • Price: ${reference.property.price:,.0f}")
            console.print(f"  • Type: {reference.property.property_type.value if hasattr(reference.property.property_type, 'value') else reference.property.property_type}")
            console.print(f"  • Bedrooms: {reference.property.bedrooms}")
            console.print(f"  • Bathrooms: {reference.property.bathrooms}")
            console.print()
            
            # Find similar properties
            self.print_query_info(
                "More Like This search",
                {
                    "reference_property": reference.property.listing_id,
                    "max_results": 5
                }
            )
            
            similar_request = SearchRequest(
                query_type=QueryType.SIMILAR,
                similar_to_id=reference.doc_id,
                size=5
            )
            
            similar_response = self.search_engine.search(similar_request)
            
            if similar_response.total > 0:
                console.print(f"[green]Found {similar_response.total} similar properties:[/green]\n")
                self.print_results(similar_response, show_details=False)
            else:
                console.print("[yellow]No similar properties found[/yellow]")
        else:
            console.print("[yellow]No reference property found[/yellow]")
    
    def run_all_demos(self):
        """Run all demonstration searches."""
        try:
            # Header
            console.print("\n" + "="*80)
            console.print("[bold green]PROPERTY SEARCH SYSTEM DEMONSTRATION[/bold green]", justify="center")
            console.print(f"[dim]Connected to: {self.settings.elasticsearch.host}:{self.settings.elasticsearch.port}[/dim]", justify="center")
            console.print("="*80)
            
            # Check index has data
            test_request = SearchRequest(
                query_type=QueryType.FILTER,
                filters=SearchFilters(),
                size=1
            )
            test_response = self.search_engine.search(test_request)
            
            if test_response.total == 0:
                console.print("\n[red]❌ No data in index! Please run:[/red]")
                console.print("[yellow]python scripts/setup_index.py --data-dir ../real_estate_data[/yellow]\n")
                return
            
            console.print(f"\n[green]✅ Index contains {test_response.total} properties[/green]")
            console.print("[dim]Starting demonstrations...[/dim]")
            
            # Run each demo
            demos = [
                ("Text Search", self.demo_text_search),
                ("Filtered Search", self.demo_filter_search),
                ("Combined Search", self.demo_combined_search),
                ("Geographic Search", self.demo_geo_search),
                ("Aggregation Analysis", self.demo_aggregation_search),
                ("Price Range Analysis", self.demo_price_range_search),
                ("Property Type Comparison", self.demo_property_type_comparison),
                ("Similar Properties", self.demo_similar_properties)
            ]
            
            for i, (name, demo_func) in enumerate(demos, 1):
                try:
                    time.sleep(0.5)  # Brief pause between demos
                    demo_func()
                except Exception as e:
                    console.print(f"\n[red]❌ Error in {name}: {e}[/red]")
            
            # Footer
            self.print_section_header(
                "DEMONSTRATION COMPLETE",
                f"Demonstrated {len(demos)} different search capabilities"
            )
            
            console.print("[green]✅ All demonstrations completed successfully![/green]")
            console.print("\n[dim]To run individual demos, you can call specific methods:[/dim]")
            console.print("[dim]  • demo.demo_text_search()[/dim]")
            console.print("[dim]  • demo.demo_filter_search()[/dim]")
            console.print("[dim]  • demo.demo_geo_search()[/dim]")
            console.print("[dim]  • etc.[/dim]\n")
            
        except Exception as e:
            console.print(f"\n[red]❌ Demo failed: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        finally:
            # Clean up
            self.search_engine.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Demonstrate Property Search System capabilities",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--demo",
        choices=["all", "text", "filter", "combined", "geo", "aggregation", "price", "type", "similar"],
        default="all",
        help="Which demo to run"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start interactive mode after demos"
    )
    
    args = parser.parse_args()
    
    # Create demo instance
    demo = SearchDemo()
    
    # Run requested demo
    if args.demo == "all":
        demo.run_all_demos()
    elif args.demo == "text":
        demo.demo_text_search()
    elif args.demo == "filter":
        demo.demo_filter_search()
    elif args.demo == "combined":
        demo.demo_combined_search()
    elif args.demo == "geo":
        demo.demo_geo_search()
    elif args.demo == "aggregation":
        demo.demo_aggregation_search()
    elif args.demo == "price":
        demo.demo_price_range_search()
    elif args.demo == "type":
        demo.demo_property_type_comparison()
    elif args.demo == "similar":
        demo.demo_similar_properties()
    
    # Interactive mode
    if args.interactive:
        console.print("\n[bold cyan]Entering interactive mode...[/bold cyan]")
        console.print("[dim]Type 'help' for commands, 'quit' to exit[/dim]\n")
        
        while True:
            try:
                command = input("search> ").strip().lower()
                
                if command == "quit" or command == "exit":
                    break
                elif command == "help":
                    console.print("\nAvailable commands:")
                    console.print("  text <query>     - Text search")
                    console.print("  filter           - Filter search (interactive)")
                    console.print("  geo <lat> <lon>  - Geographic search")
                    console.print("  stats            - Show statistics")
                    console.print("  quit             - Exit")
                    console.print()
                elif command.startswith("text "):
                    query = command[5:].strip()
                    request = SearchRequest(
                        query_type=QueryType.TEXT,
                        query_text=query,
                        size=5,
                        include_highlights=True
                    )
                    response = demo.search_engine.search(request)
                    demo.print_results(response)
                elif command == "stats":
                    demo.demo_aggregation_search()
                else:
                    console.print("[yellow]Unknown command. Type 'help' for available commands.[/yellow]")
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'quit' to exit[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
    
    console.print("\n[dim]Demo session ended.[/dim]")


if __name__ == "__main__":
    main()