#!/usr/bin/env python3
"""
Query Validation Script

Tests various real estate queries against the DSPy location extraction module
to identify which queries work well and which don't. This helps us choose
good demo queries that showcase the system capabilities.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from real_estate_search.mcp_demos.base_demo import BaseMCPDemo
from real_estate_search.mcp_demos.models.hybrid_search import HybridSearchRequest, DemoExecutionResult


class QueryValidator(BaseMCPDemo):
    """Validates queries for DSPy location extraction and hybrid search."""
    
    def __init__(self):
        super().__init__(
            demo_name="Query Validation Test",
            demo_number=16  # Use 16 since it's our comparison demo number
        )
    
    def get_test_queries(self) -> List[Dict[str, Any]]:
        """Get various queries to test location extraction."""
        return [
            # Known working queries (from management demo 16)
            {"query": "Find a great family home in San Francisco", "category": "Known Working"},
            {"query": "Luxury condo in Oakland California", "category": "Known Working"},
            {"query": "Affordable homes in Salinas CA", "category": "Known Working"},
            {"query": "Properties near downtown San Jose", "category": "Known Failing"},
            
            # Park City queries
            {"query": "Ski chalet in Park City Utah", "category": "Park City"},
            {"query": "Mountain home with views in Park City", "category": "Park City"},
            {"query": "Luxury resort property Park City UT", "category": "Park City"},
            {"query": "Vacation rental near Park City ski slopes", "category": "Park City"},
            
            # California cities (should work)
            {"query": "Beachfront condo in Santa Monica California", "category": "California Cities"},
            {"query": "Wine country estate in Napa CA", "category": "California Cities"},
            {"query": "Tech worker housing in Palo Alto", "category": "California Cities"},
            {"query": "Historic home in Sacramento California", "category": "California Cities"},
            
            # Generic location patterns
            {"query": "Modern home in Denver Colorado", "category": "Other States"},
            {"query": "Apartment building in Seattle WA", "category": "Other States"},
            {"query": "Townhouse in Phoenix Arizona", "category": "Other States"},
            {"query": "Lakefront property in Austin Texas", "category": "Other States"},
            
            # Potentially problematic queries
            {"query": "luxury waterfront condo with amazing views", "category": "No Location"},
            {"query": "house near downtown with good schools", "category": "No Location"},
            {"query": "investment property with rental income", "category": "No Location"},
            {"query": "properties in the Bay Area California", "category": "Vague Location"},
            {"query": "homes near Silicon Valley", "category": "Vague Location"},
        ]
    
    async def validate_query(self, query: str) -> Dict[str, Any]:
        """Validate a single query and return results."""
        try:
            request = HybridSearchRequest(
                query=query,
                size=3,  # Small size for testing
                include_location_extraction=True
            )
            
            start_time = time.time()
            response = await self.execute_hybrid_search(request)
            execution_time = (time.time() - start_time) * 1000
            
            # Extract location extraction results
            location_data = response.metadata.location_extracted
            if location_data:
                return {
                    "query": query,
                    "success": True,
                    "has_location": location_data.has_location,
                    "city": location_data.city,
                    "state": location_data.state,
                    "cleaned_query": location_data.cleaned_query,
                    "results_count": len(response.results),
                    "total_hits": response.metadata.total_hits,
                    "execution_time": execution_time,
                    "error": None
                }
            else:
                return {
                    "query": query,
                    "success": False,
                    "error": "No location extraction data",
                    "execution_time": execution_time
                }
                
        except Exception as e:
            return {
                "query": query,
                "success": False,
                "error": str(e),
                "execution_time": 0
            }
    
    def display_validation_results(self, results: List[Dict[str, Any]], category: str) -> None:
        """Display validation results for a category."""
        category_results = [r for r in results if r.get("category") == category]
        if not category_results:
            return
            
        self.console.print(f"\n[bold blue]📊 {category} Results:[/bold blue]")
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Query", style="white", min_width=30)
        table.add_column("Location?", justify="center", style="green", min_width=10)
        table.add_column("City", style="yellow", min_width=12)
        table.add_column("State", style="yellow", min_width=12)
        table.add_column("Results", justify="right", style="blue", min_width=8)
        table.add_column("Status", justify="center", style="magenta", min_width=8)
        
        for result in category_results:
            if result["success"]:
                location_status = "✅ Yes" if result["has_location"] else "❌ No"
                city = result.get("city") or "—"
                state = result.get("state") or "—"
                results_count = f"{result['results_count']}/{result['total_hits']}"
                status = "✅"
                
                # Truncate long queries
                query_display = result["query"]
                if len(query_display) > 30:
                    query_display = query_display[:27] + "..."
                    
                table.add_row(query_display, location_status, city, state, results_count, status)
            else:
                query_display = result["query"]
                if len(query_display) > 30:
                    query_display = query_display[:27] + "..."
                table.add_row(query_display, "❌", "—", "—", "ERROR", "❌")
        
        self.console.print(table)
    
    def display_summary_recommendations(self, all_results: List[Dict[str, Any]]) -> None:
        """Display summary and recommendations for demo queries."""
        successful = [r for r in all_results if r["success"]]
        location_found = [r for r in successful if r["has_location"]]
        no_location = [r for r in successful if not r["has_location"]]
        
        self.console.print(Panel(
            f"[bold green]📈 Validation Summary[/bold green]\n\n"
            f"Total queries tested: {len(all_results)}\n"
            f"Successful queries: {len(successful)}\n"
            f"Location detected: {len(location_found)}\n"
            f"No location detected: {len(no_location)}\n"
            f"Failed queries: {len(all_results) - len(successful)}",
            title="Summary",
            border_style="green"
        ))
        
        # Recommend good demo queries
        good_location_queries = [r for r in location_found if r["results_count"] > 0]
        good_no_location = [r for r in no_location if r["results_count"] > 0]
        
        if good_location_queries:
            self.console.print(f"\n[bold green]✅ Recommended Location Queries for Demos:[/bold green]")
            for result in good_location_queries[:8]:  # Top 8
                city_state = f"{result.get('city', '')} {result.get('state', '')}".strip()
                self.console.print(f"  • \"{result['query']}\" → {city_state} ({result['results_count']} results)")
        
        if good_no_location:
            self.console.print(f"\n[bold yellow]✅ Recommended Non-Location Queries for Demos:[/bold yellow]")  
            for result in good_no_location[:4]:  # Top 4
                self.console.print(f"  • \"{result['query']}\" ({result['results_count']} results)")
    
    async def run_validation(self):
        """Run the validation process."""
        self.display_demo_header("Tests various queries to find ones that work well with DSPy location extraction")
        
        test_queries = self.get_test_queries()
        self.console.print(f"\n[bold yellow]🔍 Testing {len(test_queries)} queries...[/bold yellow]")
        
        # Test all queries
        all_results = []
        for query_info in test_queries:
            result = await self.validate_query(query_info["query"])
            result["category"] = query_info["category"]
            all_results.append(result)
            
            # Show progress
            status = "✅" if result["success"] and result.get("has_location") else ("⚠️" if result["success"] else "❌")
            self.console.print(f"{status} {query_info['query'][:50]}...")
        
        # Display results by category
        categories = ["Known Working", "Known Failing", "Park City", "California Cities", 
                     "Other States", "No Location", "Vague Location"]
        
        for category in categories:
            self.display_validation_results(all_results, category)
        
        # Display summary and recommendations
        self.display_summary_recommendations(all_results)
        
        return all_results
    
    async def run_demo_queries(self) -> DemoExecutionResult:
        """Required abstract method - runs the validation."""
        results = await self.run_validation()
        successful = len([r for r in results if r["success"]])
        
        return DemoExecutionResult(
            demo_name=self.demo_name,
            demo_number=self.demo_number,
            success=True,
            queries_executed=len(results),
            queries_successful=successful,
            total_execution_time_ms=0,
            error_message=None
        )


async def main():
    """Run the query validation."""
    validator = QueryValidator()
    await validator.run_validation()
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)