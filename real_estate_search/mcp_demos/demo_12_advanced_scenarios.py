#!/usr/bin/env python3
"""
Demo 12: Complex Search Scenarios

This demo tests complex query handling capabilities of the hybrid search
using clean Pydantic models and FastMCP client patterns.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from pydantic import ValidationError

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from real_estate_search.mcp_demos.base_demo import BaseMCPDemo, ProgressTrackingMixin
from real_estate_search.mcp_demos.models.hybrid_search import (
    HybridSearchRequest,
    DemoExecutionResult,
    ValidationTestCase
)


class AdvancedScenariosDemo(BaseMCPDemo, ProgressTrackingMixin):
    """Demo showcasing complex search scenarios."""
    
    def __init__(self):
        super().__init__(
            demo_name="Complex Search Scenarios",
            demo_number=12
        )
    
    def get_validation_test_cases(self) -> List[ValidationTestCase]:
        """Get parameter validation test cases."""
        return [
            ValidationTestCase(
                name="Empty Query",
                params={"query": "", "size": 5},
                should_fail=True,
                expected_error="ValidationError",
                description="Tests empty query validation"
            ),
            ValidationTestCase(
                name="Maximum Size Boundary",
                params={"query": "test property", "size": 50},
                should_fail=False,
                expected_error=None,
                description="Tests maximum allowed size parameter"
            ),
            ValidationTestCase(
                name="Size Too Large",
                params={"query": "test property", "size": 100},
                should_fail=True,
                expected_error="ValidationError",
                description="Tests size parameter upper bound validation"
            ),
            ValidationTestCase(
                name="Size Zero",
                params={"query": "test property", "size": 0},
                should_fail=True,
                expected_error="ValidationError",
                description="Tests size parameter lower bound validation"
            ),
            ValidationTestCase(
                name="Very Long Query",
                params={"query": "luxury home " * 100, "size": 5},
                should_fail=True,
                expected_error="ValidationError",
                description="Tests query length validation (500+ chars)"
            ),
            ValidationTestCase(
                name="Minimum Valid Query",
                params={"query": "a", "size": 1},
                should_fail=False,
                expected_error=None,
                description="Tests minimum valid parameters"
            )
        ]
    
    def get_complex_queries(self) -> List[dict]:
        """Get complex query test scenarios."""
        return [
            {
                "name": "SF Bay Area Family Search",
                "query": "Family home near good schools in San Jose California",
                "description": "Tests complex family-oriented search with location",
                "size": 8
            },
            {
                "name": "Modern Kitchen Features",
                "query": "modern kitchen with stainless steel appliances",
                "description": "Tests feature-specific hybrid search",
                "size": 8
            },
            {
                "name": "Oakland Affordable Housing",
                "query": "Affordable house in Oakland California",
                "description": "Tests Oakland location with affordability criteria",
                "size": 8
            }
        ]
    
    def display_complex_query_summary(self, query_name: str, query_text: str, response, execution_time: float) -> None:
        """Display detailed summary for a complex query result."""
        # Get metadata directly from response
        
        self.console.print(f"\n[green]📊 {query_name} Summary:[/green]")
        self.console.print(f"   [dim]🔍 Query:[/dim] \"{query_text}\"")
        self.console.print(f"   [dim]⏱️ Total time:[/dim] {execution_time:.1f}ms (Server: {response.execution_time_ms}ms)")
        self.console.print(f"   [dim]📈 Results:[/dim] {response.returned_results} of {response.total_results} total")
        
        # Show location extraction if present
        if response.location_extracted and response.location_extracted.get('has_location'):
            city = response.location_extracted.get('city') or "N/A"
            state = response.location_extracted.get('state') or "N/A"
            cleaned_query = response.location_extracted.get('cleaned_query', '')
            cleaned = cleaned_query[:60]
            if len(cleaned_query) > 60:
                cleaned += "..."
            self.console.print(f"   [dim]📍 Location:[/dim] {city}, {state}")
            self.console.print(f"   [dim]🧹 Cleaned:[/dim] \"{cleaned}\"")
        
        # Show detailed property results
        if response.properties:
            self.console.print(f"\n   [bold magenta]🏆 Property Details:[/bold magenta]")
            for j, prop in enumerate(response.properties, 1):
                score = prop.score or 0
                prop_type = prop.property_type or "Unknown"
                price_str = f"${prop.price:,}" if prop.price else "N/A"
                
                # Address details
                city = prop.address.city or "N/A"
                state = prop.address.state or "N/A"
                street = prop.address.street or "Address not available"
                if len(street) > 30:
                    street = street[:27] + "..."
                
                # Property specs
                beds = f"{prop.bedrooms}" if prop.bedrooms else "N/A"
                baths = f"{prop.bathrooms}" if prop.bathrooms else "N/A"
                sqft = f"{prop.square_feet:,}" if prop.square_feet else "N/A"
                
                self.console.print(f"     [cyan]{j}. {prop_type.title()}[/cyan] - [green]{price_str}[/green] (Score: [yellow]{score:.3f}[/yellow])")
                self.console.print(f"        📍 {street}, {city}, {state}")
                self.console.print(f"        🏠 {beds} bed, {baths} bath, {sqft} sqft")
                
                # Show features if available
                if prop.features:
                    features_str = ", ".join(prop.features[:3])  # Show first 3 features
                    if len(prop.features) > 3:
                        features_str += f" (+{len(prop.features) - 3} more)"
                    self.console.print(f"        ✨ {features_str}")
                
                if j < len(response.properties):
                    self.console.print("")  # Add spacing between properties
    async def run_demo_queries(self) -> DemoExecutionResult:
        """Execute the advanced scenarios demo."""
        self.display_demo_header("Tests complex query scenarios")
        
        start_time = time.time()
        total_queries = 0
        successful_queries = 0
        
        # Complex Query Tests
        self.console.print(f"\n{Panel.fit('[bold yellow]🔍 Testing Complex Query Scenarios[/bold yellow]', border_style='yellow')}")
        
        complex_queries = self.get_complex_queries()
        
        with self.create_progress_tracker(len(complex_queries)) as progress:
            for i, query_config in enumerate(complex_queries, 1):
                task = progress.add_task(f"Processing complex query {i}/{len(complex_queries)}...", total=1)
                
                self.console.print(f"\n[bold blue]--- Query {i}: {query_config['name']} ---[/bold blue]")
                self.console.print(f"[dim]Purpose:[/dim] {query_config['description']}")
                
                total_queries += 1
                query_start = time.time()
                
                try:
                    request = HybridSearchRequest(
                        query=query_config["query"],
                        size=query_config["size"],
                        include_location_extraction=True
                    )
                    
                    response = await self.execute_hybrid_search(request)
                    query_time = (time.time() - query_start) * 1000
                    
                    self.display_complex_query_summary(query_config['name'], query_config['query'], response, query_time)
                    self.console.print("[green]✅ Complex query processed successfully[/green]")
                    successful_queries += 1
                    
                except Exception as e:
                    self.console.print(f"[red]❌ Query failed: {e}[/red]")
                
                progress.update(task, advance=1)
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        
        return DemoExecutionResult(
            demo_name=self.demo_name,
            demo_number=self.demo_number,
            success=successful_queries == total_queries,
            queries_executed=total_queries,
            queries_successful=successful_queries,
            total_execution_time_ms=total_time,
            error_message=None if successful_queries == total_queries else f"Failed {total_queries - successful_queries} queries"
        )


async def main():
    """Run the advanced scenarios demo."""
    demo = AdvancedScenariosDemo()
    result = await demo.execute()
    return 0 if result.success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)