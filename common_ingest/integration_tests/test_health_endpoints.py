"""
Integration tests for health and root endpoints.

Tests the basic health check and root information endpoints to ensure
the API is properly configured and responsive.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test suite for health check and root endpoints."""
    
    def test_root_endpoint(self, test_client: TestClient):
        """
        Test the root endpoint returns API information.
        
        Verifies:
        - Returns 200 OK status
        - Contains expected API information fields
        - Includes version and description
        """
        response = test_client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify required fields are present
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "docs_url" in data
        assert "health_url" in data
        
        # Verify expected values
        assert data["name"] == "Common Ingest API"
        assert data["docs_url"] == "/docs"
        assert data["health_url"] == "/api/v1/health"
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0
    
    def test_health_endpoint(self, test_client: TestClient):
        """
        Test the health check endpoint.
        
        Verifies:
        - Returns 200 OK status
        - Contains health status information
        - Includes version and data source paths
        """
        response = test_client.get("/api/v1/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify required fields are present
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "components" in data  # Updated from data_sources
        
        # Verify expected values
        assert data["status"] == "healthy"
        assert isinstance(data["version"], str)
        assert isinstance(data["timestamp"], (int, float))
        assert data["timestamp"] > 0
        
        # Verify components structure
        components = data["components"]
        assert "property_data_directory" in components
        assert "wikipedia_database" in components
        
        # Verify property data component
        prop_component = components["property_data_directory"]
        assert prop_component["status"] == "healthy"
        assert "path" in prop_component
        assert "json_files_count" in prop_component
        
        # Verify wikipedia component
        wiki_component = components["wikipedia_database"]
        assert wiki_component["status"] == "healthy"
        assert "path" in wiki_component
        assert "size_mb" in wiki_component
    
    def test_health_endpoint_has_correlation_id(self, test_client: TestClient):
        """
        Test that health endpoint includes correlation ID in response headers.
        
        Verifies:
        - Response includes X-Correlation-ID header
        - Correlation ID is a valid UUID format
        """
        response = test_client.get("/api/v1/health")
        
        assert response.status_code == status.HTTP_200_OK
        assert "X-Correlation-ID" in response.headers
        
        correlation_id = response.headers["X-Correlation-ID"]
        assert isinstance(correlation_id, str)
        assert len(correlation_id) > 0
        
        # Basic UUID format validation (should contain dashes)
        assert "-" in correlation_id