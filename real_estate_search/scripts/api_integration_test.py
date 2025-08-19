#!/usr/bin/env python3
"""
API Integration Test Script.
Tests complete workflows and data consistency across endpoints.
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint


console = Console()


class APIIntegrationTester:
    """Integration tests for Property Search API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize integration tester."""
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def print_test_header(self, test_name: str, description: str):
        """Print test header."""
        console.print("\n" + "="*80)
        console.print(f"[bold cyan]Integration Test: {test_name}[/bold cyan]")
        console.print(f"[dim]{description}[/dim]")
        console.print("-"*80)
    
    def assert_response(self, response: requests.Response, expected_status: int = 200) -> bool:
        """Assert response status and return success."""
        if response.status_code != expected_status:
            console.print(f"[red]✗ Expected status {expected_status}, got {response.status_code}[/red]")
            console.print(f"[red]Response: {response.text[:200]}[/red]")
            return False
        console.print(f"[green]✓ Status {response.status_code} OK[/green]")
        return True
    
    def assert_field(self, data: Dict, field: str, expected_value: Any = None) -> bool:
        """Assert field exists and optionally check value."""
        if field not in data:
            console.print(f"[red]✗ Field '{field}' not found in response[/red]")
            return False
        
        if expected_value is not None and data[field] != expected_value:
            console.print(f"[red]✗ Field '{field}' expected {expected_value}, got {data[field]}[/red]")
            return False
        
        console.print(f"[green]✓ Field '{field}' present{f' with value {data[field]}' if expected_value else ''}[/green]")
        return True
    
    def test_search_consistency(self) -> bool:
        """Test that search results are consistent across endpoints."""
        self.print_test_header(
            "Search Consistency",
            "Verify that property data is consistent between search and detail endpoints"
        )
        
        success = True
        
        # Step 1: Search for properties
        console.print("\n[yellow]Step 1: Search for properties[/yellow]")
        search_response = self.session.post(
            f"{self.base_url}/api/search",
            json={"query_type": "filter", "size": 5}
        )
        
        if not self.assert_response(search_response):
            return False
        
        search_data = search_response.json()
        if not search_data.get('properties'):
            console.print("[red]No properties found in search[/red]")
            return False
        
        property_summary = search_data['properties'][0]
        property_id = property_summary['id']
        
        # Step 2: Get property details
        console.print(f"\n[yellow]Step 2: Get details for property {property_id}[/yellow]")
        detail_response = self.session.get(f"{self.base_url}/api/properties/{property_id}")
        
        if not self.assert_response(detail_response):
            return False
        
        property_detail = detail_response.json()
        
        # Step 3: Verify consistency
        console.print("\n[yellow]Step 3: Verify data consistency[/yellow]")
        
        fields_to_check = ['listing_id', 'property_type', 'price', 'bedrooms', 'bathrooms']
        for field in fields_to_check:
            if property_summary.get(field) != property_detail.get(field):
                console.print(f"[red]✗ Inconsistent {field}: {property_summary.get(field)} vs {property_detail.get(field)}[/red]")
                success = False
            else:
                console.print(f"[green]✓ {field} consistent: {property_summary.get(field)}[/green]")
        
        return success
    
    def test_pagination_integrity(self) -> bool:
        """Test that pagination returns correct results."""
        self.print_test_header(
            "Pagination Integrity",
            "Verify that pagination returns unique results without duplicates"
        )
        
        all_ids = set()
        duplicates = []
        
        # Get first 3 pages
        for page in range(1, 4):
            console.print(f"\n[yellow]Fetching page {page}[/yellow]")
            
            response = self.session.post(
                f"{self.base_url}/api/search",
                json={"query_type": "filter", "page": page, "size": 10}
            )
            
            if not self.assert_response(response):
                return False
            
            data = response.json()
            
            # Check for duplicates
            for prop in data['properties']:
                if prop['id'] in all_ids:
                    duplicates.append(prop['id'])
                    console.print(f"[red]✗ Duplicate found: {prop['id']}[/red]")
                else:
                    all_ids.add(prop['id'])
            
            # Verify pagination metadata
            success = True
            success &= self.assert_field(data, 'page', page)
            success &= self.assert_field(data, 'size', 10)
            
            if not success:
                return False
        
        if duplicates:
            console.print(f"[red]✗ Found {len(duplicates)} duplicate properties[/red]")
            return False
        else:
            console.print(f"[green]✓ No duplicates found across {len(all_ids)} properties[/green]")
            return True
    
    def test_filter_accuracy(self) -> bool:
        """Test that filters return accurate results."""
        self.print_test_header(
            "Filter Accuracy",
            "Verify that filtered searches return only matching properties"
        )
        
        # Test price filter
        console.print("\n[yellow]Testing price filter ($500k - $800k)[/yellow]")
        
        response = self.session.post(
            f"{self.base_url}/api/search",
            json={
                "query_type": "filter",
                "filters": {
                    "min_price": 500000,
                    "max_price": 800000
                },
                "size": 20
            }
        )
        
        if not self.assert_response(response):
            return False
        
        data = response.json()
        out_of_range = []
        
        for prop in data['properties']:
            if prop['price'] < 500000 or prop['price'] > 800000:
                out_of_range.append((prop['id'], prop['price']))
        
        if out_of_range:
            console.print(f"[red]✗ Found {len(out_of_range)} properties outside price range[/red]")
            for prop_id, price in out_of_range[:3]:
                console.print(f"  - {prop_id}: ${price:,.0f}")
            return False
        else:
            console.print(f"[green]✓ All {len(data['properties'])} properties within price range[/green]")
        
        # Test bedroom filter
        console.print("\n[yellow]Testing bedroom filter (3+ bedrooms)[/yellow]")
        
        response = self.session.post(
            f"{self.base_url}/api/search",
            json={
                "query_type": "filter",
                "filters": {"min_bedrooms": 3},
                "size": 20
            }
        )
        
        if not self.assert_response(response):
            return False
        
        data = response.json()
        invalid_bedrooms = []
        
        for prop in data['properties']:
            if prop['bedrooms'] < 3:
                invalid_bedrooms.append((prop['id'], prop['bedrooms']))
        
        if invalid_bedrooms:
            console.print(f"[red]✗ Found {len(invalid_bedrooms)} properties with < 3 bedrooms[/red]")
            return False
        else:
            console.print(f"[green]✓ All {len(data['properties'])} properties have 3+ bedrooms[/green]")
        
        return True
    
    def test_geo_search_distance(self) -> bool:
        """Test geographic search returns properties within radius."""
        self.print_test_header(
            "Geographic Search Distance",
            "Verify that geo search respects distance radius"
        )
        
        # San Francisco coordinates
        lat, lon = 37.7749, -122.4194
        radius = 10  # km
        
        console.print(f"\n[yellow]Searching within {radius}km of ({lat}, {lon})[/yellow]")
        
        response = self.session.post(
            f"{self.base_url}/api/geo-search",
            json={
                "latitude": lat,
                "longitude": lon,
                "radius": radius,
                "unit": "kilometers",
                "size": 20
            }
        )
        
        if not self.assert_response(response):
            return False
        
        data = response.json()
        
        if not data['properties']:
            console.print("[yellow]No properties found in geo search[/yellow]")
            return True
        
        # Check that distance is provided and within radius
        for prop in data['properties']:
            if 'distance' not in prop or prop['distance'] is None:
                console.print(f"[red]✗ Property {prop['id']} missing distance[/red]")
                return False
            
            if prop['distance'] > radius:
                console.print(f"[red]✗ Property {prop['id']} distance {prop['distance']:.2f}km > {radius}km[/red]")
                return False
        
        console.print(f"[green]✓ All {len(data['properties'])} properties within {radius}km radius[/green]")
        return True
    
    def test_similar_properties_workflow(self) -> bool:
        """Test complete workflow of finding similar properties."""
        self.print_test_header(
            "Similar Properties Workflow",
            "Test finding and validating similar properties"
        )
        
        # Step 1: Find a luxury property
        console.print("\n[yellow]Step 1: Find a luxury property[/yellow]")
        
        response = self.session.post(
            f"{self.base_url}/api/search",
            json={
                "query_type": "filter",
                "filters": {"min_price": 1000000},
                "size": 1
            }
        )
        
        if not self.assert_response(response):
            return False
        
        data = response.json()
        if not data['properties']:
            console.print("[yellow]No luxury properties found[/yellow]")
            return True
        
        source_property = data['properties'][0]
        property_id = source_property['id']
        
        console.print(f"Found property: {property_id}")
        console.print(f"  Price: ${source_property['price']:,.0f}")
        console.print(f"  Type: {source_property['property_type']}")
        console.print(f"  Beds/Baths: {source_property['bedrooms']}/{source_property['bathrooms']}")
        
        # Step 2: Find similar properties
        console.print(f"\n[yellow]Step 2: Find similar properties[/yellow]")
        
        response = self.session.post(
            f"{self.base_url}/api/properties/{property_id}/similar",
            json={"max_results": 5, "include_source": False}
        )
        
        if not self.assert_response(response):
            return False
        
        similar_data = response.json()
        
        if not similar_data['properties']:
            console.print("[yellow]No similar properties found[/yellow]")
            return True
        
        # Step 3: Verify similar properties are actually similar
        console.print(f"\n[yellow]Step 3: Verify similarity[/yellow]")
        
        for similar in similar_data['properties']:
            # Check that it's not the same property
            if similar['id'] == property_id:
                console.print(f"[red]✗ Source property included in results[/red]")
                return False
            
            # Log similarity
            price_diff = abs(similar['price'] - source_property['price']) / source_property['price'] * 100
            console.print(f"  Similar property {similar['id'][:12]}: ${similar['price']:,.0f} ({price_diff:.1f}% diff)")
        
        console.print(f"[green]✓ Found {len(similar_data['properties'])} similar properties[/green]")
        return True
    
    def test_aggregation_accuracy(self) -> bool:
        """Test that aggregations return accurate statistics."""
        self.print_test_header(
            "Aggregation Accuracy",
            "Verify that aggregations provide correct statistics"
        )
        
        # Get aggregations with search
        console.print("\n[yellow]Fetching aggregations[/yellow]")
        
        response = self.session.post(
            f"{self.base_url}/api/search",
            json={
                "query_type": "filter",
                "include_aggregations": True,
                "size": 1
            }
        )
        
        if not self.assert_response(response):
            return False
        
        data = response.json()
        
        if 'aggregations' not in data:
            console.print("[red]✗ No aggregations in response[/red]")
            return False
        
        aggs = data['aggregations']
        console.print("\n[cyan]Aggregations received:[/cyan]")
        
        # Check expected aggregation types
        expected_aggs = ['price_ranges', 'property_types', 'cities', 'bedroom_counts']
        found_aggs = []
        
        for agg_name in expected_aggs:
            if agg_name in aggs:
                found_aggs.append(agg_name)
                console.print(f"[green]✓ {agg_name} aggregation present[/green]")
                
                # Show sample data
                if 'buckets' in aggs[agg_name]:
                    buckets = aggs[agg_name]['buckets'][:3]
                    for bucket in buckets:
                        if isinstance(bucket, dict):
                            key = bucket.get('key', 'unknown')
                            count = bucket.get('doc_count', 0)
                            console.print(f"    - {key}: {count} properties")
            else:
                console.print(f"[yellow]○ {agg_name} aggregation not found[/yellow]")
        
        return len(found_aggs) > 0
    
    def test_error_recovery(self) -> bool:
        """Test API error handling and recovery."""
        self.print_test_header(
            "Error Recovery",
            "Verify that API handles errors gracefully and recovers"
        )
        
        # Test 1: Invalid request recovery
        console.print("\n[yellow]Test 1: Invalid request recovery[/yellow]")
        
        # Send invalid request
        response = self.session.post(
            f"{self.base_url}/api/search",
            json={"invalid_field": "test"}
        )
        
        if response.status_code >= 500:
            console.print("[red]✗ Server error on invalid request[/red]")
            return False
        
        console.print(f"[green]✓ Handled invalid request with status {response.status_code}[/green]")
        
        # Verify API still works after error
        response = self.session.get(f"{self.base_url}/api/health")
        if not self.assert_response(response):
            console.print("[red]✗ API unhealthy after error[/red]")
            return False
        
        console.print("[green]✓ API healthy after handling error[/green]")
        
        # Test 2: Large request handling
        console.print("\n[yellow]Test 2: Large request handling[/yellow]")
        
        response = self.session.post(
            f"{self.base_url}/api/search",
            json={
                "query_type": "filter",
                "size": 100  # Max size
            }
        )
        
        if not self.assert_response(response):
            return False
        
        data = response.json()
        if len(data['properties']) > 100:
            console.print(f"[red]✗ Returned {len(data['properties'])} properties, exceeds limit[/red]")
            return False
        
        console.print(f"[green]✓ Properly limited results to {len(data['properties'])} properties[/green]")
        
        return True
    
    def run_all_tests(self) -> None:
        """Run all integration tests."""
        console.print(Panel.fit(
            "[bold green]API Integration Test Suite[/bold green]\n"
            "Testing workflows and data consistency",
            border_style="green"
        ))
        
        tests = [
            ("Search Consistency", self.test_search_consistency),
            ("Pagination Integrity", self.test_pagination_integrity),
            ("Filter Accuracy", self.test_filter_accuracy),
            ("Geographic Search", self.test_geo_search_distance),
            ("Similar Properties", self.test_similar_properties_workflow),
            ("Aggregation Accuracy", self.test_aggregation_accuracy),
            ("Error Recovery", self.test_error_recovery)
        ]
        
        results = []
        for name, test_func in tests:
            try:
                success = test_func()
                results.append((name, success))
            except Exception as e:
                console.print(f"[red]Test '{name}' failed with exception: {e}[/red]")
                results.append((name, False))
            
            time.sleep(0.5)
        
        # Print summary
        self.print_summary(results)
    
    def print_summary(self, results: List[tuple]) -> None:
        """Print test summary."""
        console.print("\n" + "="*80)
        console.print("[bold cyan]Integration Test Summary[/bold cyan]")
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
            console.print("[bold green]All integration tests passed! 🎉[/bold green]")
        elif passed >= total * 0.8:
            console.print("[bold yellow]Most integration tests passed[/bold yellow]")
        else:
            console.print("[bold red]Integration tests need attention[/bold red]")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="API Integration Tests")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL for API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--test",
        help="Specific test to run"
    )
    
    args = parser.parse_args()
    
    # Check API availability
    try:
        response = requests.get(f"{args.url}/api/health", timeout=2)
        if not response.ok:
            console.print("[red]API is not healthy. Please check the server.[/red]")
            sys.exit(1)
    except requests.exceptions.RequestException:
        console.print("[red]Cannot connect to API. Please start the server first.[/red]")
        console.print("Run: python real_estate_search/api/run.py")
        sys.exit(1)
    
    tester = APIIntegrationTester(args.url)
    
    if args.test:
        # Run specific test
        test_map = {
            "consistency": tester.test_search_consistency,
            "pagination": tester.test_pagination_integrity,
            "filters": tester.test_filter_accuracy,
            "geo": tester.test_geo_search_distance,
            "similar": tester.test_similar_properties_workflow,
            "aggregations": tester.test_aggregation_accuracy,
            "errors": tester.test_error_recovery
        }
        
        if args.test in test_map:
            success = test_map[args.test]()
            sys.exit(0 if success else 1)
        else:
            console.print(f"[red]Unknown test: {args.test}[/red]")
            console.print(f"Available: {', '.join(test_map.keys())}")
            sys.exit(1)
    else:
        # Run all tests
        tester.run_all_tests()


if __name__ == "__main__":
    main()