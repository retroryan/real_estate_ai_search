"""
Integration tests for property endpoints.

Tests all property-related API endpoints with real data to verify
complete functionality including pagination, filtering, and error handling.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestPropertyEndpoints:
    """Test suite for property API endpoints."""
    
    def test_get_all_properties_default_pagination(self, test_client: TestClient):
        """
        Test getting all properties with default pagination.
        
        Verifies:
        - Returns 200 OK status
        - Contains data, metadata, and links
        - Pagination metadata is correct
        - Properties are properly enriched
        """
        response = test_client.get("/api/v1/properties")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify response structure
        assert "data" in data
        assert "metadata" in data
        assert "links" in data
        
        # Verify metadata structure
        metadata = data["metadata"]
        assert "total_count" in metadata
        assert "page" in metadata
        assert "page_size" in metadata
        assert "total_pages" in metadata
        assert "has_next" in metadata
        assert "has_previous" in metadata
        assert "timestamp" in metadata
        
        # Verify default pagination values
        assert metadata["page"] == 1
        assert metadata["page_size"] == 50
        assert metadata["has_previous"] is False
        assert isinstance(metadata["total_count"], int)
        assert metadata["total_count"] > 0
        
        # Verify links structure
        links = data["links"]
        assert "self" in links
        assert "first" in links
        assert "last" in links
        
        # Verify properties data
        properties = data["data"]
        assert isinstance(properties, list)
        assert len(properties) > 0
        assert len(properties) <= 50  # Should not exceed page_size
        
        # Verify first property structure (enriched property)
        first_property = properties[0]
        assert "listing_id" in first_property
        assert "property_type" in first_property
        assert "price" in first_property
        assert "address" in first_property
        
        # Verify address enrichment
        address = first_property["address"]
        assert "city" in address
        assert "state" in address
        assert isinstance(address["city"], str)
        assert isinstance(address["state"], str)
        assert len(address["city"]) > 0
        assert len(address["state"]) > 0
    
    def test_get_properties_with_custom_pagination(self, test_client: TestClient):
        """
        Test properties endpoint with custom pagination parameters.
        
        Verifies:
        - Custom page and page_size parameters work
        - Metadata reflects custom pagination
        - Links are properly generated
        """
        response = test_client.get("/api/v1/properties?page=2&page_size=10")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        metadata = data["metadata"]
        assert metadata["page"] == 2
        assert metadata["page_size"] == 10
        assert metadata["has_previous"] is True
        
        properties = data["data"]
        assert len(properties) <= 10
        
        # Verify links include custom page_size
        links = data["links"]
        assert "page_size=10" in links["self"]
        if links.get("next"):
            assert "page_size=10" in links["next"]
    
    def test_get_properties_filtered_by_city(self, test_client: TestClient, valid_cities):
        """
        Test filtering properties by city.
        
        Verifies:
        - City filtering works correctly
        - All returned properties match the filter
        - Metadata reflects filtered results
        """
        city = valid_cities[0]  # Use first valid city
        response = test_client.get(f"/api/v1/properties?city={city}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        properties = data["data"]
        assert len(properties) > 0
        
        # Verify all properties match the city filter
        for property_data in properties:
            property_city = property_data["address"]["city"]
            # Case-insensitive comparison
            assert property_city.lower() == city.lower()
        
        # Verify links include city parameter
        links = data["links"]
        assert f"city={city}" in links["self"]
    
    def test_get_properties_with_invalid_city(self, test_client: TestClient, invalid_city):
        """
        Test filtering properties by non-existent city.
        
        Verifies:
        - Returns 200 OK (not an error)
        - Returns empty results
        - Metadata shows zero count
        """
        response = test_client.get(f"/api/v1/properties?city={invalid_city}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        properties = data["data"]
        assert len(properties) == 0
        
        metadata = data["metadata"]
        assert metadata["total_count"] == 0
    
    def test_get_properties_with_include_embeddings_flag(self, test_client: TestClient):
        """
        Test properties endpoint with include_embeddings flag.
        
        Note: Currently this just logs a warning as embedding integration
        is not yet implemented, but it should not cause errors.
        """
        response = test_client.get("/api/v1/properties?include_embeddings=true")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should still return properties normally
        assert "data" in data
        assert len(data["data"]) > 0
    
    def test_get_single_property_success(self, test_client: TestClient, sample_property_id):
        """
        Test getting a single property by ID.
        
        Verifies:
        - Returns 200 OK for existing property
        - Returns properly enriched property data
        - Includes metadata about the property
        """
        response = test_client.get(f"/api/v1/properties/{sample_property_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify response structure
        assert "data" in data
        assert "metadata" in data
        
        # Verify property data
        property_data = data["data"]
        assert property_data["listing_id"] == sample_property_id
        assert "address" in property_data
        assert "price" in property_data
        assert "property_type" in property_data
        
        # Verify metadata
        metadata = data["metadata"]
        assert "property_id" in metadata
        assert "city" in metadata
        assert "state" in metadata
        assert metadata["property_id"] == sample_property_id
    
    def test_get_single_property_not_found(self, test_client: TestClient):
        """
        Test getting a non-existent property.
        
        Verifies:
        - Returns 404 Not Found status
        - Returns structured error response
        - Includes correlation ID
        """
        non_existent_id = "non-existent-property-123"
        response = test_client.get(f"/api/v1/properties/{non_existent_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Verify error response structure
        error_data = response.json()
        assert "error" in error_data
        
        error = error_data["error"]
        assert "code" in error
        assert "message" in error
        assert "correlation_id" in error
        assert non_existent_id in error["message"]
        
        # Verify correlation ID is in response headers
        assert "X-Correlation-ID" in response.headers
    
    def test_get_properties_invalid_page_number(self, test_client: TestClient):
        """
        Test properties endpoint with invalid page number.
        
        Verifies:
        - Returns 404 for page numbers beyond available data
        - Returns structured error response
        """
        response = test_client.get("/api/v1/properties?page=999")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        error_data = response.json()
        assert "error" in error_data
        assert "Page 999 not found" in error_data["error"]["message"]
    
    def test_get_properties_invalid_page_size(self, test_client: TestClient):
        """
        Test properties endpoint with invalid page_size parameter.
        
        Verifies:
        - Returns 422 Unprocessable Entity for invalid page_size
        - Validates page_size constraints (1-500)
        """
        # Test page_size too large
        response = test_client.get("/api/v1/properties?page_size=1000")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test page_size zero
        response = test_client.get("/api/v1/properties?page_size=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test negative page_size
        response = test_client.get("/api/v1/properties?page_size=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_properties_response_has_correlation_id(self, test_client: TestClient):
        """
        Test that all property endpoints include correlation ID in response headers.
        
        Verifies:
        - All responses include X-Correlation-ID header
        - Correlation ID is properly formatted
        """
        response = test_client.get("/api/v1/properties")
        
        assert response.status_code == status.HTTP_200_OK
        assert "X-Correlation-ID" in response.headers
        
        correlation_id = response.headers["X-Correlation-ID"]
        assert isinstance(correlation_id, str)
        assert len(correlation_id) > 0
        assert "-" in correlation_id  # Basic UUID format check