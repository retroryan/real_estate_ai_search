"""
Integration tests for neighborhood endpoints.

Tests all neighborhood-related API endpoints with real data to verify
complete functionality including pagination, filtering, and error handling.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestNeighborhoodEndpoints:
    """Test suite for neighborhood API endpoints."""
    
    def test_get_all_neighborhoods_default_pagination(self, test_client: TestClient):
        """
        Test getting all neighborhoods with default pagination.
        
        Verifies:
        - Returns 200 OK status
        - Contains data, metadata, and links
        - Pagination metadata is correct
        - Neighborhoods are properly enriched
        """
        response = test_client.get("/api/v1/neighborhoods")
        
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
        
        # Verify default pagination values
        assert metadata["page"] == 1
        assert metadata["page_size"] == 50
        assert metadata["has_previous"] is False
        assert isinstance(metadata["total_count"], int)
        assert metadata["total_count"] > 0
        
        # Verify neighborhoods data
        neighborhoods = data["data"]
        assert isinstance(neighborhoods, list)
        assert len(neighborhoods) > 0
        assert len(neighborhoods) <= 50  # Should not exceed page_size
        
        # Verify first neighborhood structure (enriched neighborhood)
        first_neighborhood = neighborhoods[0]
        assert "neighborhood_id" in first_neighborhood
        assert "name" in first_neighborhood
        assert "city" in first_neighborhood
        assert "state" in first_neighborhood
        
        # Verify enrichment (city/state should be expanded)
        assert isinstance(first_neighborhood["city"], str)
        assert isinstance(first_neighborhood["state"], str)
        assert len(first_neighborhood["city"]) > 0
        assert len(first_neighborhood["state"]) > 0
    
    def test_get_neighborhoods_with_custom_pagination(self, test_client: TestClient):
        """
        Test neighborhoods endpoint with custom pagination parameters.
        
        Verifies:
        - Custom page and page_size parameters work
        - Metadata reflects custom pagination
        - Links are properly generated
        """
        response = test_client.get("/api/v1/neighborhoods?page=1&page_size=5")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        metadata = data["metadata"]
        assert metadata["page"] == 1
        assert metadata["page_size"] == 5
        
        neighborhoods = data["data"]
        assert len(neighborhoods) <= 5
        
        # Verify links include custom page_size
        links = data["links"]
        assert "page_size=5" in links["self"]
    
    def test_get_neighborhoods_filtered_by_city(self, test_client: TestClient, valid_cities):
        """
        Test filtering neighborhoods by city.
        
        Verifies:
        - City filtering works correctly
        - All returned neighborhoods match the filter
        - Metadata reflects filtered results
        """
        city = valid_cities[0]  # Use first valid city
        response = test_client.get(f"/api/v1/neighborhoods?city={city}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        neighborhoods = data["data"]
        assert len(neighborhoods) > 0
        
        # Verify all neighborhoods match the city filter
        for neighborhood in neighborhoods:
            neighborhood_city = neighborhood["city"]
            # Case-insensitive comparison
            assert neighborhood_city.lower() == city.lower()
        
        # Verify links include city parameter
        links = data["links"]
        assert f"city={city}" in links["self"]
    
    def test_get_neighborhoods_with_invalid_city(self, test_client: TestClient, invalid_city):
        """
        Test filtering neighborhoods by non-existent city.
        
        Verifies:
        - Returns 200 OK (not an error)
        - Returns empty results
        - Metadata shows zero count
        """
        response = test_client.get(f"/api/v1/neighborhoods?city={invalid_city}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        neighborhoods = data["data"]
        assert len(neighborhoods) == 0
        
        metadata = data["metadata"]
        assert metadata["total_count"] == 0
    
    def test_get_neighborhoods_with_include_embeddings_flag(self, test_client: TestClient):
        """
        Test neighborhoods endpoint with include_embeddings flag.
        
        Note: Currently this just logs a warning as embedding integration
        is not yet implemented, but it should not cause errors.
        """
        response = test_client.get("/api/v1/neighborhoods?include_embeddings=true")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should still return neighborhoods normally
        assert "data" in data
        assert len(data["data"]) > 0
    
    def test_get_single_neighborhood_success(self, test_client: TestClient, sample_neighborhood_id):
        """
        Test getting a single neighborhood by ID.
        
        Verifies:
        - Returns 200 OK for existing neighborhood
        - Returns properly enriched neighborhood data
        - Includes metadata about the neighborhood
        """
        response = test_client.get(f"/api/v1/neighborhoods/{sample_neighborhood_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify response structure
        assert "data" in data
        assert "metadata" in data
        
        # Verify neighborhood data
        neighborhood_data = data["data"]
        assert neighborhood_data["neighborhood_id"] == sample_neighborhood_id
        assert "name" in neighborhood_data
        assert "city" in neighborhood_data
        assert "state" in neighborhood_data
        
        # Verify metadata
        metadata = data["metadata"]
        assert "neighborhood_id" in metadata
        assert "city" in metadata
        assert "state" in metadata
        assert metadata["neighborhood_id"] == sample_neighborhood_id
    
    def test_get_single_neighborhood_not_found(self, test_client: TestClient):
        """
        Test getting a non-existent neighborhood.
        
        Verifies:
        - Returns 404 Not Found status
        - Returns structured error response
        - Includes correlation ID
        """
        non_existent_id = "non-existent-neighborhood-123"
        response = test_client.get(f"/api/v1/neighborhoods/{non_existent_id}")
        
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
    
    def test_get_neighborhoods_invalid_page_number(self, test_client: TestClient):
        """
        Test neighborhoods endpoint with invalid page number.
        
        Verifies:
        - Returns 404 for page numbers beyond available data
        - Returns structured error response
        """
        response = test_client.get("/api/v1/neighborhoods?page=999")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        error_data = response.json()
        assert "error" in error_data
        assert "Page 999 not found" in error_data["error"]["message"]
    
    def test_get_neighborhoods_invalid_parameters(self, test_client: TestClient):
        """
        Test neighborhoods endpoint with invalid parameters.
        
        Verifies:
        - Returns 422 Unprocessable Entity for invalid parameters
        - Validates parameter constraints
        """
        # Test page_size too large
        response = test_client.get("/api/v1/neighborhoods?page_size=1000")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test invalid page number
        response = test_client.get("/api/v1/neighborhoods?page=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_neighborhoods_response_has_correlation_id(self, test_client: TestClient):
        """
        Test that all neighborhood endpoints include correlation ID in response headers.
        
        Verifies:
        - All responses include X-Correlation-ID header
        - Correlation ID is properly formatted
        """
        response = test_client.get("/api/v1/neighborhoods")
        
        assert response.status_code == status.HTTP_200_OK
        assert "X-Correlation-ID" in response.headers
        
        correlation_id = response.headers["X-Correlation-ID"]
        assert isinstance(correlation_id, str)
        assert len(correlation_id) > 0
        assert "-" in correlation_id  # Basic UUID format check
    
    def test_neighborhoods_data_enrichment_quality(self, test_client: TestClient):
        """
        Test that neighborhood data shows proper enrichment quality.
        
        Verifies:
        - City and state names are properly expanded
        - Characteristics are normalized
        - Required fields are present
        """
        response = test_client.get("/api/v1/neighborhoods?page_size=5")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        neighborhoods = data["data"]
        assert len(neighborhoods) > 0
        
        for neighborhood in neighborhoods:
            # Verify enrichment quality
            assert len(neighborhood["city"]) > 2  # Should be full names, not abbreviations
            assert len(neighborhood["state"]) > 2  # Should be full names, not codes
            
            # Verify characteristics are lists (even if empty)
            if "characteristics" in neighborhood:
                assert isinstance(neighborhood["characteristics"], list)
            
            # Verify POI count is present and valid
            if "poi_count" in neighborhood:
                assert isinstance(neighborhood["poi_count"], int)
                assert neighborhood["poi_count"] >= 0