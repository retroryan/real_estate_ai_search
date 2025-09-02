#!/usr/bin/env python3
"""
Demo 15: Basic Hybrid Search Functionality

This demo showcases the core hybrid search capabilities using clean Pydantic models
and FastMCP client best practices. Demonstrates semantic vector search, text matching,
and RRF fusion working together to find relevant properties.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import List
from rich.table import Table

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from real_estate_search.mcp_demos.base_demo import BaseMCPDemo
from real_estate_search.mcp_demos.models.hybrid_search import (
    HybridSearchRequest,
    DemoExecutionResult
)


class BasicHybridSearchDemo(BaseMCPDemo):
    """Demo showcasing basic hybrid search functionality with Pydantic validation."""
    
    def __init__(self):
        super().__init__(
            demo_name="Basic Hybrid Search Functionality",
            demo_number=15
        )
    
    def get_demo_queries(self) -> List[dict]:
        """Get the demo query configurations."""
        return [
            {
                "name": "Semantic Search",
                "query": "modern home with spacious kitchen and garage",
                "description": "Tests semantic understanding of property features",
                "size": 5
            },
            {
                "name": "Property Type Focus", 
                "query": "luxury condominium with amenities",
                "description": "Tests property type recognition and luxury features",
                "size": 5
            },
            {
                "name": "Family Home Features",
                "query": "family-friendly house with backyard and multiple bedrooms",
                "description": "Tests family-oriented feature matching",
                "size": 5
            },
            {
                "name": "Investment Property",
                "query": "income property duplex or multi-unit rental",
                "description": "Tests investment property terminology understanding",
                "size": 5
            }
        ]
    
    def display_search_results_table(self, response, query_name: str) -> None:
        """Display search results in a formatted table."""
        if not response.results:
            self.console.print("[dim]No results found[/dim]")
            return
            
        # Create results table
        table = Table(
            title=f"{query_name} - Top {len(response.results)} Properties",
            show_header=True,
            header_style="bold magenta"
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Type", style="cyan", min_width=8)
        table.add_column("Price", justify="right", style="green", min_width=10)
        table.add_column("Beds/Baths", justify="center", style="blue", min_width=10)
        table.add_column("Location", style="yellow", min_width=15)
        table.add_column("Score", justify="center", style="red", min_width=6)
        
        for i, prop in enumerate(response.results, 1):
            # Format property data safely
            property_type = prop.property_type or "Unknown"
            
            price_str = f"${prop.price:,.0f}" if prop.price else "N/A"
            
            beds = prop.bedrooms if prop.bedrooms is not None else "N/A"
            baths = prop.bathrooms if prop.bathrooms is not None else "N/A"
            beds_baths = f"{beds}/{baths}"
            
            city = prop.address.city or ""
            state = prop.address.state or ""
            location = f"{city}, {state}" if city and state else "Unknown"
            
            score_str = f"{prop.hybrid_score:.3f}" if prop.hybrid_score else "N/A"
            
            table.add_row(str(i), property_type, price_str, beds_baths, location, score_str)
        
        self.console.print(table)
    
    def display_sample_property_details(self, response) -> None:
        """Display detailed information about the first property result."""
        if not response.results:
            return
            
        sample_prop = response.results[0]
        addr = sample_prop.address
        
        details = []
        details.append(f"[bold]Property ID:[/bold] {sample_prop.listing_id or 'N/A'}")
        details.append(f"[bold]Type:[/bold] {sample_prop.property_type or 'N/A'}")
        if sample_prop.price:
            details.append(f"[bold]Price:[/bold] ${sample_prop.price:,.0f}")
        
        address_parts = []
        if addr.street:
            address_parts.append(addr.street)
        if addr.city:
            address_parts.append(addr.city)
        if addr.state:
            address_parts.append(addr.state)
        if address_parts:
            details.append(f"[bold]Address:[/bold] {', '.join(address_parts)}")
        
        size_parts = []
        if sample_prop.bedrooms is not None:
            size_parts.append(f"{sample_prop.bedrooms} bed")
        if sample_prop.bathrooms is not None:
            size_parts.append(f"{sample_prop.bathrooms} bath")
        if sample_prop.square_feet:
            size_parts.append(f"{sample_prop.square_feet} sqft")
        if size_parts:
            details.append(f"[bold]Size:[/bold] {', '.join(size_parts)}")
        
        if sample_prop.hybrid_score:
            details.append(f"[bold]Hybrid Score:[/bold] {sample_prop.hybrid_score:.3f}")
        
        if sample_prop.features:
            top_features = sample_prop.features[:3]
            details.append(f"[bold]Top Features:[/bold] {', '.join(top_features)}")
        
        from rich.panel import Panel
        self.console.print(Panel(
            "\n".join(details),
            title="Sample Property Details",
            border_style="green"
        ))
    
    async def run_demo_queries(self) -> DemoExecutionResult:
        """Execute the basic hybrid search demo queries."""
        self.display_demo_header("Showcases core hybrid search with RRF fusion via MCP HTTP client")
        
        demo_queries = self.get_demo_queries()
        queries_successful = 0
        start_time = time.time()
        
        self.console.print(f"\n[bold yellow]🔍 Running {len(demo_queries)} basic hybrid search queries...[/bold yellow]")
        
        for i, query_config in enumerate(demo_queries, 1):
            self.console.print(f"\n[bold blue]--- Query {i}: {query_config['name']} ---[/bold blue]")
            self.console.print(f"[dim]Query:[/dim] \"{query_config['query']}\"")
            self.console.print(f"[dim]Purpose:[/dim] {query_config['description']}")
            
            try:
                # Create validated request
                request = HybridSearchRequest(
                    query=query_config["query"],
                    size=query_config["size"],
                    include_location_extraction=False
                )
                
                # Execute hybrid search
                response = await self.execute_hybrid_search(request)
                
                # Display results
                metadata = response.metadata
                self.console.print(f"\n[green]📊 Results ({metadata.returned_hits} of {metadata.total_hits} total):[/green]")
                self.console.print(f"[dim]⏱️ Execution time: {metadata.execution_time_ms}ms[/dim]")
                
                # Show results table
                self.display_search_results_table(response, query_config['name'])
                
                # Show sample property details for first query
                if i == 1:
                    self.display_sample_property_details(response)
                
                self.console.print("[green]✅ Query completed successfully[/green]")
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
    """Run the basic hybrid search demo."""
    demo = BasicHybridSearchDemo()
    result = await demo.execute()
    return 0 if result.success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)