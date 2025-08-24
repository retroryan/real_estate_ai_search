"""Tests for PropertyAPIClient."""

import logging
from decimal import Decimal
from unittest.mock import Mock
from typing import List

import pytest

from property_finder_models import (
    EnrichedProperty, 
    EnrichedNeighborhood, 
    EnrichedAddress, 
    PropertyType, 
    PropertyStatus
)

from ..config import APIClientConfig
from ..exceptions import NotFoundError, APIError
from ..property_client import PropertyAPIClient


class TestPropertyAPIClient:
    """Tests for PropertyAPIClient."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return APIClientConfig(
            base_url="http://test-api.example.com",
            timeout=30
        )
    
    @pytest.fixture
    def logger(self):
        """Create test logger."""
        return logging.getLogger("test")
    
    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        return Mock()
    
    @pytest.fixture
    def client(self, config, logger, mock_http_client):
        """Create test Property API client."""
        return PropertyAPIClient(config, logger)
    
    @pytest.fixture
    def sample_property(self):
        """Create sample property data."""
        return {
            "listing_id": "test-prop-123",
            "property_type": "house",
            "price": 500000,
            "bedrooms": 3,
            "bathrooms": 2.0,
            "address": {
                "street": "123 Test St",
                "city": "Test City",
                "state": "California",
                "zip_code": "12345",
                "coordinates": {"lat": 37.7749, "lon": -122.4194}
            },
            "features": ["garage", "garden"],
            "status": "active"
        }
    
    @pytest.fixture
    def sample_neighborhood(self):
        """Create sample neighborhood data."""
        return {
            "neighborhood_id": "test-neighborhood-123",
            "name": "Test Neighborhood",
            "city": "Test City",
            "state": "California"
        }
    
    def test_initialization(self, config, logger, mock_http_client):
        """Test client initialization."""
        client = PropertyAPIClient(config, logger)
        
        assert client.config == config
        assert client.logger == logger
    
    def test_get_properties_success(self, client, sample_property):
        """Test successful property retrieval."""
        # Mock HTTP response
        mock_response = {
            "data": [sample_property],
            "metadata": {
                "total_count": 1,
                "page": 1,
                "page_size": 50,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False
            },
            "links": None
        }
        
        # Mock the underlying get method
        client.get = Mock(return_value=mock_response)
        
        # Call method
        result = client.get_properties()
        
        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], EnrichedProperty)
        assert result[0].listing_id == "test-prop-123"
        
        # Verify API call
        client.get.assert_called_once_with(
            "/properties", 
            params={"page": 1, "page_size": 50}
        )
    
    def test_get_properties_with_filters(self, client, sample_property):
        """Test property retrieval with filters."""
        # Mock HTTP response
        mock_response = {
            "data": [sample_property],
            "metadata": {
                "total_count": 1,
                "page": 1,
                "page_size": 25,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False
            },
            "links": None
        }
        
        # Mock the underlying get method
        client.get = Mock(return_value=mock_response)
        
        # Call method with filters
        result = client.get_properties(
            city="Test City",
            include_embeddings=True,
            collection_name="test_collection",
            page=1,
            page_size=25
        )
        
        # Verify result
        assert len(result) == 1
        
        # Verify API call with filters
        client.get.assert_called_once_with(
            "/properties", 
            params={
                "page": 1, 
                "page_size": 25,
                "city": "Test City",
                "include_embeddings": True,
                "collection_name": "test_collection"
            }
        )
    
    def test_get_property_by_id_success(self, client, sample_property):
        """Test successful single property retrieval."""
        # Mock HTTP response
        mock_response = {
            "data": sample_property,
            "metadata": {}
        }
        
        # Mock the underlying get method
        client.get = Mock(return_value=mock_response)
        
        # Call method
        result = client.get_property_by_id("test-prop-123")
        
        # Verify result
        assert isinstance(result, EnrichedProperty)
        assert result.listing_id == "test-prop-123"
        
        # Verify API call
        client.get.assert_called_once_with("/properties/test-prop-123")
    
    def test_get_property_by_id_not_found(self, client):
        """Test property retrieval when property not found."""
        # Mock the underlying get method to raise NotFoundError
        client.get = Mock(side_effect=NotFoundError("Property not found"))
        
        # Call method and expect exception
        with pytest.raises(NotFoundError):
            client.get_property_by_id("nonexistent-prop")
    
    def test_get_neighborhoods_success(self, client, sample_neighborhood):
        """Test successful neighborhood retrieval."""
        # Mock HTTP response
        mock_response = {
            "data": [sample_neighborhood],
            "metadata": {
                "total_count": 1,
                "page": 1,
                "page_size": 50,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False
            },
            "links": None
        }
        
        # Mock the underlying get method
        client.get = Mock(return_value=mock_response)
        
        # Call method
        result = client.get_neighborhoods()
        
        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], EnrichedNeighborhood)
        assert result[0].name == "Test Neighborhood"
        
        # Verify API call
        client.get.assert_called_once_with(
            "/neighborhoods", 
            params={"page": 1, "page_size": 50}
        )
    
    def test_get_neighborhood_by_id_success(self, client, sample_neighborhood):
        """Test successful single neighborhood retrieval."""
        # Mock HTTP response
        mock_response = {
            "data": sample_neighborhood,
            "metadata": {}
        }
        
        # Mock the underlying get method
        client.get = Mock(return_value=mock_response)
        
        # Call method
        result = client.get_neighborhood_by_id("test-neighborhood-123")
        
        # Verify result
        assert isinstance(result, EnrichedNeighborhood)
        assert result.neighborhood_id == "test-neighborhood-123"
        
        # Verify API call
        client.get.assert_called_once_with("/neighborhoods/test-neighborhood-123")
    
    def test_get_all_properties_single_page(self, client, sample_property):
        """Test get_all_properties with single page."""
        # Mock HTTP response - less than page_size indicates last page
        mock_response = {
            "data": [sample_property],
            "metadata": {
                "total_count": 1,
                "page": 1,
                "page_size": 50,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False
            },
            "links": None
        }
        
        # Mock the underlying get method
        client.get = Mock(return_value=mock_response)
        
        # Call method
        pages = list(client.get_all_properties(page_size=50))
        
        # Verify result
        assert len(pages) == 1
        assert len(pages[0]) == 1
        assert pages[0][0].listing_id == "test-prop-123"
    
    def test_get_all_properties_multiple_pages(self, client, sample_property):
        """Test get_all_properties with multiple pages."""
        # Create multiple property responses
        property2 = sample_property.copy()
        property2["listing_id"] = "test-prop-456"
        
        # Page 1 - full page (should continue)
        page1_response = {
            "data": [sample_property, sample_property],  # Full page of 2 items
            "metadata": {
                "total_count": 3,
                "page": 1,
                "page_size": 2,
                "total_pages": 2,
                "has_next": True,
                "has_previous": False
            }
        }
        
        # Page 2 - partial page (should stop after this)
        page2_response = {
            "data": [property2],  # Only 1 item (less than page_size of 2)
            "metadata": {
                "total_count": 3,
                "page": 2,
                "page_size": 2,
                "total_pages": 2,
                "has_next": False,
                "has_previous": True
            }
        }
        
        # Mock the underlying get method to return different responses
        client.get = Mock(side_effect=[page1_response, page2_response])
        
        # Call method
        pages = list(client.get_all_properties(page_size=2))
        
        # Verify result
        assert len(pages) == 2
        assert len(pages[0]) == 2  # Full page
        assert len(pages[1]) == 1  # Partial page (should stop here)
        assert pages[0][0].listing_id == "test-prop-123"
        assert pages[1][0].listing_id == "test-prop-456"
    
    def test_batch_get_properties_success(self, client, sample_property):
        """Test batch property retrieval."""
        # Create multiple properties
        property2 = sample_property.copy()
        property2["listing_id"] = "test-prop-456"
        
        mock_responses = [
            {"data": sample_property, "metadata": {}},
            {"data": property2, "metadata": {}}
        ]
        
        # Mock the underlying get method
        client.get = Mock(side_effect=mock_responses)
        
        # Call method
        result = client.batch_get_properties(["test-prop-123", "test-prop-456"])
        
        # Verify result
        assert len(result) == 2
        assert result[0].listing_id == "test-prop-123"
        assert result[1].listing_id == "test-prop-456"
    
    def test_batch_get_properties_with_missing(self, client, sample_property):
        """Test batch property retrieval with some missing properties."""
        # Mock responses - first succeeds, second raises NotFoundError
        client.get = Mock(side_effect=[
            {"data": sample_property, "metadata": {}},
            NotFoundError("Property not found")
        ])
        
        # Call method
        result = client.batch_get_properties(["test-prop-123", "nonexistent-prop"])
        
        # Verify result - should only include found properties
        assert len(result) == 1
        assert result[0].listing_id == "test-prop-123"