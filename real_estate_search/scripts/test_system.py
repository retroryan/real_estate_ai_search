#!/usr/bin/env python3
"""
Test script for Phase 1 (Indexing) and Phase 2 (Search) functionality.
Validates that the Property Search System is working correctly.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

import structlog
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track

from real_estate_search.config.settings import Settings
from real_estate_search.indexer.property_indexer import PropertyIndexer
from real_estate_search.indexer.models import Property, Address, GeoLocation, Neighborhood
from real_estate_search.indexer.enums import PropertyType, PropertyStatus
from real_estate_search.search.search_engine import PropertySearchEngine
from real_estate_search.search.models import SearchRequest, SearchFilters, GeoSearchParams, GeoPoint
from real_estate_search.search.enums import QueryType, GeoDistanceUnit

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)
console = Console()


class PropertySearchTester:
    """Test harness for Property Search System."""
    
    def __init__(self):
        """Initialize the tester."""
        self.settings = Settings.load()
        self.indexer = None
        self.search_engine = None
        self.test_properties = []
        
    def run_all_tests(self) -> bool:
        """
        Run all tests for Phase 1 and Phase 2.
        
        Returns:
            True if all tests pass, False otherwise.
        """
        console.print("\n[bold cyan]Property Search System Test Suite[/bold cyan]\n")
        
        all_passed = True
        
        # Phase 1 Tests
        console.print(Panel("[bold]Phase 1: Indexing Tests[/bold]", style="blue"))
        
        if not self.test_connection():
            return False
            
        if not self.test_index_creation():
            all_passed = False
            
        if not self.test_property_indexing():
            all_passed = False
        
        # Phase 2 Tests
        console.print("\n" + "="*50 + "\n")
        console.print(Panel("[bold]Phase 2: Search Tests[/bold]", style="green"))
        
        if not self.test_text_search():
            all_passed = False
            
        if not self.test_filtered_search():
            all_passed = False
            
        if not self.test_geo_search():
            all_passed = False
            
        if not self.test_aggregations():
            all_passed = False
            
        if not self.test_similar_properties():
            all_passed = False
        
        # Summary
        self.print_summary(all_passed)
        
        return all_passed
    
    def test_connection(self) -> bool:
        """Test Elasticsearch connection with authentication."""
        console.print("\n[yellow]Testing Elasticsearch Connection...[/yellow]")
        
        try:
            self.indexer = PropertyIndexer(self.settings)
            
            # Test ping
            if self.indexer.es.ping():
                console.print("✅ Connected to Elasticsearch")
                
                # Check authentication
                if self.settings.elasticsearch.has_auth:
                    console.print(f"✅ Authenticated as: {self.settings.elasticsearch.username}")
                else:
                    console.print("ℹ️  No authentication configured")
                
                # Get cluster info
                info = self.indexer.es.info()
                console.print(f"✅ Cluster: {info['cluster_name']}")
                console.print(f"✅ Version: {info['version']['number']}")
                
                return True
            else:
                console.print("❌ Cannot connect to Elasticsearch")
                return False
                
        except Exception as e:
            console.print(f"❌ Connection failed: {e}")
            return False
    
    def test_index_creation(self) -> bool:
        """Test index creation with mappings."""
        console.print("\n[yellow]Testing Index Creation...[/yellow]")
        
        try:
            # Create index
            created = self.indexer.create_index(force=True)
            
            if created:
                console.print("✅ Index created successfully")
            else:
                console.print("ℹ️  Index already exists")
            
            # Verify alias
            if self.indexer.es.indices.exists_alias(name=self.settings.index.alias):
                console.print(f"✅ Alias '{self.settings.index.alias}' exists")
            else:
                console.print(f"❌ Alias '{self.settings.index.alias}' not found")
                return False
            
            # Check mappings
            mapping = self.indexer.es.indices.get_mapping(index=self.settings.index.alias)
            if mapping:
                console.print("✅ Mappings configured")
                
                # Count fields
                index_name = list(mapping.keys())[0]
                field_count = len(mapping[index_name]['mappings']['properties'])
                console.print(f"✅ {field_count} fields mapped")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Index creation failed: {e}")
            return False
    
    def test_property_indexing(self) -> bool:
        """Test property document indexing."""
        console.print("\n[yellow]Testing Property Indexing...[/yellow]")
        
        try:
            # Create test properties
            self.test_properties = self._create_test_properties()
            console.print(f"ℹ️  Created {len(self.test_properties)} test properties")
            
            # Index properties
            stats = self.indexer.index_properties(self.test_properties)
            
            console.print(f"✅ Indexed: {stats.success}/{stats.total}")
            if stats.failed > 0:
                console.print(f"⚠️  Failed: {stats.failed}")
                for error in stats.errors[:3]:
                    console.print(f"   - {error}")
            
            # Verify documents in index
            time.sleep(1)  # Wait for refresh
            count_response = self.indexer.es.count(index=self.settings.index.alias)
            doc_count = count_response['count']
            console.print(f"✅ Documents in index: {doc_count}")
            
            return stats.success > 0
            
        except Exception as e:
            console.print(f"❌ Indexing failed: {e}")
            return False
    
    def test_text_search(self) -> bool:
        """Test text search functionality."""
        console.print("\n[yellow]Testing Text Search...[/yellow]")
        
        try:
            self.search_engine = PropertySearchEngine(self.settings)
            
            # Test 1: Simple text search
            request = SearchRequest(
                query_type=QueryType.TEXT,
                query_text="modern kitchen",
                size=5
            )
            
            response = self.search_engine.search(request)
            console.print(f"✅ Text search returned {response.total} results")
            
            if response.hits:
                console.print(f"   Top result: {response.hits[0].property.address.street}")
            
            # Test 2: Multi-field search
            request = SearchRequest(
                query_type=QueryType.TEXT,
                query_text="park view",
                size=5
            )
            
            response = self.search_engine.search(request)
            console.print(f"✅ Multi-field search: {response.total} results")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Text search failed: {e}")
            return False
    
    def test_filtered_search(self) -> bool:
        """Test filtered search functionality."""
        console.print("\n[yellow]Testing Filtered Search...[/yellow]")
        
        try:
            # Test various filters
            filters = SearchFilters(
                min_price=300000,
                max_price=800000,
                min_bedrooms=3,
                property_types=[PropertyType.SINGLE_FAMILY, PropertyType.CONDO],
                cities=["park city", "san francisco"]
            )
            
            request = SearchRequest(
                query_type=QueryType.FILTER,
                filters=filters,
                size=10
            )
            
            response = self.search_engine.search(request)
            console.print(f"✅ Filtered search returned {response.total} results")
            
            # Verify filters worked
            for hit in response.hits[:3]:
                prop = hit.property
                assert prop.price >= 300000 and prop.price <= 800000
                assert prop.bedrooms >= 3
            
            console.print("✅ Filter validation passed")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Filtered search failed: {e}")
            return False
    
    def test_geo_search(self) -> bool:
        """Test geographic search functionality."""
        console.print("\n[yellow]Testing Geographic Search...[/yellow]")
        
        try:
            # Search within radius of Park City
            response = self.search_engine.geo_search(
                center_lat=40.6461,
                center_lon=-111.4980,
                radius=10,
                unit="km",
                size=10
            )
            
            console.print(f"✅ Geo search returned {response.total} results within 10km")
            
            # Check distances
            if response.hits:
                for hit in response.hits[:3]:
                    if hit.distance:
                        console.print(f"   Property at {hit.distance:.2f}km")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Geo search failed: {e}")
            return False
    
    def test_aggregations(self) -> bool:
        """Test aggregation functionality."""
        console.print("\n[yellow]Testing Aggregations...[/yellow]")
        
        try:
            request = SearchRequest(
                query_type=QueryType.TEXT,
                query_text="home",
                include_aggregations=True,
                size=1
            )
            
            response = self.search_engine.search(request)
            
            if response.aggregations:
                console.print(f"✅ Received {len(response.aggregations)} aggregations")
                
                # Display some aggregation results
                for agg_name, agg_data in list(response.aggregations.items())[:3]:
                    console.print(f"   - {agg_name}: {agg_data.type}")
            else:
                console.print("⚠️  No aggregations returned")
                return False
            
            return True
            
        except Exception as e:
            console.print(f"❌ Aggregations failed: {e}")
            return False
    
    def test_similar_properties(self) -> bool:
        """Test similar properties search."""
        console.print("\n[yellow]Testing Similar Properties...[/yellow]")
        
        try:
            # First get a property
            request = SearchRequest(
                query_type=QueryType.TEXT,
                query_text="luxury",
                size=1
            )
            
            response = self.search_engine.search(request)
            
            if not response.hits:
                console.print("⚠️  No properties found for similarity test")
                return True
            
            # Find similar properties
            source_id = response.hits[0].doc_id
            
            similar_request = SearchRequest(
                query_type=QueryType.SIMILAR,
                similar_to_id=source_id,
                size=5
            )
            
            similar_response = self.search_engine.search(similar_request)
            console.print(f"✅ Found {similar_response.total} similar properties")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Similar properties search failed: {e}")
            return False
    
    def _create_test_properties(self) -> List[Property]:
        """Create test property data."""
        properties = []
        
        # Test data for different scenarios
        test_data = [
            {
                "listing_id": "test-001",
                "property_type": PropertyType.SINGLE_FAMILY,
                "price": 750000,
                "bedrooms": 4,
                "bathrooms": 3.5,
                "square_feet": 2800,
                "address": Address(
                    street="123 Mountain View Dr",
                    city="Park City",
                    state="UT",
                    zip_code="84060",
                    location=GeoLocation(lat=40.6461, lon=-111.4980)
                ),
                "description": "Beautiful modern home with stunning mountain views and gourmet kitchen",
                "features": ["mountain view", "gourmet kitchen", "hardwood floors"],
                "amenities": ["garage", "deck", "fireplace"],
                "neighborhood": Neighborhood(
                    id="pc-001",
                    name="Old Town",
                    walkability_score=85
                )
            },
            {
                "listing_id": "test-002",
                "property_type": PropertyType.CONDO,
                "price": 450000,
                "bedrooms": 2,
                "bathrooms": 2,
                "square_feet": 1400,
                "address": Address(
                    street="456 Park Ave",
                    city="San Francisco",
                    state="CA",
                    zip_code="94102",
                    location=GeoLocation(lat=37.7749, lon=-122.4194)
                ),
                "description": "Urban condo with modern amenities and park views",
                "features": ["park view", "modern kitchen", "in-unit laundry"],
                "amenities": ["gym", "rooftop deck", "concierge"]
            },
            {
                "listing_id": "test-003",
                "property_type": PropertyType.TOWNHOUSE,
                "price": 625000,
                "bedrooms": 3,
                "bathrooms": 2.5,
                "square_feet": 2100,
                "address": Address(
                    street="789 Deer Valley Loop",
                    city="Park City",
                    state="UT",
                    zip_code="84060",
                    location=GeoLocation(lat=40.6374, lon=-111.4785)
                ),
                "description": "Luxury townhouse near ski slopes with modern finishes",
                "features": ["ski access", "modern design", "heated floors"],
                "amenities": ["hot tub", "ski storage", "garage"]
            }
        ]
        
        # Create more test properties
        for i, data in enumerate(test_data):
            property_model = Property(
                listing_id=data["listing_id"],
                property_type=data["property_type"],
                price=data["price"],
                bedrooms=data["bedrooms"],
                bathrooms=data["bathrooms"],
                square_feet=data.get("square_feet"),
                address=data["address"],
                description=data.get("description"),
                features=data.get("features", []),
                amenities=data.get("amenities", []),
                neighborhood=data.get("neighborhood"),
                status=PropertyStatus.ACTIVE,
                listing_date=datetime.now() - timedelta(days=i*10)
            )
            properties.append(property_model)
        
        return properties
    
    def print_summary(self, all_passed: bool) -> None:
        """Print test summary."""
        console.print("\n" + "="*50)
        
        if all_passed:
            console.print(Panel(
                "[bold green]✅ ALL TESTS PASSED[/bold green]\n\n"
                "Phase 1 (Indexing) and Phase 2 (Search) are working correctly!",
                style="green"
            ))
        else:
            console.print(Panel(
                "[bold red]❌ SOME TESTS FAILED[/bold red]\n\n"
                "Please check the error messages above.",
                style="red"
            ))
        
        # Print configuration info
        table = Table(title="Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("ES Host", f"{self.settings.elasticsearch.host}:{self.settings.elasticsearch.port}")
        table.add_row("Authentication", "Yes" if self.settings.elasticsearch.has_auth else "No")
        table.add_row("Index Alias", self.settings.index.alias)
        table.add_row("Environment", self.settings.environment)
        
        console.print(table)


def main():
    """Main entry point."""
    tester = PropertySearchTester()
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        logger.exception("Test suite failed")
        sys.exit(1)


if __name__ == "__main__":
    main()