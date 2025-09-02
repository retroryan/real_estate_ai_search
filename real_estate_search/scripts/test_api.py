#!/usr/bin/env python3
"""
Test script for Property Search API endpoints.
Tests all API functionality with various scenarios.
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
from rich import print as rprint

from real_estate_search.indexer.enums import PropertyType, PropertyStatus, SortOrder


console = Console()


class APITester:
    """Test Property Search API endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize API tester.
        
        Args:
            base_url: Base URL for API
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        
    def print_section(self, title: str, description: str = ""):
        """Print section header."""
        console.print("\n" + "="*80)
        console.print(f"[bold cyan]{title}[/bold cyan]")
        if description:
            console.print(f"[dim]{description}[/dim]")
        console.print("="*80)
    
    def print_request(self, method: str, endpoint: str, data: Optional[Dict] = None):
        """Print request details."""
        console.print(f"\n[yellow]Request:[/yellow] {method} {endpoint}")
        if data:
            console.print("[yellow]Body:[/yellow]")
            rprint(data)
    
    def print_response(self, response: requests.Response, show_full: bool = False):
        """Print response details."""
        console.print(f"\n[green]Response:[/green] {response.status_code} {response.reason}")
        console.print(f"[green]Time:[/green] {response.elapsed.total_seconds():.3f}s")
        
        if response.headers.get('X-Request-ID'):
            console.print(f"[green]Request ID:[/green] {response.headers['X-Request-ID']}")
        
        if response.ok:
            data = response.json()
            if show_full:
                rprint(data)
            else:
                # Show summary for lists
                if isinstance(data, dict):
                    if 'properties' in data:
                        console.print(f"[green]Results:[/green] {len(data['properties'])} properties found")
                        console.print(f"[green]Total:[/green] {data.get('total', 0)} matches")
                        if data['properties']:
                            self._print_property_table(data['properties'][:5])
                    else:
                        rprint(data)
                else:
                    rprint(data)
        else:
            console.print(f"[red]Error:[/red] {response.text}")
    
    def _print_property_table(self, properties: list):
        """Print properties in a table."""
        table = Table(title="Properties")
        table.add_column("ID", style="dim", width=12)
        table.add_column("Type", style="cyan")
        table.add_column("Price", justify="right", style="green")
        table.add_column("Beds/Baths", justify="right")
        table.add_column("SqFt", justify="right")
        table.add_column("Address", style="yellow")
        
        for prop in properties:
            table.add_row(
                prop['id'][:12],
                prop['property_type'],
                f"${prop['price']:,.0f}",
                f"{prop['bedrooms']}/{prop['bathrooms']}",
                str(prop.get('square_feet', 'N/A')),
                f"{prop['street']}, {prop['city']}"
            )
        
        console.print(table)
    
    def test_health(self):
        """Test health endpoint."""
        self.print_section("Health Check", "Testing system health and connectivity")
        
        endpoint = f"{self.base_url}/api/health"
        self.print_request("GET", endpoint)
        
        response = self.session.get(endpoint)
        self.print_response(response, show_full=True)
        
        return response.ok
    
    def test_basic_search(self):
        """Test basic text search."""
        self.print_section("Basic Text Search", "Search for properties with text query")
        
        endpoint = f"{self.base_url}/api/search"
        data = {
            "query": "modern kitchen",
            "query_type": "text",
            "size": 10
        }
        
        self.print_request("POST", endpoint, data)
        response = self.session.post(endpoint, json=data)
        self.print_response(response)
        
        return response.ok
    
    def test_filtered_search(self):
        """Test search with filters."""
        self.print_section("Filtered Search", "Search with price and bedroom filters")
        
        endpoint = f"{self.base_url}/api/search"
        data = {
            "query_type": "filter",
            "filters": {
                "min_price": 500000,
                "max_price": 1000000,
                "min_bedrooms": 3,
                "property_types": ["single_family", "condo"]
            },
            "sort_by": "price_asc",
            "size": 10
        }
        
        self.print_request("POST", endpoint, data)
        response = self.session.post(endpoint, json=data)
        self.print_response(response)
        
        return response.ok
    
    def test_combined_search(self):
        """Test combined text and filter search."""
        self.print_section("Combined Search", "Text search with filters")
        
        endpoint = f"{self.base_url}/api/search"
        data = {
            "query": "pool",
            "query_type": "text",
            "filters": {
                "min_bedrooms": 4,
                "cities": ["San Francisco", "Park City"]
            },
            "sort_by": "relevance",
            "size": 10,
            "include_aggregations": True
        }
        
        self.print_request("POST", endpoint, data)
        response = self.session.post(endpoint, json=data)
        self.print_response(response)
        
        if response.ok and response.json().get('aggregations'):
            console.print("\n[cyan]Aggregations:[/cyan]")
            rprint(response.json()['aggregations'])
        
        return response.ok
    
    def test_geo_search(self):
        """Test geographic radius search."""
        self.print_section("Geographic Search", "Find properties within radius")
        
        endpoint = f"{self.base_url}/api/geo-search"
        data = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "radius": 5,
            "unit": "kilometers",
            "filters": {
                "min_bedrooms": 2
            },
            "size": 10
        }
        
        self.print_request("POST", endpoint, data)
        response = self.session.post(endpoint, json=data)
        self.print_response(response)
        
        return response.ok
    
    def test_property_detail(self):
        """Test getting single property details."""
        self.print_section("Property Details", "Get detailed information for a property")
        
        # First get a property ID from search
        search_response = self.session.post(
            f"{self.base_url}/api/search",
            json={"query_type": "filter", "size": 1}
        )
        
        if search_response.ok and search_response.json()['properties']:
            property_id = search_response.json()['properties'][0]['id']
            
            endpoint = f"{self.base_url}/api/properties/{property_id}"
            self.print_request("GET", endpoint)
            
            response = self.session.get(endpoint)
            self.print_response(response)
            
            if response.ok:
                prop = response.json()
                console.print(f"\n[cyan]Property Details:[/cyan]")
                console.print(f"  Listing ID: {prop['listing_id']}")
                console.print(f"  Type: {prop['property_type']}")
                console.print(f"  Price: ${prop['price']:,.0f}")
                console.print(f"  Bedrooms: {prop['bedrooms']}")
                console.print(f"  Bathrooms: {prop['bathrooms']}")
                console.print(f"  Square Feet: {prop.get('square_feet', 'N/A')}")
                console.print(f"  Year Built: {prop.get('year_built', 'N/A')}")
                
                if prop.get('features'):
                    console.print(f"  Features: {', '.join(prop['features'][:5])}")
            
            return response.ok
        else:
            console.print("[red]No properties found to test detail endpoint[/red]")
            return False
    
    def test_similar_properties(self):
        """Test finding similar properties."""
        self.print_section("Similar Properties", "Find properties similar to a given property")
        
        # First get a property ID
        search_response = self.session.post(
            f"{self.base_url}/api/search",
            json={"query_type": "filter", "size": 1}
        )
        
        if search_response.ok and search_response.json()['properties']:
            property_id = search_response.json()['properties'][0]['id']
            
            endpoint = f"{self.base_url}/api/properties/{property_id}/similar"
            data = {
                "max_results": 5,
                "include_source": False
            }
            
            self.print_request("POST", endpoint, data)
            response = self.session.post(endpoint, json=data)
            self.print_response(response)
            
            return response.ok
        else:
            console.print("[red]No properties found to test similar endpoint[/red]")
            return False
    
    def test_statistics(self):
        """Test market statistics endpoint."""
        self.print_section("Market Statistics", "Get aggregate market statistics")
        
        endpoint = f"{self.base_url}/api/stats"
        self.print_request("GET", endpoint)
        
        response = self.session.get(endpoint)
        self.print_response(response)
        
        if response.ok:
            stats = response.json()
            console.print(f"\n[cyan]Market Statistics:[/cyan]")
            console.print(f"  Total Properties: {stats['total_properties']}")
            
            if 'aggregations' in stats:
                aggs = stats['aggregations']
                if 'price_stats' in aggs:
                    price = aggs['price_stats']
                    console.print(f"  Average Price: ${price['avg']:,.0f}")
                    console.print(f"  Min Price: ${price['min']:,.0f}")
                    console.print(f"  Max Price: ${price['max']:,.0f}")
        
        return response.ok
    
    def test_pagination(self):
        """Test pagination."""
        self.print_section("Pagination", "Test result pagination")
        
        endpoint = f"{self.base_url}/api/search"
        
        # Page 1
        console.print("\n[yellow]Page 1:[/yellow]")
        data = {
            "query_type": "filter",
            "page": 1,
            "size": 5
        }
        response1 = self.session.post(endpoint, json=data)
        self.print_response(response1)
        
        # Page 2
        console.print("\n[yellow]Page 2:[/yellow]")
        data['page'] = 2
        response2 = self.session.post(endpoint, json=data)
        self.print_response(response2)
        
        return response1.ok and response2.ok
    
    def test_error_handling(self):
        """Test error handling."""
        self.print_section("Error Handling", "Test API error responses")
        
        # Test 404
        console.print("\n[yellow]Testing 404 - Invalid property ID:[/yellow]")
        response = self.session.get(f"{self.base_url}/api/properties/invalid-id-12345")
        console.print(f"Response: {response.status_code} - {response.text[:100]}")
        
        # Test validation error
        console.print("\n[yellow]Testing validation error - Invalid search:[/yellow]")
        response = self.session.post(
            f"{self.base_url}/api/search",
            json={"query_type": "text"}  # Missing required query field
        )
        console.print(f"Response: {response.status_code} - {response.text[:200]}")
        
        # Test invalid geo search
        console.print("\n[yellow]Testing invalid geo search:[/yellow]")
        response = self.session.post(
            f"{self.base_url}/api/geo-search",
            json={"latitude": 200, "longitude": 300, "radius": -5}  # Invalid values
        )
        console.print(f"Response: {response.status_code} - {response.text[:200]}")
        
        return True
    
    def run_all_tests(self):
        """Run all API tests."""
        console.print(Panel.fit(
            "[bold green]Property Search API Test Suite[/bold green]\n"
            "Testing all API endpoints and functionality",
            border_style="green"
        ))
        
        tests = [
            ("Health Check", self.test_health),
            ("Basic Search", self.test_basic_search),
            ("Filtered Search", self.test_filtered_search),
            ("Combined Search", self.test_combined_search),
            ("Geographic Search", self.test_geo_search),
            ("Property Details", self.test_property_detail),
            ("Similar Properties", self.test_similar_properties),
            ("Market Statistics", self.test_statistics),
            ("Pagination", self.test_pagination),
            ("Error Handling", self.test_error_handling)
        ]
        
        results = []
        for name, test_func in tests:
            try:
                success = test_func()
                results.append((name, success))
            except Exception as e:
                console.print(f"[red]Test failed with exception: {e}[/red]")
                results.append((name, False))
            
            time.sleep(0.5)  # Small delay between tests
        
        # Print summary
        self.print_summary(results)
    
    def print_summary(self, results: list):
        """Print test summary."""
        console.print("\n" + "="*80)
        console.print("[bold cyan]Test Summary[/bold cyan]")
        console.print("="*80)
        
        table = Table(title="Test Results")
        table.add_column("Test", style="cyan")
        table.add_column("Status", justify="center")
        
        passed = 0
        for name, success in results:
            status = "[green]✓ PASSED[/green]" if success else "[red]✗ FAILED[/red]"
            table.add_row(name, status)
            if success:
                passed += 1
        
        console.print(table)
        
        total = len(results)
        percentage = (passed / total * 100) if total > 0 else 0
        
        console.print(f"\n[bold]Total:[/bold] {passed}/{total} tests passed ({percentage:.1f}%)")
        
        if passed == total:
            console.print("[bold green]All tests passed! 🎉[/bold green]")
        elif passed >= total * 0.8:
            console.print("[bold yellow]Most tests passed[/bold yellow]")
        else:
            console.print("[bold red]Many tests failed - please check API[/bold red]")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Property Search API")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL for API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--test",
        choices=[
            "health", "search", "filter", "combined", "geo", 
            "detail", "similar", "stats", "pagination", "errors", "all"
        ],
        default="all",
        help="Specific test to run (default: all)"
    )
    
    args = parser.parse_args()
    
    tester = APITester(args.url)
    
    # Check if API is running
    try:
        response = requests.get(f"{args.url}/api/health", timeout=2)
        if not response.ok:
            console.print("[red]API is not healthy. Please start the API server first.[/red]")
            console.print("Run: python real_estate_search/api/run.py")
            sys.exit(1)
    except requests.exceptions.RequestException:
        console.print("[red]Cannot connect to API. Please start the API server first.[/red]")
        console.print("Run: python real_estate_search/api/run.py")
        sys.exit(1)
    
    # Run requested tests
    if args.test == "all":
        tester.run_all_tests()
    else:
        test_map = {
            "health": tester.test_health,
            "search": tester.test_basic_search,
            "filter": tester.test_filtered_search,
            "combined": tester.test_combined_search,
            "geo": tester.test_geo_search,
            "detail": tester.test_property_detail,
            "similar": tester.test_similar_properties,
            "stats": tester.test_statistics,
            "pagination": tester.test_pagination,
            "errors": tester.test_error_handling
        }
        
        if args.test in test_map:
            test_map[args.test]()
        else:
            console.print(f"[red]Unknown test: {args.test}[/red]")


if __name__ == "__main__":
    main()