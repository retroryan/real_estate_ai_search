#!/usr/bin/env python3
"""
Demo 11: Location-Aware Hybrid Search

This demo showcases location extraction and understanding capabilities using DSPy
and clean Pydantic models. Demonstrates how the system automatically extracts
geographic context from natural language queries and applies location filtering.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import List
from rich.table import Table
from rich.panel import Panel

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from real_estate_search.mcp_demos.base_demo import BaseMCPDemo
from real_estate_search.mcp_demos.models.hybrid_search import (
    HybridSearchRequest,
    DemoExecutionResult
)


class LocationAwareSearchDemo(BaseMCPDemo):
    """Demo showcasing location extraction and geographic understanding."""
    
    def __init__(self):
        super().__init__(
            demo_name="Location-Aware Hybrid Search",
            demo_number=11
        )
    
    def get_demo_queries(self) -> List[dict]:
        """Get location-focused demo query configurations."""
        return [
            {
                "name": "San Jose Properties",
                "query": "Condo with amenities in San Jose",
                "description": "Tests San Jose location extraction with high result count",
                "size": 8,
                "include_location": True
            },
            {
                "name": "Oakland Townhouses", 
                "query": "Townhouse in Oakland under 800k",
                "description": "Tests Oakland location with price filtering",
                "size": 8,
                "include_location": True
            },
            {
                "name": "San Francisco Luxury",
                "query": "Luxury waterfront condo in San Francisco",
                "description": "Tests San Francisco luxury property search",
                "size": 8,
                "include_location": True
            },
            {
                "name": "Bay Area Family Homes",
                "query": "Single family home in San Francisco Bay Area",
                "description": "Tests regional Bay Area location extraction",
                "size": 8,
                "include_location": True
            }
        ]
    
    def display_location_extraction_details(self, response, query_name: str) -> None:
        """Display detailed location extraction information."""
        if not response.location_extracted:
            self.console.print("[dim]No location extraction data available[/dim]")
            return
            
        location_data = response.location_extracted
        
        # Create location details panel
        details = []
        details.append(f"[bold]Has Location:[/bold] {'✅ Yes' if location_data.get('has_location') else '❌ No'}")
        
        if location_data.get('city'):
            details.append(f"[bold]Extracted City:[/bold] {location_data.get('city')}")
        if location_data.get('state'):
            details.append(f"[bold]Extracted State:[/bold] {location_data.get('state')}")
        if location_data.get('cleaned_query'):
            details.append(f"[bold]Cleaned Query:[/bold] \"{location_data.get('cleaned_query')}\"")
        
        self.console.print(Panel(
            "\n".join(details),
            title=f"🗺️ Location Extraction - {query_name}",
            border_style="blue"
        ))
    
    def display_geographic_results_table(self, response, query_name: str) -> None:
        """Display search results with geographic context."""
        if not response.properties:
            self.console.print("[dim]No results found[/dim]")
            return
            
        # Create results table with location emphasis
        table = Table(
            title=f"{query_name} - Geographic Results",
            show_header=True,
            header_style="bold blue"
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Type", style="cyan", min_width=8)
        table.add_column("Price", justify="right", style="green", min_width=10)
        table.add_column("Location", style="yellow", min_width=20)
        table.add_column("Address", style="white", min_width=25)
        table.add_column("Score", justify="center", style="red", min_width=6)
        
        for i, prop in enumerate(response.properties, 1):
            # Format property data with location emphasis
            property_type = prop.property_type or "Unknown"
            price_str = f"${prop.price:,.0f}" if prop.price else "N/A"
            
            # Emphasize location information
            city = prop.address.city or ""
            state = prop.address.state or ""
            location = f"{city}, {state}" if city and state else city or state or "Unknown"
            
            address = prop.address.street or "Address not available"
            if len(address) > 25:
                address = address[:22] + "..."
            
            score_str = f"{prop.score:.3f}" if prop.score else "N/A"
            
            table.add_row(str(i), property_type, price_str, location, address, score_str)
        
        self.console.print(table)
    
    def display_location_insights(self, responses: List, query_configs: List[dict]) -> None:
        """Display insights about location extraction across all queries."""
        insights = []
        
        location_found_count = 0
        cities_extracted = set()
        states_extracted = set()
        
        for response, config in zip(responses, query_configs):
            if response.location_extracted and response.location_extracted.get('has_location'):
                location_found_count += 1
                if response.location_extracted.get('city'):
                    cities_extracted.add(response.location_extracted.get('city'))
                if response.location_extracted.get('state'):
                    states_extracted.add(response.location_extracted.get('state'))
        
        insights.append(f"[bold]Location Detection Rate:[/bold] {location_found_count}/{len(responses)} queries")
        
        if cities_extracted:
            insights.append(f"[bold]Cities Detected:[/bold] {', '.join(sorted(cities_extracted))}")
        if states_extracted:
            insights.append(f"[bold]States Detected:[/bold] {', '.join(sorted(states_extracted))}")
        
        # Calculate average results per location query
        avg_results = sum(len(r.properties) for r in responses) / len(responses) if responses else 0
        insights.append(f"[bold]Average Results per Query:[/bold] {avg_results:.1f}")
        
        self.console.print(Panel(
            "\n".join(insights),
            title="🎯 Location Extraction Insights",
            border_style="green"
        ))
    
    async def run_demo_queries(self) -> DemoExecutionResult:
        """Execute the location-aware hybrid search demo queries."""
        self.display_demo_header("Showcases location extraction and geographic filtering via DSPy")
        
        demo_queries = self.get_demo_queries()
        queries_successful = 0
        start_time = time.time()
        responses = []
        
        self.console.print(f"\n[bold yellow]🗺️ Running {len(demo_queries)} location-aware search queries...[/bold yellow]")
        
        for i, query_config in enumerate(demo_queries, 1):
            self.console.print(f"\n[bold blue]--- Query {i}: {query_config['name']} ---[/bold blue]")
            self.console.print(f"[dim]Query:[/dim] \"{query_config['query']}\"")
            self.console.print(f"[dim]Purpose:[/dim] {query_config['description']}")
            
            try:
                # Create validated request with location extraction enabled
                request = HybridSearchRequest(
                    query=query_config["query"],
                    size=query_config["size"],
                    include_location_extraction=query_config["include_location"]
                )
                
                # Execute hybrid search
                response = await self.execute_hybrid_search(request)
                responses.append(response)
                
                # Display location extraction details first
                self.display_location_extraction_details(response, query_config['name'])
                
                # Display results with geographic emphasis
                # Get metadata directly from response
                self.console.print(f"\n[green]📊 Results ({response.returned_results} of {response.total_results} total):[/green]")
                self.console.print(f"[dim]⏱️ Execution time: {response.execution_time_ms}ms[/dim]")
                
                self.display_geographic_results_table(response, query_config['name'])
                
                self.console.print("[green]✅ Location-aware query completed successfully[/green]")
                queries_successful += 1
                
            except Exception as e:
                self.console.print(f"[red]❌ Query failed: {e}[/red]")
        
        # Show location extraction insights
        if responses:
            self.console.print()
            self.display_location_insights(responses, demo_queries)
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        
        # Create demo result
        return DemoExecutionResult(
            demo_name=self.demo_name,
            demo_number=self.demo_number,
            success=queries_successful == len(demo_queries),
            queries_executed=len(demo_queries),
            queries_successful=queries_successful,
            total_execution_time_ms=total_time,
            error_message=None if queries_successful == len(demo_queries) else f"Failed {len(demo_queries) - queries_successful} queries"
        )


async def main():
    """Run the location-aware hybrid search demo."""
    demo = LocationAwareSearchDemo()
    result = await demo.execute()
    return 0 if result.success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)