#!/usr/bin/env python3
"""
Demo 19: Advanced Search Scenarios and Edge Cases

This demo tests the robustness and advanced capabilities of the hybrid search
using clean Pydantic models and FastMCP client patterns. Includes parameter 
validation, edge cases, error handling, and performance analysis.
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
    ValidationTestCase,
    EdgeCaseTest
)


class AdvancedScenariosDemo(BaseMCPDemo, ProgressTrackingMixin):
    """Demo showcasing advanced scenarios, validation, and edge cases."""
    
    def __init__(self):
        super().__init__(
            demo_name="Advanced Search Scenarios and Edge Cases",
            demo_number=19
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
    
    def get_edge_test_cases(self) -> List[EdgeCaseTest]:
        """Get edge case test scenarios."""
        return [
            EdgeCaseTest(
                name="Modern Oakland Apartment",
                query="Modern apartment in Oakland",
                description="Tests Oakland location extraction",
                expected_behavior="Should extract Oakland location correctly"
            ),
            EdgeCaseTest(
                name="Investment Property Generic",
                query="investment property with rental income",
                description="Tests non-location query handling",
                expected_behavior="Should handle queries without location"
            ),
            EdgeCaseTest(
                name="Luxury Features Only",
                query="luxury waterfront condo with amazing views",
                description="Tests feature-only queries without location",
                expected_behavior="Should return results without location filtering"
            ),
            EdgeCaseTest(
                name="Minimal Query",
                query="home",
                description="Tests very minimal search terms",
                expected_behavior="Should return broad results for minimal queries"
            ),
            EdgeCaseTest(
                name="Bay Area Reference",
                query="properties in the Bay Area California",
                description="Tests regional location reference",
                expected_behavior="Should handle vague regional terms"
            ),
        ]
    
    def display_validation_results(self, test_cases: List[ValidationTestCase], results: List[Dict]) -> None:
        """Display parameter validation test results."""
        table = Table(
            title="Parameter Validation Tests",
            show_header=True,
            header_style="bold magenta"
        )
        table.add_column("Test", style="cyan", min_width=20)
        table.add_column("Expected", justify="center", style="yellow", min_width=10)
        table.add_column("Actual", justify="center", style="green", min_width=15)
        table.add_column("Status", justify="center", style="blue", min_width=8)
        
        for test_case, result in zip(test_cases, results):
            expected = "FAIL" if test_case.should_fail else "PASS"
            
            if result["error"]:
                actual = f"FAIL ({result['error_type']})"
                status = "✅" if test_case.should_fail else "❌"
            else:
                hits = result.get("hits", 0)
                actual = f"PASS ({hits})"
                status = "❌" if test_case.should_fail else "✅"
            
            table.add_row(test_case.name, expected, actual, status)
        
        self.console.print(table)
    
    def display_complex_query_summary(self, query_name: str, query_text: str, response, execution_time: float) -> None:
        """Display detailed summary for a complex query result."""
        metadata = response.metadata
        
        self.console.print(f"\n[green]📊 {query_name} Summary:[/green]")
        self.console.print(f"   [dim]🔍 Query:[/dim] \"{query_text}\"")
        self.console.print(f"   [dim]⏱️ Total time:[/dim] {execution_time:.1f}ms (Server: {metadata.execution_time_ms}ms)")
        self.console.print(f"   [dim]📈 Results:[/dim] {metadata.returned_hits} of {metadata.total_hits} total")
        
        # Show location extraction if present
        if metadata.location_extracted and metadata.location_extracted.has_location:
            city = metadata.location_extracted.city or "N/A"
            state = metadata.location_extracted.state or "N/A"
            cleaned = metadata.location_extracted.cleaned_query[:60]
            if len(metadata.location_extracted.cleaned_query) > 60:
                cleaned += "..."
            self.console.print(f"   [dim]📍 Location:[/dim] {city}, {state}")
            self.console.print(f"   [dim]🧹 Cleaned:[/dim] \"{cleaned}\"")
        
        # Show detailed property results
        if response.results:
            self.console.print(f"\n   [bold magenta]🏆 Property Details:[/bold magenta]")
            for j, prop in enumerate(response.results, 1):
                score = prop.hybrid_score or 0
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
                
                if j < len(response.results):
                    self.console.print("")  # Add spacing between properties
    def display_edge_case_results(self, edge_cases: List[EdgeCaseTest], results: List[Dict]) -> None:
        """Display edge case test results."""
        table = Table(
            title="Edge Case Test Results",
            show_header=True,
            header_style="bold magenta"
        )
        table.add_column("Test Case", style="cyan", min_width=18)
        table.add_column("Status", justify="center", style="green", min_width=8)
        table.add_column("Results", justify="center", style="blue", min_width=8)
        table.add_column("Time (ms)", justify="center", style="yellow", min_width=10)
        table.add_column("Location", justify="center", style="magenta", min_width=10)
        
        for edge_case, result in zip(edge_cases, results):
            if result["error"]:
                table.add_row(edge_case.name, "❌", "ERROR", "N/A", "❌")
            else:
                response_data = result["response"]
                metadata = response_data.metadata
                has_location = (metadata.location_extracted and 
                              metadata.location_extracted.has_location) if metadata.location_extracted else False
                
                table.add_row(
                    edge_case.name,
                    "✅",
                    str(metadata.returned_hits),
                    f"{metadata.execution_time_ms}",
                    "✅" if has_location else "❌"
                )
        
        self.console.print(table)
    
    async def run_demo_queries(self) -> DemoExecutionResult:
        """Execute the advanced scenarios demo."""
        self.display_demo_header("Tests robustness, validation, and advanced query handling")
        
        start_time = time.time()
        total_queries = 0
        successful_queries = 0
        
        # 1. Parameter Validation Tests
        self.console.print(Panel.fit(
            "[bold yellow]🧪 Testing Parameter Validation & Edge Cases[/bold yellow]",
            border_style="yellow"
        ))
        
        validation_cases = self.get_validation_test_cases()
        validation_results = []
        
        for test_case in validation_cases:
            total_queries += 1
            try:
                # Try to create request - this will validate parameters
                if test_case.should_fail:
                    try:
                        request = HybridSearchRequest(**test_case.params)
                        # If no validation error, try the actual request
                        response = await self.execute_hybrid_search(request)
                        validation_results.append({"error": None, "hits": len(response.results), "error_type": None})
                    except ValidationError as e:
                        validation_results.append({"error": str(e), "error_type": "ValidationError"})
                        successful_queries += 1  # Expected validation failure
                else:
                    request = HybridSearchRequest(**test_case.params)
                    response = await self.execute_hybrid_search(request)
                    validation_results.append({"error": None, "hits": len(response.results), "error_type": None})
                    successful_queries += 1
                    
            except Exception as e:
                error_type = type(e).__name__
                validation_results.append({"error": str(e), "error_type": error_type})
                if test_case.should_fail:
                    successful_queries += 1  # Expected failure
        
        self.display_validation_results(validation_cases, validation_results)
        
        # 2. Complex Query Tests
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
        
        # 3. Edge Case Tests
        self.console.print(f"\n{Panel.fit('[bold yellow]🎯 Testing Edge Cases & Unusual Scenarios[/bold yellow]', border_style='yellow')}")
        
        edge_cases = self.get_edge_test_cases()
        edge_results = []
        
        for edge_case in edge_cases:
            total_queries += 1
            try:
                request = HybridSearchRequest(
                    query=edge_case.query,
                    size=5,
                    include_location_extraction=True
                )
                
                response = await self.execute_hybrid_search(request)
                edge_results.append({"error": None, "response": response})
                successful_queries += 1
                
            except Exception as e:
                edge_results.append({"error": str(e), "response": None})
        
        self.display_edge_case_results(edge_cases, edge_results)
        
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