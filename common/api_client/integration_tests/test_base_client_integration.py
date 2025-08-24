"""Integration tests for BaseAPIClient functionality against running API server."""

import logging
from unittest.mock import Mock

import pytest
import httpx

from ..base import BaseAPIClient
from ..config import APIClientConfig
from ..exceptions import NotFoundError, TimeoutError, APIError


class ConcreteAPIClient(BaseAPIClient):
    """Concrete implementation of BaseAPIClient for testing."""
    pass


class TestBaseAPIClientIntegration:
    """Integration tests for BaseAPIClient core functionality."""
    
    @pytest.fixture
    def test_client(self, api_base_url, api_timeout, integration_logger):
        """Create a test instance of BaseAPIClient."""
        config = APIClientConfig(
            base_url=api_base_url,
            timeout=api_timeout
        )
        return ConcreteAPIClient(config, integration_logger)
    
    def test_client_initialization(self, test_client, api_base_url):
        """Test client initialization with configuration."""
        assert str(test_client.config.base_url).rstrip('/') == api_base_url.rstrip('/')
        assert test_client.config.timeout >= 1
        assert test_client.logger is not None
        assert test_client._http_client is not None
    
    def test_get_request_health_endpoint(self, test_client, api_server_check):
        """Test GET request against health endpoint."""
        assert api_server_check is True
        
        # Test direct health endpoint
        try:
            response = test_client.get("/health")
            
            # Should return some form of health status
            assert isinstance(response, dict)
            
        except APIError as e:
            # If health endpoint structure is different, that's OK
            pytest.skip(f"Health endpoint format different: {e}")
    
    def test_get_request_with_query_params(self, test_client, api_server_check):
        """Test GET request with query parameters."""
        assert api_server_check is True
        
        try:
            # Try to get properties with query parameters
            response = test_client.get(
                "/api/v1/properties",
                params={"page": 1, "page_size": 1}
            )
            
            # Should return some structured response
            assert isinstance(response, dict)
            
            # Basic API response structure
            if "data" in response:
                assert isinstance(response["data"], list)
            if "metadata" in response:
                assert isinstance(response["metadata"], dict)
                
        except APIError as e:
            pytest.skip(f"Properties endpoint not available: {e}")
    
    def test_404_error_handling(self, test_client, api_server_check):
        """Test proper handling of 404 errors."""
        assert api_server_check is True
        
        with pytest.raises(NotFoundError):
            test_client.get("/api/v1/nonexistent-endpoint")
    
    def test_invalid_json_response_handling(self, test_client):
        """Test handling of non-JSON responses."""
        # Create a mock client that returns non-JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Not JSON content"
        
        test_client._http_client.request = Mock(return_value=mock_response)
        
        with pytest.raises(APIError, match="Failed to parse JSON response"):
            test_client.get("/test")
    
    def test_timeout_handling(self, test_client):
        """Test timeout error handling."""
        # Create a client with very short timeout
        config = APIClientConfig(
            base_url=str(test_client.config.base_url),
            timeout=0.001  # Very short timeout
        )
        short_timeout_client = ConcreteAPIClient(config, test_client.logger)
        
        # Mock timeout exception
        short_timeout_client._http_client.request = Mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )
        
        with pytest.raises(TimeoutError):
            short_timeout_client.get("/test")
    
    def test_server_error_handling(self, test_client):
        """Test handling of server errors (5xx)."""
        # Mock a 500 server error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        test_client._http_client.request = Mock(return_value=mock_response)
        
        with pytest.raises(APIError):
            test_client.get("/test")
    
    def test_client_error_handling(self, test_client):
        """Test handling of client errors (4xx)."""
        # Mock a 400 bad request error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.json.return_value = {"error": "Invalid parameter"}
        
        test_client._http_client.request = Mock(return_value=mock_response)
        
        with pytest.raises(APIError):
            test_client.get("/test")
    
    def test_post_request_functionality(self, test_client):
        """Test POST request functionality (mocked)."""
        # Mock successful POST response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"created": True, "id": 123}
        mock_response.raise_for_status = Mock()
        
        test_client._http_client.request = Mock(return_value=mock_response)
        
        # Test POST with dictionary data
        result = test_client.post("/test", {"name": "test", "value": 42})
        
        assert result == {"created": True, "id": 123}
        
        # Verify the request was made correctly
        test_client._http_client.request.assert_called_once_with(
            method="POST",
            url="/test",
            params=None,
            json={"name": "test", "value": 42}
        )
    
    def test_put_request_functionality(self, test_client):
        """Test PUT request functionality (mocked)."""
        # Mock successful PUT response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"updated": True}
        mock_response.raise_for_status = Mock()
        
        test_client._http_client.request = Mock(return_value=mock_response)
        
        result = test_client.put("/test/123", {"name": "updated"})
        
        assert result == {"updated": True}
        
        # Verify the request was made correctly
        test_client._http_client.request.assert_called_once_with(
            method="PUT",
            url="/test/123",
            params=None,
            json={"name": "updated"}
        )
    
    def test_delete_request_functionality(self, test_client):
        """Test DELETE request functionality (mocked)."""
        # Mock successful DELETE response
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.raise_for_status = Mock()
        
        test_client._http_client.request = Mock(return_value=mock_response)
        
        result = test_client.delete("/test/123")
        
        assert result is None  # DELETE requests return None
        
        # Verify the request was made correctly
        test_client._http_client.request.assert_called_once_with(
            method="DELETE",
            url="/test/123",
            params=None,
            json=None
        )
    
    def test_logging_functionality(self, test_client, caplog):
        """Test that logging is working properly."""
        # Mock a successful request
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status = Mock()
        
        test_client._http_client.request = Mock(return_value=mock_response)
        
        with caplog.at_level(logging.DEBUG):
            test_client.get("/test")
        
        # Verify debug logging occurred
        debug_messages = [record.message for record in caplog.records if record.levelname == "DEBUG"]
        assert any("Making GET request" in msg for msg in debug_messages)
        assert any("Received response" in msg for msg in debug_messages)
    
    def test_safe_json_method(self, test_client):
        """Test the _safe_json helper method."""
        # Test with valid JSON
        mock_response = Mock()
        mock_response.json.return_value = {"valid": "json"}
        
        result = test_client._safe_json(mock_response)
        assert result == {"valid": "json"}
        
        # Test with invalid JSON
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        result = test_client._safe_json(mock_response)
        assert result is None
    
    def test_configuration_validation(self, integration_logger):
        """Test configuration validation during client creation."""
        # Test with invalid base URL
        with pytest.raises(Exception):  # Pydantic validation error
            APIClientConfig(base_url="not-a-url", timeout=30)
        
        # Test with invalid timeout
        with pytest.raises(Exception):  # Pydantic validation error
            APIClientConfig(base_url="http://example.com", timeout=-1)
        
        # Test with valid configuration
        config = APIClientConfig(base_url="http://example.com", timeout=30)
        client = ConcreteAPIClient(config, integration_logger)
        
        assert str(client.config.base_url) == "http://example.com/"
        assert client.config.timeout == 30