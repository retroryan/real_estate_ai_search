"""Tests for BaseAPIClient."""

import logging
from unittest.mock import Mock, patch
from typing import List

import pytest
import httpx
from pydantic import BaseModel

from ..base import BaseAPIClient
from ..config import APIClientConfig
from ..exceptions import APIError, NotFoundError, TimeoutError, ValidationError
from ..models import PaginatedRequest, PaginatedResponse


class TestModel(BaseModel):
    """Test model for validation."""
    id: int
    name: str


class TestRequest(PaginatedRequest):
    """Test request model."""
    category: str = "default"


class TestResponse(PaginatedResponse[TestModel]):
    """Test paginated response model."""
    pass


class ConcreteAPIClient(BaseAPIClient):
    """Concrete implementation for testing."""
    pass


class TestBaseAPIClient:
    """Tests for BaseAPIClient."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return APIClientConfig(
            base_url="http://test.example.com",
            timeout=30
        )
    
    @pytest.fixture
    def logger(self):
        """Create test logger."""
        return logging.getLogger("test")
    
    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        return Mock(spec=httpx.Client)
    
    @pytest.fixture
    def client(self, config, logger, mock_http_client):
        """Create test client."""
        return ConcreteAPIClient(config, logger, mock_http_client)
    
    def test_initialization(self, config, logger, mock_http_client):
        """Test client initialization."""
        client = ConcreteAPIClient(config, logger, mock_http_client)
        
        assert client.config == config
        assert client.logger == logger
        assert client._http_client == mock_http_client
    
    def test_get_request_success(self, client):
        """Test successful GET request."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "name": "test"}
        client._http_client.request.return_value = mock_response
        
        result = client.get("/test", {"param": "value"})
        
        assert result == {"id": 1, "name": "test"}
        client._http_client.request.assert_called_once_with(
            method="GET",
            url="/test",
            params={"param": "value"},
            json=None
        )
    
    def test_get_request_with_model_validation(self, client):
        """Test GET request with response model validation."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "name": "test"}
        client._http_client.request.return_value = mock_response
        
        result = client.get("/test", response_model=TestModel)
        
        assert isinstance(result, TestModel)
        assert result.id == 1
        assert result.name == "test"
    
    def test_post_request_with_model_data(self, client):
        """Test POST request with Pydantic model data."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        client._http_client.request.return_value = mock_response
        
        data = TestModel(id=1, name="test")
        result = client.post("/test", data)
        
        assert result == {"success": True}
        client._http_client.request.assert_called_once_with(
            method="POST",
            url="/test",
            params=None,
            json={"id": 1, "name": "test"}
        )
    
    def test_post_request_with_dict_data(self, client):
        """Test POST request with dictionary data."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        client._http_client.request.return_value = mock_response
        
        data = {"id": 1, "name": "test"}
        result = client.post("/test", data)
        
        assert result == {"success": True}
        client._http_client.request.assert_called_once_with(
            method="POST",
            url="/test",
            params=None,
            json=data
        )
    
    def test_put_request(self, client):
        """Test PUT request."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"updated": True}
        client._http_client.request.return_value = mock_response
        
        data = {"id": 1, "name": "updated"}
        result = client.put("/test/1", data)
        
        assert result == {"updated": True}
        client._http_client.request.assert_called_once_with(
            method="PUT",
            url="/test/1",
            params=None,
            json=data
        )
    
    def test_delete_request(self, client):
        """Test DELETE request."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 204
        client._http_client.request.return_value = mock_response
        
        result = client.delete("/test/1")
        
        assert result is None
        client._http_client.request.assert_called_once_with(
            method="DELETE",
            url="/test/1",
            params=None,
            json=None
        )
    
    def test_404_error_handling(self, client):
        """Test 404 error handling."""
        mock_response = Mock()
        mock_response.status_code = 404
        client._http_client.request.return_value = mock_response
        
        with pytest.raises(NotFoundError) as exc_info:
            client.get("/not-found")
        
        assert "Resource not found" in str(exc_info.value)
        assert exc_info.value.status_code == 404
    
    def test_timeout_error_handling(self, client):
        """Test timeout error handling."""
        client._http_client.request.side_effect = httpx.TimeoutException("Timeout")
        
        with pytest.raises(TimeoutError) as exc_info:
            client.get("/test")
        
        assert "Request timed out" in str(exc_info.value)
    
    def test_validation_error_on_invalid_response(self, client):
        """Test validation error on invalid response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid": "data"}  # Missing required fields
        client._http_client.request.return_value = mock_response
        
        with pytest.raises(ValidationError):
            client.get("/test", response_model=TestModel)
    
    def test_pagination_single_page(self, client):
        """Test pagination with single page."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}],
            "total": 2,
            "page": 1,
            "page_size": 50,
            "total_pages": 1
        }
        client._http_client.request.return_value = mock_response
        
        pages = list(client.paginate("/test", TestRequest, TestResponse))
        
        assert len(pages) == 1
        assert len(pages[0]) == 2
        assert all(isinstance(item, TestModel) for item in pages[0])
    
    def test_pagination_multiple_pages(self, client):
        """Test pagination with multiple pages."""
        # Mock responses for multiple pages
        responses = [
            {
                "data": [{"id": 1, "name": "test1"}],
                "total": 3,
                "page": 1,
                "page_size": 1,
                "total_pages": 3
            },
            {
                "data": [{"id": 2, "name": "test2"}],
                "total": 3,
                "page": 2,
                "page_size": 1,
                "total_pages": 3
            },
            {
                "data": [{"id": 3, "name": "test3"}],
                "total": 3,
                "page": 3,
                "page_size": 1,
                "total_pages": 3
            }
        ]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = responses
        client._http_client.request.return_value = mock_response
        
        pages = list(client.paginate("/test", TestRequest, TestResponse, page_size=1))
        
        assert len(pages) == 3
        assert all(len(page) == 1 for page in pages)
        assert pages[0][0].id == 1
        assert pages[1][0].id == 2
        assert pages[2][0].id == 3
    
    def test_safe_json_with_valid_json(self, client):
        """Test _safe_json with valid JSON response."""
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        
        result = client._safe_json(mock_response)
        assert result == {"test": "data"}
    
    def test_safe_json_with_invalid_json(self, client):
        """Test _safe_json with invalid JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        result = client._safe_json(mock_response)
        assert result is None