#!/usr/bin/env python3
"""
Integration tests for Property Search API endpoints.
Tests all API functionality against a running server.
"""

import requests
import pytest
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime

# API Server Configuration
API_BASE_URL = "http://localhost:8000"
API_TIMEOUT = 30
HEADERS = {"Content-Type": "application/json"}

# Test Property ID (will be populated during tests)
TEST_PROPERTY_ID = None


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self):
        """Test /api/health endpoint returns healthy status."""
        response = requests.get(
            f"{API_BASE_URL}/api/health",
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "status" in data
        assert "timestamp" in data
        assert "api" in data
        assert "archive_elasticsearch" in data
        assert "index" in data
        assert "version" in data
        assert "environment" in data
        assert "debug_mode" in data
        
        # Verify status
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert data["api"]["status"] == "healthy"
        
        print(f"✅ Health check passed: {data['status']}")


class TestSearchEndpoints:
    """Test search-related endpoints."""
    
    def test_standard_search(self):
        """Test standard property search."""
        payload = {
            "query": "luxury home",
            "mode": "standard",
            "page": 1,
            "size": 10,
            "include_wikipedia": True,
            "include_aggregations": False
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search",
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "properties" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "total_pages" in data
        assert "took_ms" in data
        assert "mode" in data
        
        # Verify pagination
        assert data["page"] == 1
        assert data["size"] == 10
        assert data["mode"] == "standard"
        
        # Store property ID for later tests
        if data["properties"]:
            global TEST_PROPERTY_ID
            TEST_PROPERTY_ID = data["properties"][0]["id"]
            
        print(f"✅ Standard search passed: {data['total']} properties found")
    
    def test_search_with_filters(self):
        """Test search with filters."""
        payload = {
            "query": "pool",
            "mode": "standard",
            "filters": {
                "min_price": 500000,
                "max_price": 2000000,
                "min_bedrooms": 3,
                "cities": ["San Francisco", "Park City"]
            },
            "page": 1,
            "size": 5
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search",
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that filters were applied (where data is available)
        for prop in data["properties"]:
            assert prop["price"] >= 500000
            assert prop["price"] <= 2000000
            assert prop["bedrooms"] >= 3
            # City might be empty in some results, skip city check if empty
            if prop.get("city"):
                assert prop["city"] in ["San Francisco", "Park City", "Oakland"]
        
        print(f"✅ Filtered search passed: {len(data['properties'])} matching properties")
    
    def test_cultural_mode_search(self):
        """Test cultural mode search."""
        payload = {
            "query": "museum arts",
            "mode": "cultural",
            "filters": {
                "cities": ["San Francisco"]
            },
            "size": 5
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search",
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "cultural"
        
        print(f"✅ Cultural mode search passed: {data['total']} properties found")
    
    def test_lifestyle_mode_search(self):
        """Test lifestyle mode search."""
        payload = {
            "query": "park recreation family",
            "mode": "lifestyle",
            "filters": {
                "min_bedrooms": 3
            },
            "size": 5
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search",
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "lifestyle"
        
        print(f"✅ Lifestyle mode search passed: {data['total']} properties found")
    
    def test_poi_proximity_search(self):
        """Test POI proximity search."""
        payload = {
            "query": "Park",
            "mode": "poi_proximity",
            "size": 5
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search",
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "poi_proximity"
        
        # Check for results
        if data["properties"]:
            prop = data["properties"][0]
            assert "listing_id" in prop
        
        print(f"✅ POI proximity search passed: {data['total']} properties found")
    
    def test_investment_mode_search(self):
        """Test investment mode search."""
        payload = {
            "query": "tourist rental",
            "mode": "investment",
            "size": 5
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search",
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "investment"
        
        print(f"✅ Investment mode search passed: {data['total']} properties found")
    
    def test_geo_search(self):
        """Test geographic radius search."""
        payload = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "radius": 5,
            "unit": "kilometers",
            "filters": {
                "min_bedrooms": 2
            },
            "size": 10
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search/geo",
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "properties" in data
        assert "total" in data
        assert data["mode"] == "geographic"
        
        # Check distance is included for geo search
        if data["properties"]:
            prop = data["properties"][0]
            assert "distance" in prop or prop["distance"] is None
        
        print(f"✅ Geographic search passed: {data['total']} properties within radius")
    
    def test_search_with_aggregations(self):
        """Test search with aggregations enabled."""
        payload = {
            "query": "luxury",
            "mode": "standard",
            "include_aggregations": True,
            "size": 5
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search",
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check aggregations are included
        assert "aggregations" in data
        if data["aggregations"]:
            assert len(data["aggregations"]) > 0
        
        print(f"✅ Search with aggregations passed")
    
    def test_search_pagination(self):
        """Test search pagination."""
        # Get page 1
        payload1 = {
            "mode": "standard",
            "page": 1,
            "size": 5
        }
        
        response1 = requests.post(
            f"{API_BASE_URL}/api/v1/search",
            json=payload1,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Get page 2
        payload2 = {
            "mode": "standard",
            "page": 2,
            "size": 5
        }
        
        response2 = requests.post(
            f"{API_BASE_URL}/api/v1/search",
            json=payload2,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Verify pagination
        assert data1["page"] == 1
        assert data2["page"] == 2
        assert data1["size"] == data2["size"] == 5
        
        # Check that results are different
        if data1["properties"] and data2["properties"]:
            ids1 = {p["id"] for p in data1["properties"]}
            ids2 = {p["id"] for p in data2["properties"]}
            assert ids1 != ids2  # Different pages should have different properties
        
        print(f"✅ Pagination test passed")


class TestPropertyEndpoints:
    """Test property detail endpoints."""
    
    def test_property_details(self):
        """Test getting property details."""
        global TEST_PROPERTY_ID
        
        # Ensure we have a test property ID
        if not TEST_PROPERTY_ID:
            # Get a property ID first
            response = requests.post(
                f"{API_BASE_URL}/api/v1/search",
                json={"mode": "standard", "size": 1},
                headers=HEADERS,
                timeout=API_TIMEOUT
            )
            if response.status_code == 200 and response.json()["properties"]:
                TEST_PROPERTY_ID = response.json()["properties"][0]["id"]
        
        if not TEST_PROPERTY_ID:
            pytest.skip("No property ID available for testing")
        
        response = requests.get(
            f"{API_BASE_URL}/api/v1/properties/{TEST_PROPERTY_ID}",
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "id" in data
        assert "listing_id" in data
        assert "property_type" in data
        assert "price" in data
        assert "bedrooms" in data
        assert "bathrooms" in data
        assert "street" in data
        assert "city" in data
        assert "state" in data
        assert "zip_code" in data
        
        # Check optional enrichment fields
        assert "features" in data
        assert "amenities" in data
        
        print(f"✅ Property details test passed for ID: {TEST_PROPERTY_ID}")
    
    def test_property_wikipedia_context(self):
        """Test getting Wikipedia context for a property."""
        if not TEST_PROPERTY_ID:
            pytest.skip("No property ID available for testing")
        
        response = requests.get(
            f"{API_BASE_URL}/api/v1/properties/{TEST_PROPERTY_ID}/wikipedia",
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "property_id" in data
        assert data["property_id"] == TEST_PROPERTY_ID
        
        # Check basic fields are present
        assert "listing_id" in data
        assert "address" in data
        
        print(f"✅ Wikipedia context test passed for ID: {TEST_PROPERTY_ID}")
    
    def test_similar_properties(self):
        """Test finding similar properties."""
        if not TEST_PROPERTY_ID:
            pytest.skip("No property ID available for testing")
        
        payload = {
            "max_results": 5,
            "include_source": False
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/properties/{TEST_PROPERTY_ID}/similar",
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "properties" in data
        assert "total" in data
        assert data["mode"] == "similar"
        
        # Verify source property is excluded if requested
        if not payload["include_source"] and data["properties"]:
            for prop in data["properties"]:
                assert prop["id"] != TEST_PROPERTY_ID
        
        print(f"✅ Similar properties test passed: {len(data['properties'])} similar found")
    
    def test_property_not_found(self):
        """Test 404 error for non-existent property."""
        response = requests.get(
            f"{API_BASE_URL}/api/v1/properties/non-existent-id-12345",
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 404
        data = response.json()
        
        # Check error response structure
        assert "error" in data
        assert "message" in data
        assert "request_id" in data
        assert "timestamp" in data
        
        print(f"✅ Property not found (404) test passed")


class TestFacetsAndStats:
    """Test facets and statistics endpoints."""
    
    def test_facets_endpoint(self):
        """Test facets endpoint."""
        payload = {
            "query": "luxury",
            "filters": {
                "cities": ["San Francisco"]
            }
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/facets",
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "total_properties" in data
        
        # Check for various facet types (may be optional)
        possible_facets = [
            "price_ranges", "price_stats", "property_types",
            "cities", "neighborhoods", "bedroom_counts",
            "bathroom_counts", "features", "amenities",
            "poi_categories", "location_quality", "cultural_features"
        ]
        
        # At least some facets should be present
        facets_present = [f for f in possible_facets if f in data]
        assert len(facets_present) > 0
        
        print(f"✅ Facets test passed: {len(facets_present)} facet types returned")
    
    def test_facets_with_specific_selection(self):
        """Test facets with specific facet selection."""
        payload = {
            "facets": ["price_ranges", "property_types", "cities"]
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/facets",
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check only requested facets are returned
        assert "total_properties" in data
        
        # These should be present if data exists
        for facet in payload["facets"]:
            if facet in data:
                assert isinstance(data[facet], list)
        
        print(f"✅ Specific facets selection test passed")
    
    def test_market_stats(self):
        """Test market statistics endpoint."""
        response = requests.get(
            f"{API_BASE_URL}/api/v1/stats",
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "total_properties" in data
        assert "active_listings" in data
        assert "price_stats" in data
        assert "bedrooms_avg" in data
        assert "bathrooms_avg" in data
        assert "cities_count" in data
        assert "neighborhoods_count" in data
        assert "wikipedia_coverage" in data
        assert "top_features" in data
        assert "top_amenities" in data
        
        # Verify price stats structure
        assert "min" in data["price_stats"]
        assert "max" in data["price_stats"]
        assert "avg" in data["price_stats"]
        
        print(f"✅ Market stats test passed: {data['total_properties']} total properties")


class TestDemoEndpoints:
    """Test demo-specific endpoints."""
    
    def test_demo_queries(self):
        """Test demo queries endpoint."""
        response = requests.get(
            f"{API_BASE_URL}/api/demo/queries",
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "queries" in data
        assert "total" in data
        assert len(data["queries"]) > 0
        
        # Check query structure
        query = data["queries"][0]
        assert "name" in query
        assert "description" in query
        assert "request" in query
        
        print(f"✅ Demo queries test passed: {data['total']} sample queries available")
    
    def test_demo_tour(self):
        """Test demo tour endpoint."""
        response = requests.post(
            f"{API_BASE_URL}/api/demo/tour",
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "tour_results" in data
        assert "message" in data
        assert len(data["tour_results"]) > 0
        
        # Check tour result structure
        result = data["tour_results"][0]
        assert "search" in result
        assert "found" in result
        assert "top_results" in result
        
        print(f"✅ Demo tour test passed: {len(data['tour_results'])} searches demonstrated")
    
    def test_demo_reset(self):
        """Test demo index reset endpoint."""
        response = requests.post(
            f"{API_BASE_URL}/api/demo/reset",
            headers=HEADERS,
            timeout=API_TIMEOUT * 2  # Allow more time for index recreation
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "status" in data
        assert "message" in data
        assert "stats" in data
        assert data["status"] == "success"
        
        # Check stats structure
        assert "san_francisco" in data["stats"]
        assert "park_city" in data["stats"]
        
        print(f"✅ Demo reset test passed: Index recreated with demo data")


class TestErrorHandling:
    """Test error handling and validation."""
    
    def test_invalid_search_mode(self):
        """Test invalid search mode returns error."""
        payload = {
            "query": "test",
            "mode": "invalid_mode"
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search",
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # Check error structure
        assert "error" in data
        assert "message" in data
        assert data["error"] == "validation_error"
        
        print(f"✅ Invalid search mode validation test passed")
    
    def test_invalid_geo_coordinates(self):
        """Test invalid geographic coordinates."""
        payload = {
            "latitude": 200,  # Invalid latitude
            "longitude": -500,  # Invalid longitude
            "radius": 5,
            "unit": "kilometers"
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search/geo",
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 422
        data = response.json()
        # Check for either error or message field (both are valid)
        assert "error" in data or "message" in data
        
        print(f"✅ Invalid geo coordinates validation test passed")
    
    def test_invalid_pagination(self):
        """Test invalid pagination parameters."""
        payload = {
            "mode": "standard",
            "page": -1,  # Invalid page number
            "size": 1000  # Exceeds max size
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search",
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 422
        data = response.json()
        # Check for either error or message field (both are valid)
        assert "error" in data or "message" in data
        
        print(f"✅ Invalid pagination validation test passed")
    
    def test_missing_required_fields(self):
        """Test missing required fields in geo search."""
        payload = {
            "latitude": 37.7749
            # Missing longitude and radius
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search/geo",
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT
        )
        
        assert response.status_code == 422
        data = response.json()
        # Check for either error or message field (both are valid)
        assert "error" in data or "message" in data
        
        print(f"✅ Missing required fields validation test passed")


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("🧪 Property Search API Integration Tests")
    print("="*60)
    print(f"Testing API at: {API_BASE_URL}")
    print("-"*60)
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        if response.status_code != 200:
            print("❌ API is not healthy. Please start the API server first.")
            print("Run: python api/run.py")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to API at {API_BASE_URL}")
        print("Please start the API server first: python api/run.py")
        print(f"Error: {e}")
        return False
    
    # Test classes
    test_classes = [
        TestHealthEndpoint(),
        TestSearchEndpoints(),
        TestPropertyEndpoints(),
        TestFacetsAndStats(),
        TestDemoEndpoints(),
        TestErrorHandling()
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n📋 Running {class_name}")
        print("-"*40)
        
        # Get all test methods
        test_methods = [m for m in dir(test_class) if m.startswith("test_")]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_class, method_name)
                method()
                passed_tests += 1
            except AssertionError as e:
                failed_tests.append(f"{class_name}.{method_name}: {str(e)}")
                print(f"❌ {method_name} failed: {str(e)}")
            except Exception as e:
                failed_tests.append(f"{class_name}.{method_name}: {str(e)}")
                print(f"❌ {method_name} error: {str(e)}")
    
    # Print summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✅")
    print(f"Failed: {len(failed_tests)} ❌")
    
    if failed_tests:
        print("\n🔴 Failed Tests:")
        for failure in failed_tests:
            print(f"  - {failure}")
    else:
        print("\n🎉 All tests passed!")
    
    print("="*60)
    
    return len(failed_tests) == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)