#!/usr/bin/env python3
"""
Demo 16: Location Understanding Comparison

This demo uses the exact same queries as management demo 16 to compare
DSPy location extraction results between the management system and MCP server.
This helps identify any differences in DSPy configuration or behavior.
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


class LocationComparisonDemo(BaseMCPDemo):
    """Demo comparing location extraction between management system and MCP server."""
    
    def __init__(self):
        super().__init__(
            demo_name="Location Understanding Comparison",
            demo_number=16
        )
    
    def get_demo_queries(self) -> List[dict]:
        """Get queries that work with actual data and test location extraction properly."""
        return [
            {
                "name": "San Francisco Kitchen Query",
                "query": "Modern kitchen in San Francisco",
                "description": "Tests city extraction with features - should find City: San Francisco",
                "size": 5,
                "include_location": True,
                "expected_city": "San Francisco",
                "expected_state": None,
                "expected_has_location": True
            },
            {
                "name": "Salinas Family Home Query", 
                "query": "Family home in Salinas California",
                "description": "Tests city+state extraction - should find City: Salinas, State: California",
                "size": 5,
                "include_location": True,
                "expected_city": "Salinas",
                "expected_state": "California",
                "expected_has_location": True
            },
            {
                "name": "San Jose Condo Query",
                "query": "Condo in San Jose CA",
                "description": "Tests city+state abbreviation - should find City: San Jose, State: California",
                "size": 5,
                "include_location": True,
                "expected_city": "San Jose",
                "expected_state": "California",
                "expected_has_location": True
            },
            {
                "name": "Luxury Waterfront Query",
                "query": "Luxury waterfront condo in San Francisco",
                "description": "Tests luxury feature extraction with city - should find City: San Francisco",
                "size": 5,
                "include_location": True,
                "expected_city": "San Francisco",
                "expected_state": None,
                "expected_has_location": True
            },
            {
                "name": "Salinas Property Query",
                "query": "Property in Salinas", 
                "description": "Tests city-only extraction - should find City: Salinas",
                "size": 5,
                "include_location": True,
                "expected_city": "Salinas",
                "expected_state": None,
                "expected_has_location": True
            },
            {
                "name": "Park City Luxury Homes Query",
                "query": "Luxury homes in Park City Utah",
                "description": "Tests Utah location extraction and state abbreviation conversion",
                "size": 5,
                "include_location": True,
                "expected_city": "Park City",
                "expected_state": "Utah",
                "expected_has_location": True
            },
            {
                "name": "Park City Mountain Properties Query",
                "query": "Mountain view homes near Park City",
                "description": "Tests Park City search with feature-based query for mountain properties",
                "size": 5,
                "include_location": True,
                "expected_city": "Park City",
                "expected_state": None,
                "expected_has_location": True
            },
            {
                "name": "Affordable Mountain Homes in Park City",
                "query": "Affordable mountain homes in Park City area",
                "description": "Tests Park City location with affordable property features",
                "size": 5,
                "include_location": True,
                "expected_city": "Park City",
                "expected_state": None,
                "expected_has_location": True
            }
        ]
    
    def display_location_comparison_table(self, response, query_config, query_name: str) -> None:
        """Display location extraction comparison with expected results."""
        if not response.location_extracted:
            self.console.print("[dim]No location extraction data available[/dim]")
            return
            
        location_data = response.location_extracted
        
        # Create comparison table
        table = Table(
            title=f"Location Extraction Comparison - {query_name}",
            show_header=True,
            header_style="bold blue"
        )
        table.add_column("Field", style="yellow", min_width=15)
        table.add_column("MCP Result", style="cyan", min_width=15)
        table.add_column("Expected", style="green", min_width=15)
        table.add_column("Match", justify="center", style="magenta", min_width=8)
        
        # Compare has_location
        expected_has_location = query_config.get("expected_has_location", False)
        has_location_match = location_data.get("has_location") == expected_has_location
        table.add_row(
            "Has Location",
            "✅ Yes" if location_data.get("has_location") else "❌ No",
            "✅ Yes" if expected_has_location else "❌ No", 
            "✅" if has_location_match else "❌"
        )
        
        # Compare city
        expected_city = query_config.get("expected_city")
        city_match = location_data.get("city") == expected_city
        table.add_row(
            "City",
            location_data.get("city") or "None",
            expected_city or "None",
            "✅" if city_match else "❌"
        )
        
        # Compare state
        expected_state = query_config.get("expected_state")
        state_match = location_data.get("state") == expected_state
        table.add_row(
            "State", 
            location_data.get("state") or "None",
            expected_state or "None",
            "✅" if state_match else "❌"
        )
        
        # Show cleaned query
        table.add_row(
            "Cleaned Query",
            f'"{location_data.get("cleaned_query", "")}"',
            "N/A",
            "—"
        )
        
        self.console.print(table)
        
        # Overall comparison summary
        total_matches = sum([has_location_match, city_match, state_match])
        if total_matches == 3:
            self.console.print("[green]✅ Perfect match with expected results[/green]")
        elif total_matches >= 2:
            self.console.print("[yellow]⚠️ Mostly matches expected results[/yellow]")
        else:
            self.console.print("[red]❌ Significant differences from expected results[/red]")
    
    def display_property_results_summary(self, response, query_name: str) -> None:
        """Display property results in a detailed table format."""
        if not response.properties:
            self.console.print("[dim]No results found[/dim]")
            return
            
        self.console.print(f"\n[bold green]📊 {query_name} - Property Results:[/bold green]")
        
        # Create property results table
        table = Table(
            show_header=True,
            header_style="bold cyan",
            title=f"{query_name} - Top Properties"
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Type", style="cyan", min_width=10)
        table.add_column("Price", justify="right", style="green", min_width=12)
        table.add_column("Location", style="yellow", min_width=20)
        table.add_column("Description", style="white", min_width=35)
        table.add_column("Score", justify="center", style="red", min_width=6)
        
        for i, prop in enumerate(response.properties[:3], 1):  # Show top 3
            prop_type = prop.property_type or "Unknown"
            price_str = f"${prop.price:,}" if prop.price else "N/A"
            city = prop.address.city or ""
            state = prop.address.state or ""
            location = f"{city}, {state}" if city and state else city or state or "Unknown"
            score = prop.score or 0
            
            # Get description and truncate if too long
            description = prop.description or "No description available"
            if len(description) > 50:
                description = description[:47] + "..."
            
            table.add_row(
                str(i),
                prop_type.title(),
                price_str,
                location,
                description,
                f"{score:.3f}"
            )
        
        self.console.print(table)
    
    async def run_demo_queries(self) -> DemoExecutionResult:
        """Execute the location comparison demo queries."""
        self.display_demo_header("Compares DSPy location extraction with management demo 16 results")
        
        demo_queries = self.get_demo_queries()
        queries_successful = 0
        start_time = time.time()
        
        self.console.print(f"\n[bold yellow]🔍 Running {len(demo_queries)} location comparison queries...[/bold yellow]")
        self.console.print("[dim]These are the exact same queries used in management demo 16[/dim]")
        
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
                
                # Display location extraction comparison
                self.display_location_comparison_table(response, query_config, query_config['name'])
                
                # Display brief property results
                self.display_property_results_summary(response, query_config['name'])
                
                # Show metadata
                self.console.print(f"\n[dim]⏱️ Execution time: {response.execution_time_ms}ms | Results: {response.returned_results}/{response.total_results}[/dim]")
                
                self.console.print("[green]✅ Comparison query completed successfully[/green]")
                queries_successful += 1
                
            except Exception as e:
                self.console.print(f"[red]❌ Query failed: {e}[/red]")
        
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
    """Run the location comparison demo."""
    demo = LocationComparisonDemo()
    result = await demo.execute()
    return 0 if result.success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)